#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"

import requests
import json
import psycopg2
import psycopg2.extras
import phonenumbers
import getopt
import sys
import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
from requests.adapters import HTTPAdapter
import fcntl  # for PID lock


# ============================
#  IMPORT SETTINGS
# ============================
from webapp.settings import (
    config,
    MAX_WORKERS,
    RAPIDPRO_MAX_API,
    RAPIDPRO_MAX_API_LIMIT,
    RAPIDPRO_MIN_API_LIMIT,
    THROTTLE_UP_THRESHOLD,
    THROTTLE_DOWN_THRESHOLD,
    SLOW_MODE_THRESHOLD,
    DEFAULT_REPORTER_GROUPS,
    REPORTER_SYNC_LOG_FILE,
    LOG_LEVEL
)
import logging
from logging.handlers import RotatingFileHandler

# ============================
#  LOGGING SETUP
# ============================

LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

logger = logging.getLogger("rapidpro_sync")
logger.setLevel(LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO))

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
))

# File Handler — rotating
file_handler = RotatingFileHandler(
    REPORTER_SYNC_LOG_FILE,
    maxBytes=10 * 1024 * 1024,   # 10MB
    backupCount=5                # keep 5 old logs
)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info("🔵 RapidPro Sync initialization starting…")


# ============================
#  PID LOCK - Prevent overlap
# ============================
LOCKFILE = "/tmp/rapidpro_sync.lock"
lock = open(LOCKFILE, "w")
try:
    fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    logger.warning("⚠ Another sync is already running. Exiting.")
    sys.exit(0)

# ============================
#  GLOBALS / SEMAPHORES
# ============================

CURRENT_API_LIMIT = RAPIDPRO_MAX_API  # dynamic limit
RAPIDPRO_SEMAPHORE = Semaphore(CURRENT_API_LIMIT)
THROTTLE_LOCK = Lock()

RETRIES = 5
BACKOFF = 1.5
DRY_RUN = False

# HTTP session
session = requests.Session()
session.headers.update({
    "Content-type": "application/json",
    "Authorization": f"Token {config['api_token']}",
})

adapter = HTTPAdapter(pool_connections=MAX_WORKERS * 2, pool_maxsize=MAX_WORKERS * 4)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ============================
# CLI ARGUMENTS
# ============================

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

# ============================
# Throttling Adjuster
# ============================

def adjust_api_limit(latency):
    """Adjust RapidPro concurrency dynamically based on latency."""
    global CURRENT_API_LIMIT, RAPIDPRO_SEMAPHORE

    with THROTTLE_LOCK:

        # SLOW MODE
        if latency > SLOW_MODE_THRESHOLD:
            if CURRENT_API_LIMIT != RAPIDPRO_MIN_API_LIMIT:
                logger.info(f"🐢 Entering SLOW MODE ({latency:.2f}s), limit → {RAPIDPRO_MIN_API_LIMIT}")
                CURRENT_API_LIMIT = RAPIDPRO_MIN_API_LIMIT
                RAPIDPRO_SEMAPHORE = Semaphore(CURRENT_API_LIMIT)
            return

        # Throttle down
        if latency > THROTTLE_DOWN_THRESHOLD:
            if CURRENT_API_LIMIT > RAPIDPRO_MIN_API_LIMIT:
                CURRENT_API_LIMIT -= 1
                logger.info(f"🔽 Reducing API concurrency → {CURRENT_API_LIMIT} (lat={latency:.2f}s)")
                RAPIDPRO_SEMAPHORE = Semaphore(CURRENT_API_LIMIT)
            return

        # Throttle up
        if latency < THROTTLE_UP_THRESHOLD:
            if CURRENT_API_LIMIT < RAPIDPRO_MAX_API_LIMIT:
                CURRENT_API_LIMIT += 1
                logger.info(f"🔼 Increasing API concurrency → {CURRENT_API_LIMIT} (lat={latency:.2f}s)")
                RAPIDPRO_SEMAPHORE = Semaphore(CURRENT_API_LIMIT)
            return

# ============================
# HTTP request with retry + throttling
# ============================

def request_retry(method, url, data=None):
    """Executes RapidPro requests with dynamic throttling."""
    global RAPIDPRO_SEMAPHORE

    with RAPIDPRO_SEMAPHORE:
        if DRY_RUN:
            logger.info(f"[DRY-RUN] {method} {url} data={data}")
            class DummyResp:
                ok = True
                status_code = 200
                text = "{}"
                def json(self): return {}
            return DummyResp()

        last_err = None
        for attempt in range(1, RETRIES + 1):
            try:
                start = time.time()

                if method == "POST":
                    resp = session.post(url, data=data, timeout=20)
                else:
                    resp = session.get(url, timeout=20)

                latency = time.time() - start
                adjust_api_limit(latency)

                if not resp.ok:
                    last_err = Exception(f"{resp.status_code}: {resp.text}")
                    time.sleep(attempt * BACKOFF)
                    continue

                return resp

            except Exception as e:
                last_err = e
                time.sleep(attempt * BACKOFF)

        logger.error(f"❌ HTTP error after {RETRIES} attempts → {url}: {last_err}")
        return None

# ============================
# Utility Functions
# ============================

def format_msisdn(msisdn):
    if not msisdn:
        return None
    try:
        num = phonenumbers.parse(msisdn, config.get("country", "UG"))
        if not phonenumbers.is_valid_number(num):
            return None
        return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except:
        return None

# ============================
# Group Management (cached)
# ============================

_GROUP_CACHE = {}
_GROUP_CACHE_LOCK = Lock()

def get_group_from_cache(name):
    with _GROUP_CACHE_LOCK:
        return _GROUP_CACHE.get(name)

def set_group_cache(name, uuid):
    with _GROUP_CACHE_LOCK:
        _GROUP_CACHE[name] = uuid

def ensure_group_exists(name):
    name = name.strip()
    if not name:
        return None

    cached = get_group_from_cache(name)
    if cached:
        return cached

    resp = request_retry("GET", f"{config['api_url']}groups.json?name={name}")
    if resp:
        try:
            results = resp.json().get("results", [])
            if results:
                uuid = results[0]["uuid"]
                set_group_cache(name, uuid)
                return uuid
        except:
            pass

    payload = json.dumps({"name": name})
    resp = request_retry("POST", f"{config['api_url']}groups.json", payload)
    if resp:
        try:
            uuid = resp.json().get("uuid")
            if uuid:
                logger.info(f"✔ Created group '{name}' → {uuid}")
                set_group_cache(name, uuid)
                return uuid
        except:
            pass

    logger.error(f"❌ Could not create/find group '{name}'")
    return None

def ensure_groups_exist(names):
    return [ensure_group_exists(n) for n in names if n.strip()]

def sync_reporter_groups(role_string):
    if not role_string:
        return []
    names = [g.strip() for g in role_string.split(",") if g.strip()]
    return ensure_groups_exist(names)

def preload_group_cache():
    resp = request_retry("GET", f"{config['api_url']}groups.json")
    if resp:
        try:
            for g in resp.json().get("results", []):
                set_group_cache(g["name"], g["uuid"])
        except:
            pass

# ============================
# RapidPro Contact Upsert
# ============================

def build_endpoint():
    endpoint = config["default_api_uri"]
    if "?" not in endpoint:
        endpoint += "?"
    return endpoint

def upsert_contact_by_uuid_or_create(endpoint, base, existing_uuid, msisdn):
    payload = json.dumps(base)

    # Update using UUID
    if existing_uuid:
        resp = request_retry("POST", f"{endpoint}uuid={existing_uuid}", payload)
        if resp:
            try:
                uuid = resp.json().get("uuid")
                if uuid:
                    return uuid
            except:
                pass

    # Create new
    resp = request_retry("POST", endpoint, payload)
    if resp:
        try:
            uuid = resp.json().get("uuid")
            if uuid:
                return uuid
        except:
            pass

    # URN fallback
    if msisdn:
        resp2 = request_retry("POST", f"{endpoint}urn=tel:{msisdn}", payload)
        if resp2:
            try:
                uuid = resp2.json().get("uuid")
                return uuid
            except:
                pass

    return None

def attach_alt_phone(endpoint, uuid, base, msisdn, alt_phone):
    if not alt_phone:
        return

    data = dict(base)
    urns = []
    if msisdn:
        urns.append(f"tel:{msisdn}")
    urns.append(f"tel:{alt_phone}")
    data["urns"] = urns

    request_retry("POST", f"{endpoint}uuid={uuid}", json.dumps(data))

# ============================
# Worker Thread
# ============================

def process_reporter_http(r):
    reporter_id = r["id"]
    existing_uuid = r["uuid"]
    endpoint = build_endpoint()

    fields = {
        "reporting_location": r["loc_name"],
        "facilitycode": r["facilitycode"],
        "facility": r["facility"],
    }
    if r["district"]:
        fields["district"] = r["district"]

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

    uuid = upsert_contact_by_uuid_or_create(endpoint, base_data, existing_uuid, msisdn)

    if uuid:
        logger.info(f"✔ Reporter {reporter_id} synced → {uuid}")

    if alt_phone:
        attach_alt_phone(endpoint, uuid or existing_uuid, base_data, msisdn, alt_phone)

    return reporter_id, uuid

# ============================
# MAIN EXECUTION
# ============================

def main():
    preload_group_cache()

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
        logger.info("No reporters to sync.")
        conn.close()
        return

    updates = []
    logger.info(f"🚀 Syncing {len(rows)} reporters with {MAX_WORKERS} workers…")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_reporter_http, r): r["id"] for r in rows}
        for future in as_completed(futures):
            rid = futures[future]
            try:
                reporter_id, uuid = future.result()
                if uuid:
                    updates.append((uuid, reporter_id))
            except Exception as e:
                logger.error(f"❌ Error processing {rid}: {e}")

    if updates and not DRY_RUN:
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE reporters SET uuid = %s WHERE id = %s",
            updates,
            page_size=50,
        )
        conn.commit()
        logger.info(f"✔ Updated UUIDs for {len(updates)} reporters")

    conn.close()
    logger.info("🎉 RapidPro sync complete!")

if __name__ == "__main__":
    main()

