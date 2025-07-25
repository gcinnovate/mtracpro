#!/usr/bin/env python
import sys
import psycopg2
import psycopg2.extras
import requests
import json
import re
import getopt
import logging
from settings import config

logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/sync_facilities.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)
cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'c:u:l:af',
    ['created-since', 'updated-since', 'id-list', 'all-facilities', 'force-sync'])

SYNC_ALL = False
FORCE_SYNC = False
facility_id_list = ""
# This the additional query string to DHIS2 orgunit URL
query_string = (
    "fields=id,name,parent[id,name,href],dataSets[id],organisationUnitGroups[id]")

for option, parameter in opts:
    if option == '-a':
        query_string += "&paging=false"
        SYNC_ALL = True
    if option == '-c':
        query_string += "&filter=created:ge:%s" % (parameter)
    if option == '-u':
        query_string += "&filter=lastUpdated:ge:%s" % (parameter)
    if option == '-l':
        facility_id_list = parameter
    if option == '-f':
        FORCE_SYNC = True

URL = "%s.json?%s" % (config["orgunits_url"], query_string)
print(URL)
url_list = []
if facility_id_list:
    for dhis2id in facility_id_list.split(','):
        url_list.append("%s/%s.json?%s" % (config["orgunits_url"], dhis2id.strip(), query_string))

user = config["dhis2_user"]
passwd = config["dhis2_passwd"]

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])

cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


def get_url(url, payload={}):
    res = requests.get(url, params=payload, auth=(user, passwd))
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
    try:
        # Python 2
        config_levels_items = config["levels"].iteritems()
        config_owners_items = config["owners"].iteritems()
    except AttributeError:
        # Python 3
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

if SYNC_ALL:
    SYNC_URL = ("%s.json?level=6&fields=id,name&paging=false")
    url_to_call = SYNC_URL % (config["orgunits_url"])
    print(url_to_call)

    payload = {}

    try:
        response = get_url(url_to_call)
        orgunits_dict = json.loads(response)
        orgunits = orgunits_dict['organisationUnits']
    except Exception as e:
        print(str(e))
        orgunits = []

    facility_ids = []
    for orgunit in orgunits:
        #  print "processing for Facility:%s" % orgunit["id"]
        cur.execute("SELECT id FROM facilities WHERE dhis2id = %s", (orgunit["id"],))
        res = cur.fetchone()
        if not res:  # we don't have an entry already
            cur.execute(
                "INSERT INTO facilities(name, dhis2id) VALUES (%s, %s)",
                (orgunit["name"], orgunit["id"]))
            print("NEW ==>", orgunit["id"])
            url_list.append("%s/%s.json?%s" % (config["orgunits_url"], orgunit["id"].strip(), query_string))
            facility_ids.append(orgunit["id"])
        else:  # we have the entry
            print("OLD ==>", orgunit["id"])
            cur.execute(
                "UPDATE facilities SET name = %s WHERE dhis2id = %s",
                (orgunit["name"], orgunit["id"]))
        conn.commit()
    facility_id_list = ','.join(facility_ids)

if FORCE_SYNC:  # this is only used when you want to sync the contents alread id sync db
    logging.debug("START FULL SYNC for DB")
    cur.execute(
        "SELECT id, name, dhis2id, district, subcounty, level, is_033b "
        "FROM facilities WHERE level <> ''")
    res = cur.fetchall()
    for r in res:
        sync_params = {
            'username': config["sync_user"], 'password': config["sync_passwd"],
            'name': r["name"], 'code': r['dhis2id'],
            'dhis2id': r["dhis2id"], 'ftype': r["level"], 'district': r["district"],
            'subcounty': r["subcounty"], 'is_033b': r["is_033b"]
        }
        try:
            resp = get_url(config["sync_url"], sync_params)
            logging.debug("Syncing facility: %s" % r["dhis2id"])
        except:
            logging.error("E00: Sync Service failed for facility: %s" % r["dhis2id"])
    logging.debug("END FULL SYNC for DB")
    sys.exit()

if facility_id_list and url_list:  # this is for a list of ids
    orgunits = []
    for url in url_list:
        try:
            response = get_url(url)
            orgunit_dict = json.loads(response)
            orgunits.append(orgunit_dict)
        except:
            logging.error("E01: Sync Service failed for multiple ids:")
            pass  # just keep quiet
else:
    try:
        response = get_url(URL)
        orgunits_dict = json.loads(response)
        orgunits = orgunits_dict['organisationUnits']
    except:
        orgunits = []
        logging.error("E02: Sync Service failed")
        # just keep quiet for now

print(URL)
print(orgunits)
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
        "SELECT id, name, dhis2id, district, subcounty, level, is_033b "
        "FROM facilities WHERE dhis2id = %s", [orgunit["id"]])
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
            print("E03: Sync Service failed for:%s" % orgunit["id"])
            logging.error("E03: Sync Service failed for:%s" % orgunit["id"])
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
                    print("E04: Sync Service failed for:%s" % orgunit["id"])
                    logging.error("E04: Sync Service failed for:%s" % orgunit["id"])
        else:
            print("Sync Service: Nothing changed for facility:[UUID: %s]" % orgunit["id"])

    conn.commit()

conn.close()
