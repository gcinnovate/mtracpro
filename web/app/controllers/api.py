import json
import web
import datetime
import random
from . import (
    db, get_current_week, serversByName,
    IndicatorMapping, IndicatorsDataSet, notifyingParties, allDistrictsByName)
from settings import config, KEYWORD_SERVER_MAPPINGS
import settings
from app.tools.utils import (
    get_basic_auth_credentials, auth_user, get_webhook_msg_old,
    queue_request, parse_message, post_request_to_dispatcher2, get_reporting_week,
    get_webhook_msg
)
# from app.tools.utils import get_location_role_reporters, queue_schedule, log_schedule, update_queued_sms
from settings import DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, TEXT_INDICATORS
from settings import USE_OLD_WEBHOOKS
from tasks import sendsms_to_uuids_task


def send_threshold_alert(msg, district):
    try:
        threshold_alert_contacts = notifyingParties[allDistrictsByName[district]]['threshold_alert_contacts']
    except:
        threshold_alert_contacts = []
    if threshold_alert_contacts:
        sendsms_to_uuids_task(threshold_alert_contacts, msg)


class LocationChildren:
    """Returns Children for a node """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM get_children($id) ORDER BY name;", {'id': id})
        if rs:
            for r in rs:
                parent = r['tree_parent_id']
                ret.append(
                    {
                        "name": r['name'],
                        "id": r['id'],
                        "attr": {'id': r['id']},
                        "parent": parent if parent else "#",
                        "state": "closed"
                    })
        return json.dumps(ret)


class DistrictFacilities:
    """Returns facilities in a given district """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name FROM healthfacilities WHERE district_id = $id "
            "ORDER BY name;", {'id': id})
        if rs:
            for r in rs:
                ret.append(
                    {
                        "id": r['id'],
                        "name": r['name']
                    })
        return json.dumps(ret)


class LocationFacilities:
    """Returns facilities in a given location """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name FROM healthfacilities WHERE location = $id "
            "ORDER BY name;", {'id': id})
        if rs:
            for r in rs:
                ret.append(
                    {
                        "id": r['id'],
                        "name": r['name']
                    })
        return json.dumps(ret)


class FacilityReporters:
    """Returns reports attached to a particular health facility"""
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT firstname, lastname, telephone FROM reporters WHERE  "
            " facilityid=$id ",
            {'id': id})
        for r in rs:
            ret.append({
                "firstname": r['firstname'],
                "lastname": r['lastname'],
                "telephone": r['telephone']})
        return json.dumps(ret)


class Location:
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM locations WHERE id = $id;", {'id': id})
        if rs:
            for r in rs:
                parent = r['tree_parent_id']
                ret.append(
                    {
                        "text": r['name'],
                        "attr": {'id': r['id']},
                        "id": parent if parent else "#",
                        "state": "closed"
                    })
        return json.dumps(ret)


class SubcountyLocations:
    def GET(self, id):
        """ returs the form bellow
        ret = {
            "Parish X": [{'name': "Villa 1"}, {"name": "Villa 2"}, {"name": "Villa 3"}],
            "Parish Y": [{'name': "Villa 4"}, {"name": "Villa 5"}],
            "Parish Z": [{'name': "Villa 6"}, {"name": "Villa 7"}],
        }
        """
        web.header("Content-Type", "application/json; charset=utf-8")
        ret = {}
        res = db.query("SELECT id, name FROM get_children($id)", {'id': id})
        for r in res:
            parish_name = r['name']
            parish_id = r['id']
            ret[parish_name] = []
            x = db.query("SELECT id, name FROM get_children($id)", {'id': parish_id})
            for i in x:
                ret[parish_name].append({'id': i['id'], 'name': i['name']})
        return json.dumps(ret)


class ReportersEndpoint:
    def GET(self, location_code):
        params = web.input(role="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        ret = []
        reporter_role = params.role
        SQL = (
            "SELECT firstname, lastname, telephone, alternate_tel, email, national_id, "
            "reporting_location, district, role, loc_name, location_code FROM reporters_view4 "
            "WHERE reporting_location IN (SELECT id FROM get_descendants_including_self(( SELECT id FROM "
            "locations WHERE code=$location_code))) ")
        if reporter_role:
            SQL += " AND lower(role) = $role"
        res = db.query(SQL, {'location_code': location_code, 'role': reporter_role.lower()})
        if res:
            for r in res:
                ret.append({
                    "firstname": r.firstname, "lastname": r.lastname,
                    "telephone": r.telephone, "alternate_tel": r.alternate_tel,
                    "email": r.email, "national_id": r.national_id,
                    "location_name": r.loc_name,
                    "location_code": r.location_code,
                    "distrcit": r.district, "role": r.role
                })
        return json.dumps(ret)


class ReporterAPI:
    def GET(self, phonenumber):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input(imei="")
        if len(phonenumber) < 10:
            return json.dumps({})
        SQL = (
            "SELECT id, firstname || ' ' || lastname as name, telephone, "
            " get_district(district_id) as district, imei, smscode, facilityid, facility, facilitycode, "
            "total_reports, to_char(last_reporting_date, 'YYYY-MM-DD HH:MI') last_reporting_date, role "
            " FROM reporters_view1 "
            # " WHERE substring(reverse(telephone), 0, 9) = substring(reverse($tel), 0, 9) "
            # " OR substring(reverse(alternate_tel), 0, 9) = substring(($tel), 0, 9) ")
            " WHERE telephone LIKE $tel "
            " OR alternate_tel LIKE $tel ")
        # " WHERE telephone = $tel OR alternate_tel = $tel")
        res = db.query(SQL, {'tel': '%%%s' % phonenumber[-9:]})
        ret = {}
        if res:
            r = res[0]
            smscode = r.smscode
            deviceChanged = False
            imei = params.imei
            if r.imei != imei:
                deviceChanged = True
                smscode = ''.join(random.choice('0123456789') for i in range(5))
                db.query(
                    "UPDATE reporters SET (smscode, imei) = ($smscode, $imei) WHERE id = $id",
                    {'smscode': smscode, 'imei': imei, 'id': r.id})
            ret = {
                'name': r.name, 'phoneNumber': r.telephone,
                'district': r.district, 'facility': r.facility,
                'facilityId': r.facilitycode, 'totalReports': r.total_reports,
                'lastReportingDate': r.last_reporting_date,
                'roles': r.role,
                'deviceChanged': deviceChanged,
                # 'smsCode': smscode
                'smsCode': '11111'
            }
            # sendsms smscode to number

        return json.dumps(ret)


class ReportsThisWeek:
    def GET(self, facilitycode):
        year, week = get_current_week()
        reports = db.query(
            "SELECT raw_msg, msisdn FROM requests WHERE year = $yr AND week = $wk "
            "AND facility = $fcode AND status IN ('pending', 'ready', 'completed', 'failed') "
            " ORDER BY id DESC",
            {'yr': year, 'wk': '%s' % week, 'fcode': facilitycode})

        html_str = '<table class="table table-striped table-bordered table-hover">'
        reporters = []
        if reports:
            html_str += "<tr><td><strong>Accepted Reports</strong></td>"
            html_str += '<td><table class="table table-striped table-bordered table-hover">'
            html_str += '<tr><th>#</th><th>Message</th></tr>'

            for x, r in enumerate(reports):
                html_str += "<tr><td>%s" % (x + 1) + "</td><td>" + r['raw_msg'] + "</td></tr>"
                if r['msisdn'] not in reporters:
                    reporters.append(r['msisdn'])
            html_str += "</table></td></tr>"
            html_str += "<tr><td><strong>Reporters</strong></td>"
            html_str += '<td><table class="table table-striped table-bordered table-hover">'
            html_str += '<tr><th>#</th><th>Name</th><th>Phone Number</th></tr>'

            for p, reporter in enumerate(reporters):
                html_str += "<tr><td>%s" % (p + 1) + "</td><td></td><td>" + reporter + "</td></tr>"
            html_str += "</table></td></tr>"
        html_str += "</table>"
        return html_str


class Cases:
    def GET(self):
        return json.dumps({"message": "0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"})

    def POST(self):
        params = web.input()
        if USE_OLD_WEBHOOKS:
            msg = get_webhook_msg_old(params, 'msg')
        else:
            payload = json.loads(web.data())
            msg = get_webhook_msg(payload, 'msg')

        message = parse_message(msg, 'cases')

        return json.dumps({"message": message})


class Deaths:
    def GET(self):
        return json.dumps({"message": "0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"})

    def POST(self):
        params = web.input()
        if USE_OLD_WEBHOOKS:
            msg = get_webhook_msg_old(params, 'msg')
        else:
            payload = json.loads(web.data())
            msg = get_webhook_msg(payload, 'msg')

        message = parse_message(msg, 'death')

        return json.dumps({"message": message})


class OrderMessage:
    def GET(self, form):
        params = web.input()
        if USE_OLD_WEBHOOKS:
            msg = get_webhook_msg_old(params, 'msg')
        else:
            payload = json.loads(web.data())
            msg = get_webhook_msg(payload, 'msg')

        message = parse_message(msg, form)

        return json.dumps({"message": message})

    def POST(self, form):
        params = web.input()
        if USE_OLD_WEBHOOKS:
            msg = get_webhook_msg_old(params, 'msg')
        else:
            payload = json.loads(web.data())
            msg = get_webhook_msg(payload, 'msg')

        message = parse_message(msg, form)

        return json.dumps({"message": message})


class Test:
    def GET(self):
        web.header('Content-Type', 'application/json')
        return json.dumps({"message": "1.2.3"})

    def POST(self):
        return json.dumps({"message": "1+0+3+4+5+6+7+8+9+10+11+12+13+14+15+16.0.0"})


class Dhis2Queue:
    def GET(self):
        return json.dumps({"status": "success"})

    def POST(self):
        params = web.input(
            facilitycode="", form="", district="", msisdn="",
            raw_msg="", report_type="", facility="", reporter_type="", reporter_name="")
        extras = {'reporter_type': params.reporter_type}
        # values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy

        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
            dataValues = []
        else:
            dataValues = ""
        # print("FACILITYCODE:", params.facilitycode, "==>", params.facility)
        if params.facilitycode:
            if not USE_OLD_WEBHOOKS:
                values = json.loads(web.data())
                results = values.get('results', {})
                thresholds_list = []
                for key, v in results.iteritems():
                    val = v.get('value')
                    try:
                        val = int(float(val))
                    except:
                        pass
                    label = v.get('name')
                    slug = "%s_%s" % (params.form, label)
                    # print(slug)
                    if val.__str__().isdigit() or slug in TEXT_INDICATORS:
                        if not(val) and params.form in getattr(
                                settings, 'REPORTS_WITH_COMMANDS', ['cases', 'death', 'epc', 'epd']):  # XXX irregular forms
                            if label not in params.raw_msg.lower():
                                continue  # skip zero values for cases and death
                        if slug not in IndicatorMapping:
                            # print("Indicator Not Supported.::.", slug)
                            continue
                        # XXX check thresholds here
                        if IndicatorMapping[slug]['threshold']:
                            try:
                                threshold = int(float(IndicatorMapping[slug]['threshold']))
                                if val >= threshold:
                                    thresholds_list.append('{} {}'.format(val, IndicatorMapping[slug]['descr']))
                            except:
                                print("Threshold.::.Failed to Add threshold Message")
                                pass
                        # print("%s=>%s" % (slug, val), IndicatorMapping[slug])
                        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                            dataValues.append(
                                {
                                    'dataElement': IndicatorMapping[slug]['dhis2_id'],
                                    'categoryOptionCombo': IndicatorMapping[slug]['dhis2_combo_id'],
                                    'value': val})
                        else:
                            dataValues += (
                                "<dataValue dataElement='%s' categoryOptionCombo="
                                "'%s' value='%s' />\n" %
                                (IndicatorMapping[slug]['dhis2_id'], IndicatorMapping[slug]['dhis2_combo_id'], val))

                # Build alert message and send it
                # print("Thresholds List.::.", thresholds_list)
                if thresholds_list:
                    alert_message = "Thresholds alert: {0} ({1}) of {2} - {3} district reported:\n".format(
                        params.reporter_name, params.msisdn, params.facility, params.district)
                    alert_message += '\n'.join(thresholds_list)
                    alert_message += '\n' + params.raw_msg
                    send_threshold_alert(alert_message, params.district)
                    # print(alert_message)

            else:
                values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
                thresholds_list = []
                for v in values:
                    val = v.get('value')
                    try:
                        val = int(float(val))
                    except:
                        pass
                    label = v.get('label')
                    slug = "%s_%s" % (params.form, label)
                    if val.__str__().isdigit() or slug in TEXT_INDICATORS:
                        if not(val) and params.form in getattr(
                                settings, 'REPORTS_WITH_COMMANDS', ['cases', 'death', 'epc', 'epd']):
                            if label not in params.raw_msg.lower():
                                continue  # skip zero values for cases and death
                        if slug not in IndicatorMapping:
                            print("Indicator Not Supported.::.", slug)
                            continue
                        # XXX check thresholds here
                        if IndicatorMapping[slug]['threshold']:
                            try:
                                threshold = int(float(IndicatorMapping[slug]['threshold']))
                                if val > threshold:
                                    thresholds_list.append('{} {}'.format(val, IndicatorMapping[slug]['descr']))
                            except Exception as e:
                                print("Threshold.::.Failed to Add threshold Message=>", str(e))
                                pass
                        print("%s=>%s" % (slug, val), IndicatorMapping[slug])
                        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                            dataValues.append(
                                {
                                    'dataElement': IndicatorMapping[slug]['dhis2_id'],
                                    'categoryOptionCombo': IndicatorMapping[slug]['dhis2_combo_id'],
                                    'value': val})
                        else:
                            dataValues += (
                                "<dataValue dataElement='%s' categoryOptionCombo="
                                "'%s' value='%s' />\n" %
                                (IndicatorMapping[slug]['dhis2_id'], IndicatorMapping[slug]['dhis2_combo_id'], val))

                # Build alert message and send it
                print("Thresholds List.::.", thresholds_list)
                if thresholds_list:
                    alert_message = "Thresholds alert: {0} ({1}) of {2} - {3} district reported:\n".format(
                        params.reporter_name, params.msisdn, params.facility, params.district)
                    alert_message += '\n'.join(thresholds_list)
                    alert_message += '\n' + params.raw_msg
                    send_threshold_alert(alert_message, params.district)
                    print(alert_message)

            if not dataValues and params.form in ('cases', 'death'):
                if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                    dataValues = []
                else:
                    dataValues = DEFAULT_DATA_VALUES[params.form]

            if dataValues:
                args_dict = {
                    'completeDate': datetime.datetime.now().strftime("%Y-%m-%d"),
                    'period': get_reporting_week(datetime.datetime.now()),
                    'orgUnit': params.facilitycode,
                    'dataValues': dataValues
                }
                if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                    args_dict['dataSet'] = IndicatorsDataSet.get(params.form, HMIS_033B_DATASET)
                    args_dict['attributeOptionCombo'] = HMIS_033B_DATASET_ATTR_OPT_COMBO
                    payload = json.dumps(args_dict)
                else:
                    payload = XML_TEMPLATE % args_dict
                year, week = tuple(args_dict['period'].split('W'))
                print(payload)
                destination_name = KEYWORD_SERVER_MAPPINGS.get(
                    params.form, config['dispatcher2_destination'])
                extra_params = {
                    'week': week, 'year': year, 'msisdn': params.msisdn,
                    'facility': params.facilitycode, 'raw_msg': params.raw_msg,
                    'district': params.district, 'report_type': params.report_type,
                    # 'source': config['dispatcher2_source'],
                    # 'destination': config['dispatcher2_destination'],
                    'source': serversByName[config['dispatcher2_source']],
                    'destination': serversByName[destination_name],
                    'extras': json.dumps(extras),
                    'status': config.get('default-queue-status', 'pending')}
                # now ready to queue to DB for pushing to DHIS2
                # resp = queue_submission(serverid, post_xml, year, week)
                print(extra_params)
                if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                    extra_params['ctype'] = 'json'
                    # resp = post_request_to_dispatcher2(
                    #    payload, params=extra_params, ctype='json')
                    extra_params['body'] = payload
                    queue_request(db, extra_params)
                else:
                    extra_params['ctype'] = 'xml'
                    # resp = post_request_to_dispatcher2(payload, params=extra_params)
                    extra_params['body'] = payload
                    queue_request(db, extra_params)
                # print "Resp:", resp

        return json.dumps({"status": "success"})


class QueueForDhis2InstanceProcessing:
    def GET(self):
        """Please specify source and destination call in your call to this API"""
        params = web.input(
            msisdn="", raw_msg="", report_type="", source="", destination="", is_qparams="t")
        year, week = get_current_week()
        payload = "message=%s&originator=%s" % (params.raw_msg, params.msisdn)
        extra_params = {
            'week': week, 'year': year, 'msisdn': params.msisdn,
            'facility': '', 'raw_msg': params.raw_msg,
            'distrcit': '', 'report_type': params.report_type,
            'source': params.source, 'destination': params.destination,
            'is_qparams': "t"}
        print(extra_params)

        resp = post_request_to_dispatcher2(payload, ctype="text", params=extra_params)
        print("Resp:", resp)

        return json.dumps({"status": "success"})


class Routing:
    def GET(self):
        params = web.input(raw_msg="", keyword="")
        raw_msg = params.raw_msg
        keyword = params.keyword
        destination_name = KEYWORD_SERVER_MAPPINGS.get(
            keyword, config['dispatcher2_destination'])
        source = config['dispatcher2_source']
