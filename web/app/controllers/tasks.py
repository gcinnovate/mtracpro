import web
import random
import requests
import json
from celery import Celery
from celeryconfig import BROKER_URL, db_conf, poll_flows, apiv2_endpoint, api_token

MAX_CHUNK_SIZE = 90

db = web.database(
    dbn='postgres',
    user=db_conf['user'],
    pw=db_conf['passwd'],
    db=db_conf['name'],
    host=db_conf['host'],
    port=db_conf['port']
)
# celery -A tasks worker --loglevel=info
app = Celery("mtrackpro", broker=BROKER_URL)


@app.task(name="add_poll_recipients_task")
def add_poll_recipients_task(poll_id, groups=[], districts=[], start_now=False, poll_type="", qn="", d_resp=""):
    print("Gona asynchronously add poll recipients:[{0}]".format(poll_id))
    # format input postgresql style
    groups_str = str([int(x) for x in groups]).replace('[', '{').replace(']', '}').replace('\'', '\"')
    districts_str = str([int(x) for x in districts]).replace('[', '{').replace(']', '}').replace('\'', '\"')

    db.query(
        "INSERT INTO poll_recipients(poll_id, reporter_id) "
        "SELECT %s, id FROM reporters where district_id = "
        "ANY('%s'::INT[]) and groups && '%s'::INT[]" % (
            poll_id, districts_str, groups_str))

    if start_now:
        db.update("UPDATE polls SET start_date = NOW() WHERE id = $id", {'id': poll_id})
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


@app.task(name="start_poll_task")
def start_poll_task():
    pass


@app.task(name="record_poll_response_task")
def record_poll_response_task(poll_id, reporter_id, response, category):
    """ records poll responses from RapidPro """
    # check whether poll is still active
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
