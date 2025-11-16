#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"

import requests
import json
import psycopg2
import psycopg2.extras
from settings import config, DEFAULT_REPORTER_GROUPS
import phonenumbers
import getopt
import sys
import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from requests.adapters import HTTPAdapter

# ================================================================
# CONFIG
# ================================================================

MAX_WORKERS = 20
RETRIES = 5
BACKOFF = 1.5
DRY_RUN = False


session = requests.Session()
session.headers.update({
    "Content-type": "application/json",
    "Authorization": f"Token {config['api_token']}",
})

adapter = HTTPAdapter(pool_connections=MAX_WORKERS * 2, pool_maxsize=MAX_WORKERS * 4)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ================================================================
# CLI ARGUMENTS
# ================================================================

cmd = sys.argv[1:]
opts, args = getopt.getopt(cmd, "fd:u:n", ["init-groups"])

now = datetime.datetime.now()
sdate = now - datetime.timedelta(days=1, minutes=5)
from_date = sdate.strftime("%Y-%m-%d %H:%M")
update_date = from_date
ADD_FIELDS = False
INIT_GROUPS = False

for option, parameter in opts:
    if option == "-d":
        from_date = parameter
    if option == "-u":
        update_date = parameter
    if option == "-f":
        ADD_FIELDS = True
    if option == "-n":
        DRY_RUN = True
    if option == "--init-groups":
        INIT_GROUPS = True

# ================================================================
# HTTP REQUEST WITH RETRY
# ================================================================

def request_retry(method, url, data=None):
    if DRY_RUN:
        print(f"[DRY-RUN] {method} {url} data={data}")
        class DummyResp(object):
            ok = True
            status_code = 200
            text = "{}"
            def json(self): return {}
        return DummyResp()

    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            if method == "POST":
                resp = session.post(url, data=data, timeout=20)
            else:
                resp = session.get(url, timeout=20)

            if not resp.ok:
                last_err = Exception(f"{resp.status_code}: {resp.text}")
                time.sleep(attempt * BACKOFF)
                continue

            return resp

        except Exception as e:
            last_err = e
            time.sleep(attempt * BACKOFF)

    print(f"❌ HTTP failed after {RETRIES} attempts → {url}: {last_err}")
    return None

# ================================================================
# PHONE FORMATTER
# ================================================================

def format_msisdn(msisdn):
    if not msisdn:
        return None
    try:
        num = phonenumbers.parse(msisdn, getattr(config, "country", "UG"))
        if not phonenumbers.is_valid_number(num):
            return None
        return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except:
        return None

# ================================================================
# GROUP CACHE
# ================================================================

_GROUP_CACHE = {}
_GROUP_CACHE_LOCK = Lock()

def get_group_from_cache(name):
    with _GROUP_CACHE_LOCK:
        return _GROUP_CACHE.get(name)

def set_group_cache(name, uuid):
    if not uuid:
        return
    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE[name] = uuid

# ================================================================
# RAPIDPRO GROUP MANAGEMENT
# ================================================================

def ensure_group_exists(group_name):
    group_name = group_name.strip()
    if not group_name:
        return None

    # Check cache
    cached = get_group_from_cache(group_name)
    if cached:
        return cached

    # 1. Check API
    resp = request_retry("GET", f"{config['api_url']}groups.json?name={group_name}")
    if resp:
        try:
            rd = resp.json()
            if rd.get("results"):
                uuid = rd["results"][0]["uuid"]
                set_group_cache(group_name, uuid)
                return uuid
        except:
            pass

    # 2. Create group
    payload = json.dumps({"name": group_name})
    resp = request_retry("POST", f"{config['api_url']}groups.json", payload)
    if resp:
        try:
            rd = resp.json()
            if "uuid" in rd:
                uuid = rd["uuid"]
                print(f"✔ Created group '{group_name}' → {uuid}")
                set_group_cache(group_name, uuid)
                return uuid
        except:
            pass

    print(f"❌ Failed group '{group_name}'")
    return None

def ensure_groups_exist(group_list):
    uuids = []
    for g in group_list:
        uuid = ensure_group_exists(g)
        if uuid:
            uuids.append(uuid)
    return uuids

def sync_reporter_groups(role_string):
    if not role_string:
        return []
    groups = [g.strip() for g in role_string.split(",") if g.strip()]
    return ensure_groups_exist(groups)

def preload_group_cache():
    print("🔄 Preloading RapidPro groups...")
    resp = request_retry("GET", f"{config['api_url']}groups.json")
    if resp:
        try:
            for g in resp.json().get("results", []):
                set_group_cache(g["name"], g["uuid"])
            print(f"✔ Preloaded {len(_GROUP_CACHE)} existing groups")
        except:
            pass

def initialize_default_groups():
    print("🔧 Initializing default groups...")
    ensure_groups_exist(DEFAULT_REPORTER_GROUPS)
    print("✔ Done initializing!")

# ================================================================
# ADD REPORTER FIELDS (optional old code)
# ================================================================

def add_reporter_fields():
    our_fields = [
        {"label": "facility", "value_type": "text"},
        {"label": "facilitycode", "value_type": "text"},
        {"label": "district", "value_type": "text"},
        {"label": "Subcounty", "value_type": "text"},
        {"label": "village", "value_type": "text"},
        {"label": "Type", "value_type": "text"},
        {"label": "reporting location", "value_type": "text"},
    ]

    resp = request_retry("GET", f"{config['api_url']}fields.json")
    if not resp:
        return

    try:
        existing = [k["key"] for k in resp.json().get("results", [])]
    except:
        existing = []

    for f in our_fields:
        if f["label"] not in existing:
            resp2 = request_retry("POST", f"{config['api_url']}fields.json", json.dumps(f))
            print(resp2.text if resp2 else "ERROR")

if ADD_FIELDS:
    add_reporter_fields()
    sys.exit(0)

if INIT_GROUPS:
    initialize_default_groups()
    sys.exit(0)

# ================================================================
# CONTACT UPSERT LOGIC
# ================================================================

def build_endpoint():
    endpoint = config["default_api_uri"]
    if "?" not in endpoint:
        endpoint += "?"
    return endpoint

def upsert_contact_by_uuid_or_create(endpoint, base_data, existing_uuid, msisdn):
    data_json = json.dumps(base_data)

    # 1. Try update by UUID
    if existing_uuid:
        url = f"{endpoint}uuid={existing_uuid}"
        resp = request_retry("POST", url, data_json)
        if resp:
            try:
                rd = resp.json()
                if "uuid" in rd:
                    return rd["uuid"], resp.text
                # UUID not found → fall through
            except:
                pass

    # 2. Create new contact
    resp = request_retry("POST", endpoint, data_json)
    if resp:
        try:
            rd = resp.json()
            if "uuid" in rd:
                return rd["uuid"], resp.text
        except:
            pass

    # 3. URN fallback
    try:
        rd = resp.json()
    except:
        rd = {}

    if msisdn and isinstance(rd, dict) and "urns" in rd and rd["urns"]:
        first = rd["urns"][0]
        if isinstance(first, dict) and "belongs" in first:
            fallback_url = f"{endpoint}urn=tel:{msisdn}"
            data2 = dict(base_data)
            data2.pop("urns", None)
            resp2 = request_retry("POST", fallback_url, json.dumps(data2))
            if resp2:
                try:
                    rd2 = resp2.json()
                    if "uuid" in rd2:
                        return rd2["uuid"], resp2.text
                except:
                    pass

    return None, None

def attach_alt_phone(endpoint, contact_uuid, base_data, msisdn, alt_msisdn):
    if not alt_msisdn:
        return
    data = dict(base_data)
    urns = []
    if msisdn:
        urns.append(f"tel:{msisdn}")
    urns.append(f"tel:{alt_msisdn}")
    data["urns"] = urns
    data_json = json.dumps(data)

    if contact_uuid:
        url = f"{endpoint}uuid={contact_uuid}"
    else:
        url = endpoint

    request_retry("POST", url, data_json)

# ================================================================
# WORKER THREAD
# ================================================================

def process_reporter_http(r):
    reporter_id = r["id"]
    district = r["district"]
    existing_uuid = r["uuid"]

    endpoint = build_endpoint()

    fields = {
        "reporting_location": r["loc_name"],
        "facilitycode": r["facilitycode"],
        "facility": r["facility"],
    }
    if district:
        fields["district"] = district

    msisdn = format_msisdn(r["telephone"])
    alt_phone = format_msisdn(r["alternate_tel"])

    base_data = {
        "name": r["name"],
        "email": r["email"],
        "groups": sync_reporter_groups(r["role"]),
        "fields": fields,
    }

    if msisdn:
        base_data["urns"] = [f"tel:{msisdn}"]

    contact_uuid, raw = upsert_contact_by_uuid_or_create(endpoint, base_data, existing_uuid, msisdn)

    if contact_uuid:
        print(f"✔ Reporter {reporter_id}: synced → {contact_uuid}")

    if alt_phone:
        attach_alt_phone(endpoint, contact_uuid or existing_uuid, base_data, msisdn, alt_phone)

    return reporter_id, contact_uuid

# ================================================================
# MAIN EXECUTION
# ================================================================

def main():
    preload_group_cache()  # ← improves speed dramatically

    conn = psycopg2.connect(
        f"dbname={config['db_name']} host={config['db_host']} port={config['db_port']} "
        f"user={config['db_user']} password={config['db_passwd']}"
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        """
        SELECT id,
               lastname || ' ' || firstname AS name,
               telephone,
               alternate_tel,
               email,
               get_location_name(district_id) AS district,
               role,
               facility,
               facilitycode,
               loc_name,
               created,
               uuid,
               get_location_name(get_subcounty_id(reporting_location)) AS subcounty
        FROM reporters_view1
        WHERE created >= %s OR updated >= %s
        """,
        [from_date, update_date],
    )
    rows = cur.fetchall()

    if not rows:
        print("No reporters to sync.")
        conn.close()
        return

    print(f"🚀 Starting RapidPro sync for {len(rows)} reporters with {MAX_WORKERS} workers…")
    updates = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_reporter_http, r): r["id"] for r in rows}
        for future in as_completed(futures):
            rid = futures[future]
            try:
                reporter_id, contact_uuid = future.result()
                if contact_uuid:
                    updates.append((contact_uuid, reporter_id))
            except Exception as e:
                print(f"❌ Worker error on {rid}: {e}")

    if not DRY_RUN and updates:
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE reporters SET uuid = %s WHERE id = %s",
            updates,
            page_size=100,
        )
        conn.commit()
        print(f"✔ Updated DB UUIDs for {len(updates)} reporters")

    conn.close()
    print("🎉 Completed RapidPro sync!")

if __name__ == "__main__":
    main()

