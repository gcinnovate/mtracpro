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
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/fullsync.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)
cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'l:af',
    ['id-list', 'all-districts', 'force-sync'])
query_string = (
    "includeDescendants=true&"
    "fields=id,name,parent[id,name,href],dataSets[id],organisationUnitGroups[id]"
    "&filter=level:eq:6&paging=false")

district_id_list = ""
for option, parameter in opts:
    if option == '-l':
        district_id_list = parameter

dhis2_ids = []
if district_id_list:
    for dhis2id in district_id_list.split(','):
        dhis2_ids.append(dhis2id)


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
    is_033b = False
    level = ""
    owner = ""
    is_active = True
    parent = re.sub(
        'Subcounty$|Sub\ County.*$', "", facilityJson["parent"]["name"],
        flags=re.IGNORECASE).strip()
    parent_id = facilityJson["parent"]["id"]
    # parent = facilityJson["parent"]["name"]
    district_url = "%s/%s.json?fields=id,name,parent[id,name,parent[id,name]]" % (config["orgunits_url"], facilityJson["parent"]["id"])
    print(district_url)
    districtJson = get_url(district_url)
    # print districtJson
    # district = json.loads(districtJson)["parent"]["name"].replace('District', '').strip()
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
    return has_no_datasets, parent, parent_id, district, level, is_033b, owner, is_active

if not dhis2_ids:
    cur.execute(
        "SELECT dhis2id FROM locations WHERE type_id = (SELECT id FROM locationtype "
        "WHERE name = 'district')")
    res = cur.fetchall()
    for district in res:
        dhis2_ids.append(district['dhis2id'])

print(dhis2_ids)
for dhis2id in dhis2_ids:
    if not dhis2id:
        continue
    URL = "%s/%s.json?%s" % (config["orgunits_url"], dhis2id, query_string)
    print(URL)
    orgunits = []
    try:
        response = get_url(URL)
        orgunits_dict = json.loads(response)
        orgunits = orgunits_dict['organisationUnits']
    except:
        logging.error("E02: Sync Service failed")
        # just keep quiet for now

    for orgunit in orgunits:
        hasNoDatasets, subcounty, subcounty_uid, district, level, is_033b, owner, is_active = get_facility_details(orgunit)
        if not level:
            continue
        if hasNoDatasets:
            continue
        sync_params = {
            'username': config["sync_user"], 'password': config["sync_passwd"],
            'name': orgunit["name"],
            'dhis2id': orgunit["id"], 'ftype': level, 'district': district,
            'subcounty': subcounty, 'subcounty_uid': subcounty_uid, 'is_033b': is_033b, 'owner': owner,
            'code': orgunit["id"], 'is_active': 't' if is_active else 'f'
        }
        # print("Params:",  sync_params)
        try:
            resp = get_url(config["sync_url"], sync_params)
            # print(sync_params)
            print("Sync Service: %s" % resp)
        except:
            print("Sync Service failed for:%s" % orgunit["id"])
            logging.error("E03: Sync Service failed for:%s" % orgunit["id"])
