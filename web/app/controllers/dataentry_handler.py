import web
import datetime
import json
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import get_reporting_week, post_request_to_dispatcher2, generate_raw_message
from settings import MAPPING, DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, REPORTS_WITH_COMMANDS


class DataEntry:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        session = get_session()
        if session.role == 'District User':
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') "
                "AND name = '%s'" % session.username.capitalize())
        else:
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")

        districts = db.query(districts_SQL)
        rweek = get_reporting_week(datetime.datetime.now())
        year, week = rweek.split('W')
        reporting_weeks = []
        for i in range(1, int(week) + 1):
            reporting_weeks.append("%sW%s" % (year, i))

        l = locals()
        del l['self']
        return render.dataentry(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input()
        week = params.week
        facility = params.facility
        facilitycode = ""
        res = db.query("SELECT dhis2id FROM facilities WHERE id = $id", {'id': facility})
        if res:
            facilitycode = res[0]['dhis2id']

        report = params.report
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
            if key in ('week', 'facility', 'district', 'report', 'report_type', 'reporter', 'csrf_token'):
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
            year, _week = tuple(args_dict['period'].split('W'))
            print payload
            extra_params = {
                'week': _week, 'year': year, 'msisdn': params.reporter,
                'facility': facilitycode, 'raw_msg': msg,
                'district': params.district, 'report_type': params.report}
            # now ready to queue to DB for pushing to DHIS2
            # resp = queue_submission(serverid, post_xml, year, week)
            print extra_params
            if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                resp = post_request_to_dispatcher2(
                    payload, params=extra_params, ctype='application/json')
            else:
                resp = post_request_to_dispatcher2(payload, params=extra_params)
            print "Resp:", resp

        with db.transaction():
            pass
        l = locals()
        del l['self']
        return render.dataentry(**l)
