import json
import web
import datetime
from . import db
# from settings import config, SMS_OFFSET_TIME
from app.tools.utils import get_basic_auth_credentials, auth_user, format_msisdn
# from app.tools.utils import get_location_role_reporters, queue_schedule, log_schedule, update_queued_sms
from app.tools.utils import parse_message, post_request_to_dispatcher2, get_reporting_week
from settings import MAPPING, DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET


def get_webhook_msg(params, label='msg'):
    """Returns value of given lable from rapidpro webhook data"""
    values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
    msg_list = [v.get('value') for v in values if v.get('label') == label]
    if msg_list:
        msg = msg_list[0].strip()
        if msg.startswith('.'):
            msg = msg[1:]
        return msg
    return ""


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
            "SELECT telephone FROM reporters WHERE id IN "
            "(SELECT reporter_id FROM reporter_healthfacilities WHERE facility_id=$id)",
            {'id': id})
        if rs:
            pass
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


class DistributionRecord:
    def GET(self, id):
        r = db.query("SELECT * FROM distribution_log_w2sc_view WHERE id = $id", {'id': id})
        html_str = '<table class="table table-striped table-bordered table-hover">'
        html_str += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        if r:
            ret = r[0]
            html_str += "<tr><td>District</td><td>%s</td></tr>" % ret['district']
            html_str += "<tr><td>Sub County</td><td>%s</td></tr>" % ret['destination']
            html_str += "<tr><td>Release Order</td><td>%s</td></tr>" % ret['release_order']
            html_str += "<tr><td>Waybill</td><td>%s</td></tr>" % ret['waybill']
            html_str += "<tr><td>Quantity</td><td>Bales: %s, Nets: %s</td></tr>" % (ret['quantity_bales'], ret['quantity_nets'])
            html_str += "<tr><td>Warehouse</td><td>%s (%s)</td></tr>" % (ret['warehouse'], ret['branch'])
            html_str += "<tr><td>Departure Date</td><td>%s</td></tr>" % ret['departure_date']
            html_str += "<tr><td>Departure Time</td><td>%s</td></tr>" % ret['departure_time']
            html_str += "<tr><td>Quantity Received</td><td>%s</td></tr>" % ret['quantity_received']
            html_str += "<tr><td>Driver</td><td>Name: %s, Tel:%s</td></tr>" % (ret['delivered_by'], ret['telephone'])
            html_str += "<tr><td>Remarks</td><td>%s</td></tr>" % ret['remarks']
            if ret['is_delivered']:
                label = "<span class='label label-primary'>Delivered</span>"
                html_str += "<tr><td>Delivered?</td><td>%s</td></tr>" % label
            else:
                label = "<span class='label label-danger'>Not Delivered</span>"
                html_str += "<tr><td>Delivered?</td><td>%s</td></tr>" % label
        html_str += "</tbody></table>"
        return html_str


class Cases:
    def GET(self):
        return json.dumps({"message": "0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"})

    def POST(self):
        params = web.input()
        values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
        msg_list = [v.get('value') for v in values if v.get('label') == 'msg']
        if msg_list:
            msg = msg_list[0]
            if msg.startswith('.'):
                msg = msg[1:]
        # print msg
        message = parse_message(msg, 'cases')

        return json.dumps({"message": message})


class Deaths:
    def GET(self):
        return json.dumps({"message": "0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"})

    def POST(self):
        params = web.input()
        values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
        msg_list = [v.get('value') for v in values if v.get('label') == 'msg']
        if msg_list:
            msg = msg_list[0]
            if msg.startswith('.'):
                msg = msg[1:]
        # print msg
        message = parse_message(msg, 'death')

        return json.dumps({"message": message})


class Test:
    def GET(self):
        return json.dumps({"message": "1.2.3"})

    def POST(self):
        return json.dumps({"message": "1+0+3+4+5+6+7+8+9+10+11+12+13+14+15+16.0.0"})


class Dhis2Queue:
    def GET(self):
        return json.dumps({"status": "success"})

    def POST(self):
        params = web.input(
            facilitycode="", form="", district="", msisdn="", raw_msg="", report_type="")
        values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
            dataValues = []
        else:
            dataValues = ""

        if params.facilitycode:
            for v in values:
                val = v.get('value')
                try:
                    val = int(float(val))
                except:
                    pass
                label = v.get('label')
                if val and val.__str__().isdigit():
                    slug = "%s_%s" % (params.form, label)
                    print "%s=>%s" % (slug, val), MAPPING[slug]
                    if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                        dataValues.append(
                            {
                                'dataElement': MAPPING[slug]['dhis2_uuid'],
                                'categoryOptionCombo': MAPPING[slug]['dhis2_combo_id'],
                                'value': val})
                    else:
                        dataValues += (
                            "<dataValue dataElement='%s' categoryOptionCombo="
                            "'%s' value='%s' />\n" %
                            (MAPPING[slug]['dhis2_uuid'], MAPPING[slug]['dhis2_combo_id'], val))

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
                    args_dict['dataSet'] = HMIS_033B_DATASET
                    payload = json.dumps(args_dict)
                else:
                    payload = XML_TEMPLATE % args_dict
                year, week = tuple(args_dict['period'].split('W'))
                print payload
                extra_params = {
                    'week': week, 'year': year, 'msisdn': params.msisdn,
                    'facility': params.facilitycode, 'raw_msg': params.raw_msg,
                    'distrcit': params.district, 'report_type': params.report_type}
                # now ready to queue to DB for pushing to DHIS2
                # resp = queue_submission(serverid, post_xml, year, week)
                print extra_params
                if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                    resp = post_request_to_dispatcher2(
                        payload, params=extra_params, ctype='application/json')
                else:
                    resp = post_request_to_dispatcher2(payload, params=extra_params)
                print "Resp:", resp

        return json.dumps({"status": "success"})