import copy
import json
from collections.abc import Mapping
from string import Template
import web
import requests
# import settings
from . import db, get_current_week, notifyingParties, allDistrictsByName
from webapp.app.tools.utils import get_basic_auth_credentials, auth_user
from webapp.settings import (
    config,
    KEYWORD_MESSAGE_TEMPLATE,
    KEYWORD_SERVER_MAPPINGS,
    SEND_ALERTS,
)
from .tasks import sendsms_to_uuids_task


def send_general_alert(msg, district):
    try:
        general_alert_contacts = notifyingParties[allDistrictsByName[district]]['threshold_alert_contacts']
    except Exception as e:
        print(str(e))
        general_alert_contacts = []
    # print("GEN ALERT=>", general_alert_contacts)
    if general_alert_contacts:
        sendsms_to_uuids_task.delay(general_alert_contacts, msg)


class IndicatorsAPI:
    """Returns mappins.json file used by the android client"""
    def GET(self):
        # params = web.input(form="")
        web.header("Content-Type", "application/json; charset=utf-8")

        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})

        indicators = db.query(
            "SELECT id, form_order, form, slug, cmd, description, shortname, dataset, dataelement, "
            "category_combo, threshold FROM dhis2_mtrack_indicators_mapping "
            "ORDER BY form, form_order")
        ret = {}
        for i in indicators:
            ret[i["slug"]] = {
                'categoryOptionCombo': i['category_combo'],
                'dataElement': i['dataelement'],
                'descr': i['description'],
            }
        return json.dumps(ret)


class ReportingStatus:
    def GET(self, reporter):
        web.header("Content-Type", "application/json; charset=utf-8")
        ret = {}
        return json.dumps(ret)


def _render_message_template(value, substitutions):
    """Render string values in a copied message template recursively."""
    if isinstance(value, Template):
        return value.safe_substitute(substitutions)
    if isinstance(value, str):
        return Template(value).safe_substitute(substitutions)
    if isinstance(value, Mapping):
        return {
            key: _render_message_template(item, substitutions)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_render_message_template(item, substitutions) for item in value]
    if isinstance(value, tuple):
        return tuple(_render_message_template(item, substitutions) for item in value)
    return value


def _dispatch_body(form, raw_msg, msisdn):
    """Build a Dispatcher2 body and its content type for a keyword."""
    template = KEYWORD_MESSAGE_TEMPLATE.get(form)
    if template is None:
        return (
            "message={0}&originator={1}".format(raw_msg, msisdn),
            "text/plain",
        )

    body = _render_message_template(
        copy.deepcopy(template),
        {"raw_msg": raw_msg, "msisdn": msisdn},
    )
    if isinstance(body, str):
        return body, "text/plain"
    return json.dumps(body), "application/json"


class Dispatch:
    """routing messages to DHIS 2 servers"""
    def GET(self):
        params = web.input(raw_msg="", msisdn="", form="")
        web.header("Content-Type", "application/json; charset=utf-8")
        year, week = get_current_week()
        myparams = {
            "username": config["dispatcher2_username"],
            "password": config["dispatcher2_password"],
            "ctype": "text",
            "raw_msg": params.raw_msg,
            "year": year,
            "week": week,
            "msisdn": params.msisdn,
            "is_qparams": 't',
            "extras": "{}",
            "source": "mtrackpro",
            "destination": KEYWORD_SERVER_MAPPINGS.get(params.form, "localhost")
        }
        payload, content_type = _dispatch_body(
            params.form, params.raw_msg, params.msisdn)

        queueEndpoint = config.get("dispatcher2_queue_url", "http://localhost:9191/queue?")
        # print("Call=>", queueEndpoint)
        requests.post(
            queueEndpoint,
            data=payload,
            params=myparams,
            headers={"Content-type": content_type})
        # print("RESP:===>", resp.text)
        return json.dumps({"status": "success"})


class SendAlert:
    def GET(self):
        params = web.input(raw_msg="", msisdn="", facility="", district="", reporter_name="")
        web.header("Content-Type", "application/json; charset=utf-8")
        # Build alert message and send it
        if SEND_ALERTS and params.facility and params.district:
            # Build alert message and send it
                alert_message = "Alert: {0} ({1}) of {2} - {3} district reported:\n".format(
                    params.reporter_name, params.msisdn, params.facility, params.district)
                alert_message += params.raw_msg
                send_general_alert(alert_message, params.district)
                # print(alert_message)

        return json.dumps({"status": "success"})
