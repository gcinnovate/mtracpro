# from __future__ import absolute_import
import web
import random
import base64
import requests
import json
from celery import Celery
from celeryconfig import BROKER_URL, db_conf, poll_flows, apiv2_endpoint, api_token, config

MAX_CHUNK_SIZE = 90

# db1 = web.database(
#     dbn='postgres',
#     user=db_conf['user'],
#     pw=db_conf['passwd'],
#     db=db_conf['name'],
#     host=db_conf['host'],
#     port=db_conf['port']
# )
# celery -A tasks worker --loglevel=info
app = Celery("mtrackpro", broker=BROKER_URL)


@app.task(name="add_poll_recipients_task")
def add_poll_recipients_task(poll_id, groups=[], districts=[], start_now=False, poll_type="", qn="", d_resp=""):
    print("Gona asynchronously add poll recipients:[{0}]".format(poll_id))
    db = web.database(dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], host=db_conf['host'], port=db_conf['port'])
    # format input postgresql style
    groups_str = str([int(x) for x in groups]).replace('[', '{').replace(']', '}').replace('\'', '\"')
    districts_str = str([int(x) for x in districts]).replace('[', '{').replace(']', '}').replace('\'', '\"')

    db.query(
        "INSERT INTO poll_recipients(poll_id, reporter_id) "
        "SELECT %s, id FROM reporters where district_id = "
        "ANY('%s'::INT[]) and groups && '%s'::INT[]" % (
            poll_id, districts_str, groups_str))

    if start_now:
        db.query("UPDATE polls SET start_date = NOW() WHERE id = $id", {'id': poll_id})
        rs = db.query(
            "SELECT array_agg(uuid) uuids FROM reporters WHERE id IN ("
            "SELECT reporter_id FROM poll_recipients WHERE poll_id = %s) " % (poll_id))
        if rs:
            recipient_uuids = list(rs[0]['uuids'])
            if poll_type in poll_flows:
                flow_uuid = random.choice(poll_flows[poll_type])
                flow_starts_endpoint = apiv2_endpoint + "flow_starts.json"
                contacts_len = len(recipient_uuids)
                j = 0
                print("Starting {0} Contacts in Flow [uuid:{1}]".format(contacts_len, flow_uuid))
                for i in range(0, contacts_len + MAX_CHUNK_SIZE, MAX_CHUNK_SIZE)[1:]:  # want to finsh batch right away
                    chunk = recipient_uuids[j:i]
                    params = {
                        'flow': flow_uuid,
                        'contacts': chunk,
                        'extra': {
                            'poll_id': poll_id,
                            'question': qn,
                            'default_response': d_resp
                        }
                    }
                    post_data = json.dumps(params)
                    try:
                        requests.post(flow_starts_endpoint, post_data, headers={
                            'Content-type': 'application/json',
                            'Authorization': 'Token %s' % api_token})
                        # print("Flow Start Response: ", resp.text)
                    except:
                        print("ERROR Startig Flow [uuid: {0}]".format(flow_uuid))
                    j = i
                print("Finished Starting Contacts in Flow [uuid:{0}]".format(flow_uuid))
    try:
        db._ctx.db.close()
    except:
        pass


@app.task(name="start_poll_task")
def start_poll_task(poll_id):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    res = db.query(
        "SELECT question, default_response, type FROM polls WHERE id = $id ", {'id': poll_id})
    if res:
        poll = res[0]
        qn = poll['question']
        d_resp = poll['default_response']
        poll_type = poll['type']

        rs = db.query(
            "SELECT array_agg(uuid) uuids FROM reporters WHERE id IN ("
            "SELECT reporter_id FROM poll_recipients WHERE poll_id = %s) " % (poll_id))
        if rs:
            recipient_uuids = list(rs[0]['uuids'])
            if poll_type in poll_flows:
                flow_uuid = random.choice(poll_flows[poll_type])
                flow_starts_endpoint = apiv2_endpoint + "flow_starts.json"
                contacts_len = len(recipient_uuids)
                j = 0
                print("Starting {0} Contacts in Flow [uuid:{1}]".format(contacts_len, flow_uuid))
                for i in range(0, contacts_len + MAX_CHUNK_SIZE, MAX_CHUNK_SIZE)[1:]:  # want to finsh batch right away
                    chunk = recipient_uuids[j:i]
                    params = {
                        'flow': flow_uuid,
                        'contacts': chunk,
                        'extra': {
                            'poll_id': poll_id,
                            'question': qn,
                            'default_response': d_resp
                        }
                    }
                    post_data = json.dumps(params)
                    try:
                        requests.post(flow_starts_endpoint, post_data, headers={
                            'Content-type': 'application/json',
                            'Authorization': 'Token %s' % api_token})
                        # print("Flow Start Response: ", resp.text)
                    except:
                        print("ERROR Startig Flow [uuid: {0}]".format(flow_uuid))
                    j = i
                db.query("UPDATE polls set start_date = NOW() WHERE id=$id", {'id': poll_id})
                print("Finished Starting Contacts in Flow [uuid:{0}]".format(flow_uuid))
    try:
        db._ctx.db.close()
    except:
        pass


@app.task(name="record_poll_response_task")
def record_poll_response_task(poll_id, reporter_id, response, category):
    """ records poll responses from RapidPro """
    # check whether poll is still active
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    rs = db.query(
        "SELECT CASE WHEN end_date IS NOT NULL THEN end_date > NOW() "
        " ELSE TRUE END AS active FROM polls WHERE id = $id", {'id': poll_id})
    if rs:
        active = rs[0]['active']
        if active:
            db.query(
                "INSERT INTO poll_responses (poll_id, reporter_id, message, category) "
                "VALUES($poll_id, $reporter_id, $message, $category)", {
                    'poll_id': poll_id, 'reporter_id': reporter_id,
                    'message': response, 'category': category})


@app.task(name="sendsms_to_uuids")
def sendsms_to_uuids(uuid_list, msg):
    broadcasts_endpoint = apiv2_endpoint + "broadcasts.json"
    contacts_len = len(uuid_list)
    j = 0
    print("Starting Broadcast to {0} Contacts ".format(contacts_len))
    for i in range(0, contacts_len + MAX_CHUNK_SIZE, MAX_CHUNK_SIZE)[1:]:
        chunk = uuid_list[j:i]
        params = {
            'contacts': chunk,
            'text': msg
        }
        post_data = json.dumps(params)
        try:
            requests.post(broadcasts_endpoint, post_data, headers={
                'Content-type': 'application/json',
                'Authorization': 'Token %s' % api_token})
            # print("Broadcast Response: ", resp.text)
        except:
            print("ERROR Sending Broadcast")
        j = i
    print("Finished Broadcast of {0} Contacts".format(contacts_len))


@app.task(name="send_bulksms_task")
def send_bulksms_task(msg, sms_roles=[], district="", facility="", check_districts=True):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    SQL = (
        "SELECT array_agg(uuid) uuids FROM reporters_view WHERE uuid <> ''  "
    )
    if check_districts:
        if district:
            SQL += " AND district_id = ANY($district::INT[]) "
    if facility:
        SQL += " AND facilityid=$facility "
    if sms_roles:
        SQL += " AND role SIMILAR TO $role "
    res = db.query(SQL, {
        'district': str(district).replace(
            '[', '{').replace(']', '}').replace("\'", '\"').replace('u', ''),
        'facility': facility,
        'role': '%%(%s)%%' % '|'.join(sms_roles)})

    if res:
        recipient_uuids = list(res[0]['uuids'])
        sendsms_to_uuids(recipient_uuids, msg)
    try:
        db._ctx.db.close()
    except:
        pass


@app.task(name="send_facility_sms_task")
def send_facility_sms_task(facilityid, msg, role=""):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    SQL = (
        "SELECT array_agg(uuid) uuids FROM reporters_view WHERE uuid <> '' AND facilityid=$fid "
    )
    if role:
        SQL += (" AND role like $role ")
    res = db.query(SQL, {'fid': facilityid, 'role': '%%%s%%' % role})
    if res:
        uuids = res[0]['uuids']
        if uuids:
            recipient_uuids = list(uuids)
            sendsms_to_uuids(recipient_uuids, msg)
    try:
        db._ctx.db.close()
    except:
        pass


@app.task(name="sendsms_to_uuids_task")
def sendsms_to_uuids_task(uuid_list, msg):
    sendsms_to_uuids(uuid_list, msg)


@app.task(name="queue_in_dispatcher2")
def queue_in_dispatcher2(data, url=config['dispatcher2_queue_url'], ctype="json", params={}):
    coded = base64.b64encode(
        "%s:%s" % (config['dispatcher2_username'], config['dispatcher2_password']))
    if 'xml' in ctype:
        ct = 'text/xml'
    elif 'json' in ctype:
        ct = 'application/json'
    else:
        ct = 'text/plain'
    response = requests.post(
        url, data=data, headers={
            'Content-Type': ct,
            'Authorization': 'Basic ' + coded},
        verify=False, params=params  # , cert=config['dispatcher2_certkey_file']
    )
    return response


@app.task(name="invalidate_older_similar_reports")
def invalidate_older_similar_reports(reporter, report_type, year, week, report_id):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    db.query(
        "UPDATE requests SET status = 'canceled' WHERE msisdn=$reporter AND "
        "report_type = $rtype AND year=$year AND week = $week AND id != $id", {
            'reporter': reporter,
            'rtype': report_type,
            'year': '{0}'.format(year),
            'week': '{0}'.format(week),
            'id': report_id
        })
    try:
        db._ctx.db.close()
    except:
        pass


@app.task(name="tasks.post_request_to_rapidpro")
def post_request_to_rapidpro(url, data):
    try:
        requests.post(url, data, headers={
            'Content-type': 'application/json',
            'Authorization': 'Token %s' % api_token})
    except:
        print("Failed to POST request to RapidPro [url: {0}] Data: {1}".format(url, data))
