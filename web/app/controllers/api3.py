import web
import datetime
import json
from . import db, require_login
from app.tools.utils import generate_raw_message, get_reporting_week
from settings import MAPPING, DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, REPORTS_WITH_COMMANDS


class EditReport:
    @require_login
    def POST(self, request_id):
        params = web.input(facilitycode="", report="", week="")
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
            if val.__str__().isdigit():
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

        if not dataValues and report in ('cases', 'death'):
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
            db.query(
                "UPDATE requests SET body = $body, is_edited = 't', edited_raw_msg = $msg, "
                "updated = NOW(), status='ready' WHERE id = $id ",
                {'body': payload, 'id': request_id, 'msg': msg})
            return 'Report successfully edited to "%s"' % msg

        return "Message was not edited"


class ReportingWeek:
    def GET(self):
        web.header('Content-Type', 'application/json')
        return json.dumps({"period": get_reporting_week(datetime.datetime.now())})
