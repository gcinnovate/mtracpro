import json
import web
import datetime
from . import db
from settings import config
from settings import USE_OLD_WEBHOOKS
from app.tools.utils import get_webhook_msg_old, get_webhook_msg
from app.tools.utils import get_request
from app.tools.utils import queue_anonymous_report


class AnonymousReports:
    def GET(self):
        params = web.input(
            contact_uuid="", msg="")

        return json.dumps({})

    def POST(self):
        params = web.input(
            contact_uuid="", msg="")
        contact_uuid = params.contact_uuid
        if USE_OLD_WEBHOOKS:
            msg = get_webhook_msg_old(params, 'msg')
        else:
            payload = json.loads(web.data())
            msg = get_webhook_msg(payload, 'msg')
        print(contact_uuid + "=> " + msg)
        extra_params = {'contact_uuid': contact_uuid, 'report': msg}
        queue_anonymous_report(db, extra_params)

        return json.dumps({})


class AnonymousReportDetails:
    def GET(self, report_id):
        htmlStr = '<table class="table table-striped table-bordered table-hover">'
        htmlStr += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        rs = db.query(
            "SELECT id, facility, district, created, report, action, topic, "
            "action_taken, action_center, comment FROM anonymousreports_view "
            "WHERE id = $id", {'id': report_id})
        if rs:
            rpt = rs[0]
            htmlStr += "<tr><td>Facility</td><td>%s</td></tr>" % rpt['facility']
            htmlStr += "<tr><td>District</td><td>%s</td></tr>" % rpt['district']
            htmlStr += "<tr><td>Date</td><td>%s</td></tr>" % rpt['created']
            htmlStr += "<tr><td>Reports</td><td>%s</td></tr>" % rpt['report']
            htmlStr += "<tr><td>Topic</td><td>%s</td></tr>" % rpt['topic']
            htmlStr += "<tr><td>Action</td><td>%s</td></tr>" % rpt['action']
            htmlStr += "<tr><td>Action Center</td><td>%s</td></tr>" % rpt['action_center']
            htmlStr += "<tr><td>Comments</td><td>%s</td></tr>" % rpt['comment']
            htmlStr += "<tr><td>Action Taken</td><td>%s</td></tr>" % rpt['action_taken']
            htmlStr += "<tr><td>Responses</td><td>%s</td></tr>" % rpt['facility']

        htmlStr += "</tbody></table>"
        return htmlStr


class AnonReport:
    def GET(self, report_id):
        web.header("Content-Type", "application/json; charset=utf-8")
        rs = db.query(
            "SELECT id, facility, district, to_char(created, 'YYYY-MM-DD HH:MI:SS') AS created,"
            "report, action, topic, action_taken, action_center, comment FROM anonymousreports_view "
            "WHERE id = $id", {'id': report_id})
        if rs:
            rpt = rs[0]
            report = {
                'id': rpt['id'], 'facility': rpt['facility'], 'district': rpt['district'],
                'created': rpt['created'], 'report': rpt['report'], 'action': rpt['action'],
                'topic': rpt['topic'], 'action_taken': rpt['action_taken'],
                'action_center': rpt['action_center'], 'comment': rpt['comment']
            }
            return json.dumps(report)
        return json.dumps({})
