import web
import datetime
import json
from . import csrf_protected, db, require_login, render, get_session, serversByName, IndicatorMapping
from settings import config
from app.tools.utils import get_reporting_week, generate_raw_message  # ,post_request_to_dispatcher2
from app.tools.utils import queue_request
from settings import DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, REPORTS_WITH_COMMANDS
from settings import TEXT_INDICATORS


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
        hmis_033b_dataset = HMIS_033B_DATASET

        l = locals()
        del l['self']
        return render.dataentry(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(districtname="")
        extras = {}
        week = params.week
        facility = params.facility
        facilitycode = ""
        res = db.query("SELECT code FROM healthfacilities WHERE id = $id", {'id': facility})
        if res:
            facilitycode = res[0]['code']

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
            if val.__str__().isdigit() or key in TEXT_INDICATORS:
                    slug = key
                    print("%s=>%s" % (slug, val), IndicatorMapping[slug])
                    dataDict[slug] = val
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

        if not dataValues and report in ('cases', 'death'):
            if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                dataValues = []
            else:
                dataValues = DEFAULT_DATA_VALUES[params.form]

        msg += generate_raw_message(db, report, dataDict, addCommands)
        # print "================>", msg

        with db.transaction():
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
                print(payload)
                extra_params = {
                    'week': _week, 'year': year, 'msisdn': params.reporter,
                    'facility': facilitycode, 'raw_msg': msg,
                    'district': params.districtname, 'report_type': params.report,
                    'source': serversByName[config['dispatcher2_source']],
                    'destination': serversByName[config['dispatcher2_destination']],
                    'extras': json.dumps(extras),
                    'status': config.get('default-queue-status', 'pending'),
                    'body': payload}
                # now ready to queue to DB for pushing to DHIS2
                # resp = queue_submission(serverid, post_xml, year, week)
                print(extra_params)
                if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                    extra_params['ctype'] = 'json'
                    # resp = post_request_to_dispatcher2(
                    #    payload, params=extra_params, ctype='application/json')
                    queue_request(db, extra_params)
                else:
                    extra_params['ctype'] = 'xml'
                    queue_request(db, extra_params)
                    # resp = post_request_to_dispatcher2(payload, params=extra_params)
                # print "Resp:", resp
                return web.seeother("/dataentry")

        l = locals()
        del l['self']
        return render.dataentry(**l)
