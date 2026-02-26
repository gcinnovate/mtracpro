#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"

import requests
import json
import psycopg2
import psycopg2.extras
from webapp.settings import config
import phonenumbers
import getopt
import sys
import datetime
import time

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'fd:u:',
    [])

now = datetime.datetime.now()
sdate = now - datetime.timedelta(days=0, minutes=30)
from_date = sdate.strftime('%Y-%m-%d %H:%M')
update_date = from_date

ADD_FIELDS = False

for option, parameter in opts:
    if option == '-d':
        from_date = parameter
    if option == '-u':
        update_date = parameter
    if option == '-f':
        ADD_FIELDS = True


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_request(url):
    response = requests.get(url, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_available_fields():
    response = requests.get(
        '%sfields.json' % config['api_url'], headers={
            'Content-type': 'application/json',
            'Authorization': 'Token %s' % config['api_token']})
    results = [k['key'] for k in json.loads(response.text)['results']]
    return results


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    assert msisdn is not None
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)  # .replace('+', '')


def add_reporter_fields():
    our_fields = [
        {'label': 'facility', 'value_type': 'text'},
        {'label': 'facilitycode', 'value_type': 'text'},
        {'label': 'district', 'value_type': 'text'},
        {'label': 'Subcounty', 'value_type': 'text'},
        {'label': 'village', 'value_type': 'text'},
        {'label': 'Type', 'value_type': 'text'},
        {'label': 'reporting location', 'value_type': 'text'},
    ]
    fields = get_available_fields()
    for f in our_fields:
        if f['label'] not in fields:
            res = post_request(
                json.dumps(f), '%sfields.json' % config['api_url'])
            print(res.text)

if ADD_FIELDS:
    add_reporter_fields()
    sys.exit(1)
conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute(
    "SELECT id, initcap(trim(lastname)) || ' ' || initcap(trim(firstname)) as name, telephone, alternate_tel, "
    "email, get_location_name(district_id) AS district, role, "
    "facility, facilitycode, loc_name, created, uuid, uuid2, "
    "get_location_name(get_subcounty_id(reporting_location)) AS subcounty FROM reporters_view1 "
    "WHERE updated >= %s", [update_date]
)

res = cur.fetchall()
# sys.exit(1)
if res:
    for r in res:
        # print(f"processing: {r['telephone']}")
        district = r["district"]
        existing_uuid = r["uuid"]
        endpoint = config["default_api_uri"]
        if '?' not in endpoint:
            endpoint += "?"
        fields = {
            "reporting_location": r['loc_name'],
            "facilitycode": r['facilitycode'],
            "facility": r['facility'],
            # "Type": "VHT" if 'VHT' in r['role'] else "HC",
            # "Subcounty": r['subcounty']
        }
        if district:
            fields["district"] = district
        phone = format_msisdn(r['telephone']) if r['telephone'] else ''
        alt_phone = format_msisdn(r['alternate_tel']) if r['alternate_tel'] else ''
        role_filter = lambda x: x != ''
        try:
            if phone:
                data = {
                    "name": r['name'],
                    "urns": ["tel:" + phone],
                    "email": r['email'],
                    "groups": list(filter(role_filter,r['role'].split(','))),
                    "fields": fields
                }
                data2 = {
                    "name": r['name'],
                    "email": r['email'],
                    "groups": list(filter(role_filter,r['role'].split(','))),
                    "fields": fields
                }
                # print("======>", list(filter(role_filter,r['role'].split(','))))
                # Let's try getting the contact
                get_url = "{0}urn={1}".format(endpoint, "tel:" + phone)
                # print(get_url)
                resp = get_request(get_url)
                json_resp = resp.json()
                if json_resp['results']:
                    url = "{0}uuid={1}".format(endpoint, json_resp['results'][0]['uuid'])
                    print("Reporter exits: [URL:{0}]".format(url))
                    post_data = json.dumps(data2)
                    resp = post_request(post_data, url=url)
                    # print(json_resp['results'])
                else:
                    print("Reporter missing in RapidPro")
                    post_data = json.dumps(data)
                    resp = post_request(post_data)

                print("Response:=>", resp.json())
                response_dict = resp.json()
                if 'uuid' in response_dict:
                    contact_uuid = response_dict["uuid"]
                    cur.execute("UPDATE reporters SET uuid = %s WHERE id=%s", [contact_uuid, r["id"]])
                    conn.commit()
                    print("Added/Updated: ", r['name'], phone)
                else:
                    pass
            else:
                print("Invalid Phone: {0}".format(r['telephone']))

                # print resp.text

            if alt_phone:
                existing_uuid = r["uuid2"]
                endpoint = config["default_api_uri"]
                if '?' not in endpoint:
                    endpoint += "?"
                alt_phone = format_msisdn(alt_phone)
                # post_data = json.dumps(data)
                data = {
                    "name": r['name'],
                    "urns": ["tel:{0}".format(phone)],
                    "email": r['email'],
                    "groups": list(filter(role_filter,r['role'].split(','))),
                    "fields": fields
                }
                data2 = {
                    "name": r['name'],
                    "email": r['email'],
                    "groups": list(filter(role_filter,r['role'].split(','))),
                    "fields": fields
                }
                # Let's try getting the contact
                get_url = "{0}urn={1}".format(endpoint, "tel:{0}".format(alt_phone))
                print(get_url)
                resp = get_request(get_url)
                json_resp = resp.json()
                if json_resp['results']:
                    url = "{0}uuid={1}".format(endpoint, json_resp['results'][0]['uuid'])
                    print("Reporter exits: [URL:{0}]".format(url))
                    post_data = json.dumps(data2)
                    resp = post_request(post_data, url=url)
                    # print(json_resp['results'])
                else:
                    print("Reporter missing in RapidPro")
                    post_data = json.dumps(data)
                    resp = post_request(post_data)

                print("=>", resp.json())
                response_dict = resp.json()
                if 'uuid' in response_dict:
                    contact_uuid = response_dict["uuid"]
                    cur.execute("UPDATE reporters SET uuid2 = %s WHERE id=%s", [contact_uuid, r["id"]])
                    conn.commit()
                    print("Added/Updated:", response_dict)
                else:
                    pass

                print(resp.text)
        except Exception as e:
            print("XXXXX", e)
            continue
        time.sleep(0.3)
conn.close()
