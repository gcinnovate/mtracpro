import json
import logging
from . import db
import web
# from settings import config
from app.tools.utils import get_basic_auth_credentials, auth_user, get_webhook_msg

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
                "FROM reporters_view4 WHERE replace(telephone, '+', '') = $tel "
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
        htmlStr = ""
        res = db.query(
            "SELECT slug, description FROM dhis2_mtrack_indicators_mapping "
            "WHERE form=$report ORDER BY form_order", {'report': report})
        for r in res:
            htmlStr += '<div class="form-group"><label for="%(slug)s" class="col-lg-6 control-label">' % r
            htmlStr += r['description'] + ":</label>"
            htmlStr += """
                            <div class="col-lg-6">
                                <input name="%(slug)s" id="%(slug)s" type="text" class="form-control"/>
                            </div>
                        </div>
            """ % r
        htmlStr += """
                       <div class="form-group">
                            <div class="col-lg-offset-6 col-lg-3">
                                <button class="btn btn-sm btn-primary" type="submit">Save Report</button>
                            </div>
                        </div>
        """
        return htmlStr
