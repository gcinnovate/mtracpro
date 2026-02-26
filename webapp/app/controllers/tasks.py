# from __future__ import absolute_import
import web
import random
import base64
import requests
from requests.auth import HTTPBasicAuth
import json
import pyexcel as pe
import os
import re
import phonenumbers
import logging
import math
import tempfile
import psycopg2
import psycopg2.extras
from string import Template
from webapp.celery_app import app
from .celeryconfig import (
    db_conf, poll_flows, apiv2_endpoint, api_token, config,
    SMB_SERVER_IP, SMB_SERVER_NAME, SMB_USER, SMB_PASSWORD, SMB_DOMAIN_NAME,
    SMB_CLIENT_HOSTNAME, SMB_SHARED_FOLDER, SMB_PORT)

from smb.SMBConnection import SMBConnection

MAX_CHUNK_SIZE = 90

# db1 = web.database(
#     dbn='postgres',
#     user=db_conf['user'],
#     pw=db_conf['passwd'],
#     db=db_conf['name'],
#     host=db_conf['host'],
#     port=db_conf['port']
# )
# celery -A webapp.celery_app:app worker --loglevel=info


def update_user_bulksms_limits(db_conn, user, msg, recipient_count):
    sms_in_msg = math.ceil(len(msg)/ 150)
    number_of_sms = sms_in_msg * recipient_count
    res = db_conn.query(
        "SELECT sms_queued FROM bulksms_limits "
        "WHERE user_id = $user AND day = CURRENT_DATE",{'user': user})
    if res:
        db_conn.query(
            "UPDATE bulksms_limits SET sms_queued = sms_queued + $number_of_sms "
            "WHERE user_id = $user AND day = CURRENT_DATE",
            {'user': user, 'number_of_sms': number_of_sms})
    else:
        db_conn.query(
            "INSERT INTO bulksms_limits (user_id, day, sms_queued) "
        "VALUES ($user, CURRENT_DATE, $number_of_sms)",
            {'user': user, 'number_of_sms': number_of_sms})



def read_remote_samba_file(filename, suffix='.xlsx'):
    """ Read remote samba file, and suffix is appened to filename of returned object """
    try:
        conn = SMBConnection(
            SMB_USER, SMB_PASSWORD, SMB_CLIENT_HOSTNAME, SMB_SERVER_NAME,
            domain=SMB_DOMAIN_NAME, use_ntlm_v2=True, is_direct_tcp=True)
        conn.connect(SMB_SERVER_IP, SMB_PORT)
        file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        file_attributes, filesize = conn.retrieveFile(SMB_SHARED_FOLDER, filename, file_obj)
        return file_obj
    except:
        return None


def delete_remote_samba_file(file_name):
    try:
        conn = SMBConnection(
            SMB_USER, SMB_PASSWORD, SMB_CLIENT_HOSTNAME, SMB_SERVER_NAME,
            domain=SMB_DOMAIN_NAME, use_ntlm_v2=True, is_direct_tcp=True)
        conn.connect(SMB_SERVER_IP, SMB_PORT)
        conn.deleteFiles(SMB_SHARED_FOLDER, file_name)
        return True
    except:
        return False


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    if not msisdn and len(msisdn) < 10:
        return None
    msisdn = msisdn.replace(' ', '')
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)


def get_url(url, payload={}):
    res = requests.get(url, params=payload, auth=HTTPBasicAuth(
        config['dhis2_user'], config['dhis2_passwd']))
    return res.text


def get_facility_details(facilityJson):
    is_033b = 'f'
    level = ""
    owner = ""
    is_active = True
    # parent = facilityJson["parent"]["name"].replace('Subcounty', '').strip()
    parent = re.sub(
        'Subcounty.*$|Sub\ County.*$', "", facilityJson["parent"]["name"],
        flags=re.IGNORECASE).strip()
    district_url = "%s/%s.json?fields=id,name,parent[id,name,parent[id,name]]" % (config["orgunits_url"], facilityJson["parent"]["id"])
    print(district_url)
    districtJson = get_url(district_url)
    # district = json.loads(districtJson)["parent"]["name"].replace('District', '').strip()
    print(districtJson)
    district = re.sub(
        'District.*$', "",
        json.loads(districtJson)["parent"]["parent"]["name"], flags=re.IGNORECASE).strip()

    orgunitGroups = facilityJson["organisationUnitGroups"]
    orgunitGroupsIds = ["%s" % k["id"] for k in orgunitGroups]
    config_levels_items = config["levels"].items()
    config_owners_items = config["owners"].items()

    for k, v in config_levels_items:
        if k in orgunitGroupsIds:
            level = v
    for k, v in config_owners_items:
        if k in orgunitGroupsIds:
            owner = v

    has_no_datasets = False
    dataSets = facilityJson["dataSets"]
    if not dataSets:
        has_no_datasets = True
    dataSetsIds = ["%s" % k["id"] for k in dataSets]
    if getattr(config, "hmis_033b_id", "C4oUitImBPK") in dataSetsIds:
        is_033b = True

    if (config["non_functional_facility_group_uid"] in orgunitGroupsIds) and not is_033b:
        is_active = False
    # we return tuple (Subcounty, District, Level, is033B)
    return has_no_datasets, parent, district, level, is_033b, owner, is_active



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
def send_bulksms_task(msg, user, sms_roles=[], district="", facility="", check_districts=True):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    SQL = (
        "SELECT array_agg(uuid) uuids FROM reporters_view WHERE uuid <> ''  "
    )
    if check_districts:
        if district:
            SQL += " AND district_id = ANY($district::INT[]) "

    facilityStr = ''
    if facility and (type(facility) == type('')):
        SQL += " AND facilityid=$facility "
        facilityStr = facility
    if facility and (type(facility) == type([])) and facility != [""]:
        SQL += " AND facilityid = ANY($facility::INT[]) "
        facilityStr = str(facility).replace(
                '[', '{').replace(']', '}').replace("\'", '\"').replace('u', '')

    if sms_roles:
        SQL += " AND role SIMILAR TO $role "
    res = db.query(SQL, {
        'district': str(district).replace(
            '[', '{').replace(']', '}').replace("\'", '\"').replace('u', ''),
        'facility': facilityStr,
        'role': '%%(%s)%%' % '|'.join(sms_roles)})

    if res:
        uuids = res[0]['uuids']
        if uuids:
            recipient_uuids = list(set(uuids))
            sendsms_to_uuids(recipient_uuids, msg)
            update_user_bulksms_limits(db, user, msg, len(recipient_uuids))
    try:
        db._ctx.db.close()
    except:
        pass


@app.task(name="create_bulletin")
def create_bulletin(message, district=None, subcounties=[], roles=[], facilities=[], is_global=False):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])
    res = db.query(
        "INSERT INTO bulletin(message, is_global) "
        " VALUES ($message, $is_global) RETURNING id",
        {
            'message': message,
            'is_global': is_global
        }
    )
    if res:
        bulletin_id = res[0]['id']
        SQL = (
            "UPDATE bulletin SET (district, subcounties, facilities, roles) "
            " = ($district, $subcounties::INTEGER, $facilities::INTEGER, $roles::INTEGER[])"
        )

        facilityStr = '{}'
        if facilities and (type(facilities) == type([])):
            facilityStr = str(facilities).replace(
                    '[', '{').replace(']', '}').replace("\'", '\"').replace('u', '')

        subcountyStr = '{}'
        if subcounties and (type(subcounties) == type([])):
            subcountyStr = str(subcounties).replace(
                    '[', '{').replace(']', '}').replace("\'", '\"').replace('u', '')

        rolesStr = '{}'
        if roles and (type(roles) == type([])):
            rolesStr = str(roles).replace(
                    '[', '{').replace(']', '}').replace("\'", '\"').replace('u', '')
        db.query(SQL, {
            'district': district,
            'subcounties': subcountyStr,
            'facilities': facilityStr,
            'roles': rolesStr
        })

        try:
            db._ctx.db.close()
        except:
            pass


@app.task(name="restart_failed_requests")
def restart_failed_requests(start_date, end_date):
    db = web.database(
        dbn='postgres', user=db_conf['user'], pw=db_conf['passwd'], db=db_conf["name"],
        host=db_conf['host'], port=db_conf['port'])

    SQL = ("UPDATE requests SET status = 'ready' WHERE status='failed' ")
    if start_date:
        SQL += " AND created >= $start_date "
    if end_date:
        SQL += " AND created <= $start_date "
    db.query(SQL, {'start_date': start_date, 'end_date': end_date})
    try:
        db._ctx.db.close()
    except:
        pass

@app.task(name="send_facility_sms_task")
def send_facility_sms_task(facilityid, msg, user, role=""):
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
            recipient_uuids = list(set(uuids))
            sendsms_to_uuids(recipient_uuids, msg)
            update_user_bulksms_limits(db, user, msg, len(recipient_uuids))
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


@app.task(name="task.send_sms_from_excel")
def send_sms_from_excel(excel_file, msg_template=""):

    broadcasts_endpoint = apiv2_endpoint + "broadcasts.json"

    # excel_file is the remote samba file name
    obj = read_remote_samba_file(excel_file)
    if not obj:
        print("Failed to read file: {} from SAMBA server:".format(excel_file))
        return
    file_name = obj.name
    obj.close()

    records = pe.iget_records(file_name=file_name)
    for record in records:
        kws = {
            'name': record['Name'], 'Name': record['Name'],
            'results': record['Results'], 'Results': record['Results'],
            'result': record['Results'], 'Result': record['Results'],
            'labid': record['LabID'], 'LabID': record['LabID'],
            'date': record['Sample Date'], 'Date': record['Sample Date']
        }
        message = Template(msg_template).safe_substitute(kws)
        telephone = format_msisdn(record["Telephone"])
        if not telephone:
            continue
        print("TO:{}, MSG:{}".format(telephone, message))
        params = {
            'urns': ["tel:{}".format(telephone)],
            'text': message
        }
        post_data = json.dumps(params)
        try:
            requests.post(broadcasts_endpoint, post_data, headers={
                'Content-type': 'application/json',
                'Authorization': 'Token %s' % api_token})
            # print("Broadcast Response: ", resp.text)
        except:
            print("ERROR Sending Broadcast")
    deleted = delete_remote_samba_file(excel_file)
    if deleted:
        print("Remote SAMBA file:{} successfully deleted".format(excel_file))
    pe.free_resources()
    os.unlink(file_name)


@app.task(name="task.sync_administrative_units")
def sync_administrative_units_task(
        dhis2_url,
        dhis2_auth,
        pg_conn_params,
        start_level=4,
        end_level=5
):
    """
        Celery task to synchronize organisation units from DHIS2 into a PostgreSQL DB using psycopg2.
        We will start at level 4 because we want to exclude the top level country, region and district.
    """
    conn = psycopg2.connect(**pg_conn_params)
    conn.autocommit = False
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        added_orgunits = 0
        for level in range(start_level, end_level + 1):
            print("Fetching org units at level {0}".format(level))
            resp = requests.get(
                "{0}/api/organisationUnits".format(dhis2_url),
                params={
                    "level": level,
                    "fields": "id,name,code,parent[id]",
                    "paging": "false"
                },
                auth=HTTPBasicAuth(dhis2_auth[0], dhis2_auth[1]),
                timeout=30)
            resp.raise_for_status()
            orgunits = resp.json().get("organisationUnits", [])
            for ou in orgunits:
                orgunit_id = ou["id"]
                parent_id = ou.get("parent", {}).get("id")
                cur.execute("SELECT 1 FROM locations WHERE dhis2id=%s", (orgunit_id,))
                exists = cur.fetchone()
                if not exists:
                    cur.execute("SELECT id FROM locations WHERE dhis2id=%s", (parent_id,))
                    parent_dhis2id = cur.fetchone()
                    if parent_dhis2id:
                        print(u"Adding {0} ({1}) to {2} ({3})".format(
                            ou['name'], orgunit_id, parent_dhis2id["id"], parent_id).encode('utf-8'))
                        cur.execute(
                            """
                            SELECT add_node(%s, %s, %s) AS id
                            """, (1, ou["name"], parent_dhis2id[0])
                        )
                        new_orgunit_id = cur.fetchone()
                        if new_orgunit_id:
                            added_orgunits += 1
                            cur.execute(
                                "UPDATE locations SET dhis2id=%s WHERE id=%s",
                                (ou["id"], new_orgunit_id["id"]))
            conn.commit()
        if added_orgunits > 0:
            print("Updating paths for all org units")
            cur.execute("SELECT refresh_hierarchy();")
            conn.commit()
            print("Added {0} new org units".format(added_orgunits))
        cur.close()
    finally:
        conn.close()


@app.task(name='task.sync_facility')
def sync_facility_task(uids, pg_conn_params,):
    conn = psycopg2.connect(**pg_conn_params)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    print("Synchronising for facility ids: ", uids[:3], "....")

    query_string = "fields=id,name,parent[id,name],dataSets[id],organisationUnitGroups[id]"
    # url = "%s/%s.json?%s" % (config["orgunits_url"], uid.strip(), query_string)
    # print("<><><>", url)
    url_list = []

    for dhis2id in uids:
        url_list.append("%s/%s.json?%s" % (config["orgunits_url"], dhis2id.strip(), query_string))
    orgunits = []
    for url in url_list:
        try:
            response = get_url(url)
            orgunit_dict = json.loads(response)
            orgunits.append(orgunit_dict)
        except Exception as e:
            logging.error("E01: Sync Service failed for ids: {}".format(str(e)))
            continue

    for orgunit in orgunits:
        try:
            hasNoDatasets, subcounty, district, level, is_033b, owner, is_active = get_facility_details(orgunit)
        except Exception as e:
            print(">>>>FAILED: ", " ERROR: ", str(e), " ORGUNIT:", orgunit)
            continue
        if not level:
            continue
        if hasNoDatasets:
            continue

        cur.execute(
            "UPDATE facilities SET name = '' WHERE dhis2id = %s RETURNING "
            "id, name, dhis2id, district, subcounty, level, is_033b", [orgunit["id"]])
        # cur.execute(
        #     "SELECT id, name, dhis2id, district, subcounty, level, is_033b "
        #     "FROM facilities WHERE dhis2id = %s", [orgunit["id"]])
        res = cur.fetchone()
        if not res:  # we don't have an entry already
            logging.debug("Sync Service: adding facility:%s to fsync" % orgunit["id"])
            cur.execute(
                "INSERT INTO facilities(name, dhis2id, district, subcounty, level, is_033b) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (orgunit["name"], orgunit["id"], district, subcounty, level, is_033b))
            # call service to create it in mTrac
            sync_params = {
                'username': config["sync_user"], 'password': config["sync_passwd"],
                'name': orgunit["name"], 'code': orgunit["id"],
                'dhis2id': orgunit["id"], 'ftype': level, 'district': district,
                'subcounty': subcounty, 'is_033b': is_033b, 'is_active': 't' if is_active else 'f'
            }
            try:
                resp = get_url(config["sync_url"], sync_params)
                print("Sync Service: %s" % resp)
            except:
                print("E003: Sync Service failed for:%s" % orgunit["id"])
                logging.error("E003: Sync Service failed for:%s" % orgunit["id"])
        else:  # we have the entry
            logging.debug("Sync Service: updating facility:%s to fsync" % orgunit["id"])
            cur.execute(
                "UPDATE facilities SET name = %s, "
                "district = %s, subcounty = %s, level = %s, is_033b = %s, "
                "ldate = NOW()"
                "WHERE dhis2id = %s",
                (orgunit["name"], district, subcounty, level, is_033b, orgunit["id"]))
            if (res["name"] != orgunit["name"]) or (res["level"] != level) or \
                    (res["is_033b"] != is_033b) or (res["district"] != district) or \
                    (res["subcounty"] != subcounty):
                print("Worth Updating..........", res["dhis2id"])
                sync_params = {
                    'username': config["sync_user"], 'password': config["sync_passwd"],
                    'name': orgunit["name"], 'code': orgunit["id"],
                    'dhis2id': orgunit["id"], 'ftype': level, 'district': district,
                    'subcounty': subcounty, 'is_033b': is_033b
                }
                try:
                    resp = get_url(config["sync_url"], sync_params)
                    logging.debug("Sync Service: ")
                    print("Sync Service: %s" % resp)
                except:
                    print(config["sync_url"])
                    print("E004: Sync Service failed for:%s" % orgunit["id"])
                    logging.error("E04: Sync Service failed for:%s" % orgunit["id"])
            else:
                print("Sync Service: Nothing changed for facility:[UUID: %s]" % orgunit["id"])

        conn.commit()
    conn.close()

