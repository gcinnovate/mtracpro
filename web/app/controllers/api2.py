import json
import logging
from . import db, Indicators, IndicatorsByFormOrder, IndicatorsCategoryCombos, server_apps
import web
from app.tools.utils import post_request
from settings import config
import settings
from app.tools.utils import get_basic_auth_credentials, auth_user, get_webhook_msg
from tasks import send_bulksms_task, send_facility_sms_task

logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/mtrackpro-web.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)


class LocationsEndpoint:
    def GET(self, district_code):
        params = web.input(from_date="", type="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})

        y = db.query("SELECT id, lft, rght FROM locations WHERE code = $code", {'code': district_code})
        location_id = 0
        if y:
            loc = y[0]
            location_id = loc['id']
            lft = loc['lft']
            rght = loc['rght']
        SQL = (
            "SELECT a.id, a.name, a.code, a.uuid, a.lft, a.rght, a.tree_id, a.tree_parent_id, "
            "b.code as parent_code, c.level, c.name as type, "
            "to_char(a.cdate, 'YYYY-mm-dd') as created "
            " FROM locations a, locations b, locationtype c"
            " WHERE "
            " a.tree_parent_id = b.id "
            " AND a.lft > %s AND a.lft < %s "
            " AND a.type_id = c.id "
        )
        SQL = SQL % (lft, rght)
        if params.from_date:
            SQL += " AND a.cdate >= $date "
        if params.type:
            SQL += " AND c.name = $type "
        r = db.query(SQL, {'id': location_id, 'date': params.from_date, 'type': params.type})
        ret = []
        for i in r:
            ret.append(dict(i))
        return json.dumps(ret)


class ReportersXLEndpoint:
    def GET(self):
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header("Content-Type", "application/json; charset=utf-8")
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        web.header("Content-Type", "application/zip; charset=utf-8")
        # web.header('Content-disposition', 'attachment; filename=%s.csv'%file_name)
        web.seeother("/static/downloads/reporters_all.xls.zip")


class Remarks:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        remark = get_webhook_msg(params, 'msg')
        phone = params.phone.replace('+', '')
        with db.transaction():
            r = db.query(
                "SELECT id, reporting_location, district_id, "
                "district, loc_name "
                "FROM reporters_view WHERE replace(telephone, '+', '') = $tel "
                "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
            if r:
                reporter = r[0]
                db.query(
                    "INSERT INTO alerts(district_id, reporting_location, alert) "
                    "VALUES($district_id, $loc, $msg) ",
                    {
                        'district_id': reporter['district_id'],
                        'loc': reporter['reporting_location'],
                        'msg': remark})
            else:
                db.query(
                    "INSERT INTO alerts (alert) VALUES($msg)", {'msg': remark})
            ret = ("Thank you for your report, this report will be sent to relevant authorities.")
            return json.dumps({"message": ret})


class CreateFacility:
    """Creates and edits an mTrac health facility"""
    # @require_login
    def GET(self):
        params = web.input(
            name="", ftype="", district="",
            code="", is_033b='f', dhis2id="", subcounty="",
            username="", password=""
        )
        username = params.username
        password = params.password
        r = auth_user(db, username, password)
        if not r[0]:
            return "Unauthorized access"

        with db.transaction():
            res = db.query(
                "SELECT id FROM healthfacility_type "
                "WHERE lower(name) = $name ",
                {'name': params.ftype.lower()})
            if res:
                type_id = res[0]["id"]
                r = db.query(
                    "SELECT id FROM healthfacilities WHERE code = $code",
                    {'code': params.code})
                if not r:
                    logging.debug("Creating facility with ID:%s" % params.code)
                    new = db.query(
                        "INSERT INTO healthfacilities "
                        "(name, code, type_id, district, is_033b) VALUES "
                        "($name, $dhis2id, $type, $district, $is_033b) RETURNING id",
                        {
                            'name': params.name, 'dhis2id': params.dhis2id,
                            'code': params.code, 'type': type_id, 'district': params.district,
                            'active': True, 'deleted': False,
                            'is_033b': params.is_033b
                        })
                    if new:
                        facility_id = new[0]["id"]
                        d = db.query(
                            "SELECT id FROM locations WHERE lower(name) = $district "
                            "AND type_id = 3", {'district': params.district.lower()})
                        if d:
                            district_id = d[0]["id"]
                            db.query(
                                "UPDATE healthfacilities SET district_id = $district_id "
                                " WHERE id = $facility",
                                {'district_id': district_id, 'facility': facility_id})
                            res2 = db.query(
                                "SELECT id FROM locations "
                                "WHERE name ilike $name AND type_id = 4"
                                " AND tree_parent_id = $district",
                                {'name': '%%%s%%' % params.subcounty, 'district': district_id})
                            if res2:
                                # we have a sub county in mTrac
                                subcounty_id = res2[0]["id"]
                                db.query(
                                    "UPDATE healthfacilities SET location = $loc, "
                                    "location_name = $loc_name"
                                    " WHERE id = $facility ",
                                    {
                                        'facility': facility_id, 'loc': subcounty_id,
                                        'loc_name': params.subcounty})
                                logging.debug("Set Facility Location: ID:%s Location:%s" % (params.code, subcounty_id))
                            else:
                                # make district catchment area
                                db.query(
                                    "UPDATE healthfacilities SET "
                                    " location = $loc, location_name = $loc_name WHERE id = $facility",
                                    {
                                        'facility': facility_id, 'loc': district_id,
                                        'loc_name': params.subcounty})
                                logging.debug("Set Facility Location: ID:%s Location:%s" % (params.code, district_id))
                        logging.debug("Facility with ID:%s sucessfully created." % params.code)
                    return "Created Facility ID:%s" % params.code
                else:
                    # facility with passed uuid already exists
                    logging.debug("updating facility with ID:%s" % params.code)
                    facility_id = r[0]["id"]
                    db.query(
                        "UPDATE healthfacilities SET "
                        "name = $name, code = $dhis2id, type_id = $type, district = $district, "
                        "is_033b = $is_033b "
                        " WHERE id = $facility ",
                        {
                            'name': params.name, 'dhis2id': params.dhis2id, 'type': type_id,
                            'district': params.district, 'facility': facility_id, 'is_033b': params.is_033b})

                    logging.debug("Set h033b for facility with ID:%s to %s" % (params.code, params.is_033b))
                    d = db.query(
                        "SELECT id FROM locations WHERE lower(name) = $name "
                        "AND type_id = 3", {'name': params.district.lower()})
                    if d:
                        district_id = d[0]["id"]
                        db.query(
                            "UPDATE healthfacilities SET district_id = $district_id "
                            "WHERE id = $facility ", {
                                'facility': facility_id, 'district_id': district_id})
                        res2 = db.query(
                            "SELECT id FROM locations WHERE name ilike $name AND type_id = 4"
                            " AND tree_parent_id = $district",
                            {'name': '%%%s%%' % params.subcounty.strip(), 'district': district_id})
                        if res2:
                            # we have a sub county in mTrac
                            subcounty_id = res2[0]["id"]
                            logging.debug(
                                "Sub county:%s set for facility with ID:%s" %
                                (params.subcounty, params.code))
                            res3 = db.query(
                                "UPDATE  healthfacilities SET location = $loc, location_name = $loc_name "
                                " WHERE id = $facility RETURNING id",
                                {
                                    'facility': facility_id, 'loc':
                                    subcounty_id, 'loc_name': params.subcounty.strip()})
                            if not res3:
                                logging.debug("Set Facility Location: ID:%s Location:%s" % (params.code, subcounty_id))
                        else:
                            # make district catchment area
                            res3 = db.query(
                                "UPDATE healthfacilities SET location = $loc, location_name = $loc_name "
                                "WHERE id = $facility RETURNING id",
                                {
                                    'facility': facility_id, 'loc': district_id,
                                    'loc_name': params.district})
                            if not res3:
                                logging.debug("Set Facility Location: ID:%s Location:%s" % (params.code, district_id))
                        logging.debug("Facility with ID:%s sucessfully updated." % params.code)
                    return "Updated Facility ID:%s" % params.code
            else:
                return "Unsupported type:%s" % params.ftype

    def POST(self):
        params = web.input()
        l = locals()
        del l['self']
        return "Created!"


class ReportForms:
    def GET(self, report_type):
        web.header("Content-Type", "application/json; charset=utf-8")
        res = db.query(
            "SELECT distinct form FROM dhis2_mtrack_indicators_mapping "
            "WHERE dataset=$dataset", {'dataset': report_type})
        ret = []
        for r in res:
            ret.append({'name': r['form']})
        return json.dumps(ret)


class IndicatorHtml:
    def GET(self, report):
        params = web.input(request_id="", has_errors="false")
        # res = db.query(
        #     "SELECT slug, description FROM dhis2_mtrack_indicators_mapping "
        #     "WHERE form=$report ORDER BY form_order", {'report': report})
        # for r in res:

        # XXX Crazy hacks to get values from json body if request_id is passed
        json_body = {}
        htmlStr = ""
        if params.request_id:
            view = "requests_view"
            if params.has_errors == "true":
                view = "rejected_reports_view"  # error messages go in different view

            SQL = "SELECT body, facility, week, year FROM %s WHERE id= $request_id" % view
            res = db.query(
                SQL,
                {'request_id': params.request_id})
            if res:
                rpt = res[0]
                htmlStr += """<input name="report" type="hidden" value="%s"/>""" % report
                htmlStr += """<input name="request_id" id="request_id" type="hidden" value="%s"/>""" % params.request_id
                htmlStr += """<input name="facilitycode" type="hidden" value="%s"/>""" % rpt['facility']
                htmlStr += """<input name="week" type="hidden" value="%sW%s"/>""" % (rpt['year'], rpt['week'])
                try:
                    json_body = json.loads(rpt['body'])
                except:
                    pass
        # import pprint; pprint.pprint(json_body)
        for r in IndicatorsByFormOrder[report]:  # use indicators preloaded in __init__.py
            value = ""
            if json_body:
                for val in json_body['dataValues']:
                    if report in getattr(settings, 'SPECIAL_FORMS', ['mat']):
                        # for the case where a dataElement is shared across indicators, but the categoryOtpionCombo
                        if val['dataElement'] in Indicators[report]:
                            if val['categoryOptionCombo'] == IndicatorsCategoryCombos[report][r['slug']]:
                                value = val['value']
                    else:
                        if val['dataElement'] in Indicators[report]:
                            if r['slug'] == Indicators[report][val['dataElement']]['slug']:
                                value = val['value']
                                # print ">>>>>>>>>>>>>>>>>>>>>>", value
            # XXX Crazy hacks end here

            htmlStr += '<div class="row"><div class="form-group"><label for="%(slug)s" class="col-lg-6 control-label">' % r
            htmlStr += r['description'] + ":</label>"
            htmlStr += """
                            <div class="col-lg-6">
                                <input name="%(slug)s" id="%(slug)s" value="%(value)s" type="text" class="form-control"/>
                            </div>
                        </div>
                    </div>
                    <br/>
            """ % {'slug': r['slug'], 'value': value}
        if not params.request_id:
            htmlStr += """
                        <div class="row">
                        <div class="form-group">
                                <div class="col-lg-offset-6 col-lg-3">
                                    <button class="btn btn-sm btn-primary report_edit_btn" type="submit">Save Report</button>
                                </div>
                            </div>
                        </div>
            """
        return htmlStr


class FacilitySMS:
    def GET(self, facilityid):
        pass

    def POST(self, facilityid):
        params = web.input(role="", sms="")
        send_facility_sms_task.delay(facilityid, params.sms, params.role)
        return "<h4>SMS Queued!</h4>"


class SendBulkSMS:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input(sms_roles=[], msg="", district="", sms_facility="")
        if not params.district or params.district == "0":
            return json.dumps({'message': 'Please select District before sending!'})
        if not params.msg:
            return json.dumps({'message': 'You cannot send an empty message!'})
        if not params.sms_roles:
            return json.dumps({'message': 'Please specify a role or list of roles!'})

        send_bulksms_task.delay(params.msg, params.sms_roles, params.district, params.sms_facility)

        return json.dumps({'message': 'SMS Queued For Submission'})


class SendSMS:
    def POST(self):
        params = web.input(uuid="", sms="")
        post_data = json.dumps({'contacts': [params.uuid], 'text': params.sms})
        try:
            resp = post_request(post_data, '%sbroadcasts.json' % config['api_url'])
            code = "%s" % resp.status_code
            print(resp.text)
        except:
            code = "400"
        if code.startswith("4"):
            return "Failed"
        return "Success"


class RequestDetails:
    def GET(self, request_id):
        rs = db.query(
            "SELECT source, destination, body_pprint(body) as body, "
            "xml_is_well_formed_document(body) as is_xml, "
            "raw_msg, status, week, month, year, facility_name, msisdn, statuscode, errors "
            "FROM requests_view WHERE id = $request_id", {'request_id': request_id})

        html_str = '<table class="table table-striped table-bordered table-hover">'
        html_str += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        if rs:
            ret = rs[0]
            html_str += "<tr><td>Facility</td><td>%s</td></tr>" % ret['facility_name']
            html_str += "<tr><td>Reporter</td><td>%s</td></tr>" % ret['msisdn']
            html_str += "<tr><td>Report</td><td>%s</td></tr>" % ret['raw_msg']
            html_str += "<tr><td>Week</td><td>%sW%s</td></tr>" % (ret['year'], ret['week'])
            html_str += "<tr><td>Status</td><td>%s</td></tr>" % (ret['status'])
            html_str += "<tr><td>StatusCode</td><td>%s</td></tr>" % (ret['statuscode'],)
            html_str += "<tr><td>Errors</td>"
            if ret['errors']:
                html_str += "<td><textarea rows='4' cols='25' wrap='off' readonly>%s</textarea></td></tr>" % (ret['errors'])
            else:
                html_str += "<td></td></tr>"
            if ret['is_xml']:
                html_str += "<tr><td>Body</td><td><textarea rows='10' cols='40' "
                html_str += "wrap='off' readonly>%s</textarea></td></tr>" % ret['body']

            else:
                html_str += "<tr><td>Body</td><td><pre class='language-js'>"
                html_str += "<code class='language-js'>%s<code></pre></td></tr>" % ret['body']

        html_str += "</tbody></table>"
        return html_str


class ServerDetails:
    def GET(self, server_id):
        rs = db.query("SELECT * FROM servers WHERE id = $server_id", {'server_id': server_id})
        html_str = '<table class="table table-striped table-bordered table-hover">'
        html_str += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"

        if rs:
            ret = rs[0]
            html_str += "<tr><td>Name</td><td>%s</td></tr>" % ret['name']
            html_str += "<tr><td>Username</td><td>%s</td></tr>" % ret['username']
            html_str += "<tr><td>Password</td><td>%s</td></tr>" % ret['password']
            html_str += "<tr><td>Data Endpoint</td><td>%s</td></tr>" % ret['url']
            html_str += "<tr><td>Authentication Method</td><td>%s</td></tr>" % ret['auth_method']
            html_str += "<tr><td>Allowed Apps/Sources</td><td>%s</td></tr>" % server_apps(ret['id'])
            html_str += "<tr><td>Start of Submission Period</td><td>%s</td></tr>" % ret['start_submission_period']
            html_str += "<tr><td>End of Submission Period</td><td>%s</td></tr>" % ret['end_submission_period']
            html_str += "<tr><td>XML Response Status XPath</td><td>%s</td></tr>" % ret['xml_response_xpath']
            html_str += "<tr><td>JSON Response Status Path</td><td>%s</td></tr>" % ret['json_response_xpath']
            html_str += "<tr><td>Suspended?</td><td>%s</td></tr>" % ret['suspended']
            html_str += "<tr><td>Parse Responses?</td><td>%s</td></tr>" % ret['parse_responses']
            html_str += "<tr><td>Use SSL?</td><td>%s</td></tr>" % ret['use_ssl']
            html_str += "<tr><td>SSL Client CertKey File Path</td><td>%s</td></tr>" % ret['ssl_client_certkey_file']

        html_str += "</tbody></table>"
        return html_str


class DeleteServer:
    def GET(self, server_id):
        try:
            db.query("DELETE FROM server_allowed_sources WHERE server_id = $id", {'id': server_id})
            db.query("DELETE FROM servers WHERE id = $id", {'id': server_id})
        except:
            return json.dumps({"message": "failed"})
        return json.dumps({"message": "success"})


class DeleteRequest:
    def GET(self, server_id):
        try:
            db.query("DELETE FROM requests WHERE id = $id", {'id': server_id})
        except:
            return json.dumps({"message": "failed"})
        return json.dumps({"message": "success"})
