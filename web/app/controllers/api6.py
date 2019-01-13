import json
import web
import datetime
from . import db, serversByName
from settings import config
from settings import USE_OLD_WEBHOOKS
# from app.tools.utils import get_webhook_msg_old
from app.tools.utils import get_reporting_week, get_request
from app.tools.utils import queue_rejected_reports
from settings import MAPPING, DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, TEXT_INDICATORS


class QueueRejectedReports:
    def get_last_response_message(self, contact_uuid):
        start_of_today = datetime.datetime.now().strftime("%Y-%m-%dT00:00:00.00")
        try:
            resp = get_request(
                config['api_url'] + "messages.json?contact=%s&after=%s" % (contact_uuid, start_of_today))
            messages = json.loads(resp.text)
            print(messages)
        except Exception as e:
            print(str(e))
            messages = {}
        if 'results' in messages:
            msgs = list(messages['results'])
            if msgs:
                return msgs[0]['text']
        return ""

    def GET(self):
        return json.dumps({"status": "success"})

    def POST(self):
        params = web.input(
            facilitycode="", form="", district="", msisdn="",
            raw_msg="", report_type="", facility="", reporter_type="", uuid="")
        extras = {'reporter_type': params.reporter_type}
        # values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
            dataValues = []
        else:
            dataValues = ""
        print("FACILITYCODE:", params.facilitycode, "==>", params.facility, "UUID:", params.uuid)
        if params.facilitycode:
            if not USE_OLD_WEBHOOKS:
                values = json.loads(web.data())
                results = values.get('results', {})
                for key, v in results.iteritems():
                    val = v.get('value')
                    try:
                        val = int(float(val))
                    except:
                        pass
                    label = v.get('name')
                    slug = "%s_%s" % (params.form, label)
                    if val.__str__().isdigit() or slug in TEXT_INDICATORS:
                        if not(val) and params.form in ['cases', 'death', 'epc', 'epd']:
                            if label not in params.raw_msg.lower():
                                continue  # skip zero values for cases, death, epc and epd
                        print("%s=>%s" % (slug, val), MAPPING[slug])
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
            else:
                values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
                for v in values:
                    val = v.get('value')
                    try:
                        val = int(float(val))
                    except:
                        pass
                    label = v.get('label')
                    slug = "%s_%s" % (params.form, label)
                    if val.__str__().isdigit() or slug in TEXT_INDICATORS:
                        if not(val) and params.form in ['cases', 'death']:
                            if label not in params.raw_msg.lower():
                                continue  # skip zero values for cases and death
                        print("%s=>%s" % (slug, val), MAPPING[slug])
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
                    args_dict['attributeOptionCombo'] = HMIS_033B_DATASET_ATTR_OPT_COMBO
                    payload = json.dumps(args_dict)
                else:
                    payload = XML_TEMPLATE % args_dict
                year, week = tuple(args_dict['period'].split('W'))
                print(payload)
                extra_params = {
                    'week': week, 'year': year, 'msisdn': params.msisdn,
                    'facility': params.facilitycode, 'raw_msg': params.raw_msg,
                    'district': params.district, 'report_type': params.report_type,
                    # 'source': config['dispatcher2_source'],
                    # 'destination': config['dispatcher2_destination'],
                    'source': serversByName[config['dispatcher2_source']],
                    'destination': serversByName[config['dispatcher2_destination']],
                    'extras': json.dumps(extras),
                    'response': self.get_last_response_message(params.uuid),
                    'status': config.get('default-queue-status', 'pending')}
                # now ready to queue to DB for pushing to DHIS2
                # resp = queue_submission(serverid, post_xml, year, week)
                print(extra_params)
                if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                    extra_params['ctype'] = 'json'
                    # resp = post_request_to_dispatcher2(
                    #    payload, params=extra_params, ctype='json')
                    extra_params['body'] = payload
                    queue_rejected_reports(db, extra_params)
                else:
                    extra_params['ctype'] = 'xml'
                    # resp = post_request_to_dispatcher2(payload, params=extra_params)
                    extra_params['body'] = payload
                    queue_rejected_reports(db, extra_params)
                # print "Resp:", resp

        return json.dumps({"status": "success"})
