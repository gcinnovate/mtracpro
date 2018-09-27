import web
import datetime
import json
from . import db, require_login, serversByName, formatMsgForAndroid
from app.tools.utils import generate_raw_message, get_reporting_week
from settings import MAPPING, DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, REPORTS_WITH_COMMANDS
from settings import TEXT_INDICATORS
import settings


class EditReport:
    @require_login
    def POST(self, request_id):
        params = web.input(facilitycode="", report="", week="", has_errors="false")
        week = params.week
        facilitycode = params.facilitycode
        report = params.report
        print params.values()

        dataDict = {}
        addCommands = False
        if report in REPORTS_WITH_COMMANDS:
            addCommands = True

        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
            dataValues = []
        else:
            dataValues = ""
        msg = "%s." % report
        for key, val in params.iteritems():
            if key in ('xweek', 'facility', 'district', 'report', 'report_type', 'reporter', 'request_id'):
                continue
            if val.__str__().isdigit() or key in TEXT_INDICATORS:
                    slug = key
                    print "%s=>%s" % (slug, val), MAPPING[slug]
                    dataDict[slug] = val
                    if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                        dataValues.append(
                            {
                                'dataElement': MAPPING[slug]['dhis2_id'],
                                'categoryOptionCombo': MAPPING[slug]['dhis2_combo_id'],
                                'value': val})
                    else:
                        dataValues += (
                            "<dataValue dataElement='%s' categoryOptionCombo="
                            "'%s' value='%s' />\n" %
                            (MAPPING[slug]['dhis2_id'], MAPPING[slug]['dhis2_combo_id'], val))

        if not dataValues and report in getattr(
                settings, 'IRREGULAR_FORMS', ('cases', 'death', 'epc', 'epd')):
            if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                dataValues = []
            else:
                dataValues = DEFAULT_DATA_VALUES[params.form]

        msg += generate_raw_message(db, report, dataDict, addCommands)
        # print "================>", msg

        if facilitycode and dataValues:
            args_dict = {
                'completeDate': datetime.datetime.now().strftime("%Y-%m-%d"),
                'period': week,
                'orgUnit': facilitycode,
                'dataValues': dataValues
            }
            if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                args_dict['dataSet'] = HMIS_033B_DATASET
                args_dict['attributeOptionCombo'] = HMIS_033B_DATASET_ATTR_OPT_COMBO
                payload = json.dumps(args_dict)
            else:
                payload = XML_TEMPLATE % args_dict
            SQL = (
                "UPDATE %s SET body = $body, is_edited = 't', edited_raw_msg = $msg, "
                "updated = NOW(), status='ready' WHERE id = $id ")
            if params.has_errors == "true":
                SQL = SQL % 'rejected_reports'
            else:
                SQL = SQL % 'requests'
            db.query(
                SQL,
                {'body': payload, 'id': request_id, 'msg': msg})
            return 'Report successfully edited to "%s"' % msg

        return "Message was not edited"


class ReportingWeek:
    def GET(self):
        web.header('Content-Type', 'application/json')
        return json.dumps({"period": get_reporting_week(datetime.datetime.now())})


class ReporterHistoryApi:
    def GET(self, phonenumber):
        params = web.input(sdate="", report_type="")
        web.header('Content-Type', 'application/json')
        ret = []
        SQL = (
            "SELECT id, raw_msg, week, year, to_char(created, 'yyyy-mm-dd HH:MI') as created, "
            "body, report_type FROM requests_view WHERE msisdn = $phone AND source = $source ")
        if params.sdate:
            SQL += " AND created >= $sdate "
        if params.report_type:
            SQL += " AND report_type = $report_type "
        SQL += " ORDER BY id DESC LIMIT 10"
        ret = []
        res = db.query(
            SQL,
            {
                'phone': phonenumber, 'sdate': params.sdate,
                'report_type': params.report_type, 'source': serversByName['mTracPro_android']})
        if res:
            for r in res:
                ret.append({
                    "id": r.id,
                    "rawMsg": r.raw_msg,
                    "date": r.created,
                    "details": formatMsgForAndroid(r.body, r.report_type),
                    "period": "%sW%s" % (r.year, r.week)})
        return json.dumps(ret)
