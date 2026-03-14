import json
import web
import datetime
from . import db, serversByName, IndicatorMapping, notifyingParties, allDistrictsByName
from webapp.settings import config
from webapp.settings import USE_OLD_WEBHOOKS
# from app.tools.utils import get_webhook_msg_old
from webapp.app.tools.utils import (
    get_reporting_week, get_request, queue_rejected_reports)
from webapp.settings import DEFAULT_DATA_VALUES, XML_TEMPLATE, PREFERED_DHIS2_CONTENT_TYPE
from webapp.settings import HMIS_033B_DATASET, HMIS_033B_DATASET_ATTR_OPT_COMBO, TEXT_INDICATORS
from .tasks import sendsms_to_uuids_task


def send_threshold_alert(msg, district):
    try:
        threshold_alert_contacts = notifyingParties[allDistrictsByName[district]]['threshold_alert_contacts']
    except:
        threshold_alert_contacts = []
    if threshold_alert_contacts:
        sendsms_to_uuids_task.delay(threshold_alert_contacts, msg)


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

    def POST(self):
        params = web.input(facilitycode="", form="", msisdn="", reporter_type="")
        extras = {'reporter_type': params.reporter_type}
        # values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
        if PREFERED_DHIS2_CONTENT_TYPE == 'json':
            dataValues = []
        else:
            dataValues = ""
            
        if not USE_OLD_WEBHOOKS:
            values = json.loads(web.data())
            results = values.get('results', {})
            contact = values.get('contact', {})
            facilitycode = contact['facilitycode'] if 'facilitycode' in contact else ''
            if not facilitycode:
                return json.dumps({'status': 'error', 'message': 'facilitycode is empty'})
            raw_msg = results['report']['value'] if results.get('report') is not None else ''
            facility = contact['facility'] if 'facility' in contact else ''
            district = contact['district'] if 'district' in contact else ''
            msisdn = contact['urn'] if 'urn' in contact else ""
            reporter_name = contact['name'] if 'name' in contact else ''
            uuid = contact['uuid'] if 'uuid' in contact else ''
            flow = values.get('flow', {})
            report_type = flow['report_type'] if 'report_type' in flow else ''
            if not report_type:
                return json.dumps({'status': 'error', 'message': 'report_type is empty'})

            thresholds_list = []
            for key, v in results.items():
                val = v.get('value')
                try:
                    val = int(float(val))
                except:
                    pass
                label = key
                slug = "%s_%s" % (report_type, label)
                if val.__str__().isdigit() or slug in TEXT_INDICATORS:
                    if not(val) and report_type in ['cases', 'death', 'epc', 'epd']:
                        if label not in raw_msg.lower():
                            continue  # skip zero values for cases, death, epc and epd
                    if slug not in IndicatorMapping:
                        continue
                    # XXX check thresholds here
                    if IndicatorMapping[slug]['threshold']:
                        try:
                            threshold = int(float(IndicatorMapping[slug]['threshold']))
                            if val > threshold:
                                thresholds_list.append('{} {}'.format(val, IndicatorMapping[slug]['descr']))
                        except:
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
            alert_message = "Thresholds alert: {0} ({1}) of {2} - {3} district reported:\n".format(
                reporter_name, msisdn, facility, district)
            alert_message += '\n'.join(thresholds_list)
            send_threshold_alert(alert_message, district)
            print(alert_message)

        else:
            values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
            results = values.get('results', {})
            contact = values.get('contact', {})
            uuid = contact['uuid'] if 'uuid' in contact else ''
            raw_msg = results['report']['value'] if results.get('report') is not None else ''
            facility = contact['facility'] if 'facility' in contact else ''
            district = contact['district'] if 'district' in contact else ''
            msisdn = contact['urn'] if 'urn' in contact else ''
            facilitycode = contact['facilitycode'] if 'facilitycode' in contact else ''
            if not facilitycode:
                return json.dumps({'status': 'error', 'message': 'facilitycode is empty'})
            flow = values.get('flow', {})
            report_type = flow['report_type'] if 'report_type' in flow else ''
            if not report_type:
                return json.dumps({'status': 'error', 'message': 'report_type is empty'})
            reporter_name = contact['name'] if 'name' in contact else ''
            thresholds_list = []
            for v in values:
                val = v.get('value')
                try:
                    val = int(float(val))
                except:
                    pass
                label = v.get('label')
                slug = "%s_%s" % (report_type, label)
                if val.__str__().isdigit() or slug in TEXT_INDICATORS:
                    if not(val) and report_type in ['cases', 'death']:
                        if label not in raw_msg.lower():
                            continue  # skip zero values for cases and death
                    if slug not in IndicatorMapping:
                        continue
                    # XXX check thresholds here
                    if IndicatorMapping[slug]['threshold']:
                        try:
                            threshold = int(float(IndicatorMapping[slug]['threshold']))
                            if val > threshold:
                                thresholds_list.append('{} {}'.format(val, IndicatorMapping[slug]['descr']))
                        except:
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
            alert_message = "Thresholds alert: {0} ({1}) of {2} - {3} district reported:\n".format(
                reporter_name, msisdn, facility, district)
            alert_message += '\n'.join(thresholds_list)
            send_threshold_alert(alert_message, district)
            print(alert_message)

        if not dataValues and report_type in ('cases', 'death'):
            if PREFERED_DHIS2_CONTENT_TYPE == 'json':
                dataValues = []
            else:
                dataValues = DEFAULT_DATA_VALUES[report_type]

        if dataValues:
            args_dict = {
                'completeDate': datetime.datetime.now().strftime("%Y-%m-%d"),
                'period': get_reporting_week(datetime.datetime.now()),
                'orgUnit': facilitycode,
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
                'week': week, 'year': year, 'msisdn': msisdn,
                'facility': facilitycode, 'raw_msg': raw_msg,
                'district': district, 'report_type': report_type,
                # 'source': config['dispatcher2_source'],
                # 'destination': config['dispatcher2_destination'],
                'source': serversByName[config['dispatcher2_source']],
                'destination': serversByName[config['dispatcher2_destination']],
                'extras': json.dumps(extras),
                'response': self.get_last_response_message(uuid),
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
