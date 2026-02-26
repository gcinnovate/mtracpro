-- mTrac Tables, Samuel Sekiwere, 2017-02-25
-- remeber to add indexes
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION "uuid-ossp";
CREATE EXTENSION plpython3u;
CREATE EXTENSION hstore;

-- webpy sessions
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

CREATE TABLE user_roles (
    id SERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    descr text DEFAULT '',
    cdate TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX user_roles_idx1 ON user_roles(name);

CREATE TABLE permissions(
    id SERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    codename TEXT NOT NULL,
    sys_module TEXT NOT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (codename, sys_module)
);

CREATE TABLE user_role_permissions (
    id SERIAL NOT NULL PRIMARY KEY,
    user_role INTEGER NOT NULL REFERENCES user_roles ON DELETE CASCADE ON UPDATE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE
);

CREATE TABLE users (
    id bigserial NOT NULL PRIMARY KEY,
    user_role  INTEGER NOT NULL REFERENCES user_roles ON DELETE RESTRICT ON UPDATE CASCADE, --(call agents, admin, service providers)
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL UNIQUE,
    telephone TEXT NOT NULL DEFAULT '', -- acts as the username
    password TEXT NOT NULL, -- blowfish hash of password
    email TEXT NOT NULL DEFAULT '',
    districts INTEGER [] DEFAULT '{}'::INT[],
    allowed_ips TEXT NOT NULL DEFAULT '127.0.0.1;::1', -- semi-colon separated list of allowed ip masks
    denied_ips TEXT NOT NULL DEFAULT '', -- semi-colon separated list of denied ip masks
    failed_attempts TEXT DEFAULT '0/'||to_char(now(),'yyyymmdd'),
    transaction_limit TEXT DEFAULT '0/'||to_char(now(),'yyyymmdd'),
    is_active BOOLEAN NOT NULL DEFAULT 't',
    is_system_user BOOLEAN NOT NULL DEFAULT 'f',
    last_login TIMESTAMPTZ,
    last_passwd_update TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_permissions(
    id SERIAL NOT NULL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE
);

CREATE INDEX users_idx1 ON users(telephone);
CREATE INDEX users_idx2 ON users(username);

CREATE TABLE audit_log (
        id BIGSERIAL NOT NULL PRIMARY KEY,
        logtype VARCHAR(32) NOT NULL DEFAULT '',
        actor TEXT NOT NULL,
        action text NOT NULL DEFAULT '',
        remote_ip INET,
        detail TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id), -- like actor id
        created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX au_idx1 ON audit_log(created);
CREATE INDEX au_idx2 ON audit_log(logtype);
CREATE INDEX au_idx4 ON audit_log(action);

CREATE TABLE configs (
        id serial NOT NULL PRIMARY KEY,
        item TEXT NOT NULL UNIQUE,
        val TEXT NOT NULL,
        detail TEXT DEFAULT '',
        created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE anonymousreports(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    facilityid INTEGER REFERENCES healthfacilities(id),
    districtid INTEGER REFERENCES locations,
    report TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL DEFAULT 'Open' CHECK(action IN('Open', 'Ignored', 'Escalated', 'Closed', 'Canceled')),
    action_center TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    action_taken TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    contact_uuid TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE anonymousreport_messages(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    report_id BIGINT REFERENCES anonymousreports(id),
    message TEXT NOT NULL DEFAULT '',
    direction VARCHAR(1) NOT NULL DEFAULT 'I',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION gen_code() RETURNS TEXT AS
$delim$
import string
import random
from uuid import uuid4


def id_generator(size=10, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return random.choice(string.ascii_uppercase) + ''.join(random.choice(chars) for _ in range(size))

return id_generator()
$delim$ LANGUAGE plpython3u;

CREATE TABLE locationtree(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP

);


CREATE TABLE locationtype(
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES locationtree(id),
    name TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL,
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE locations(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES locationtree(id),
    type_id INTEGER NOT NULL REFERENCES locationtype(id), --Cascade
    code TEXT NOT NULL DEFAULT gen_code(),
    name TEXT NOT NULL DEFAULT '',
    tree_parent_id INTEGER REFERENCES locations(id),
    lft INTEGER NOT NULL,
    rght INTEGER NOT NULL,
    dhis2id TEXT NOT NULL DEFAULT '',
    level INTEGER,
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX locations_idx4 ON locations(lft);
CREATE INDEX locations_idx5 ON locations(rght);
CREATE INDEX locations_idx6 ON locations(code);

CREATE VIEW locations_view AS
    SELECT a.*, b.level FROM locations a, locationtype b
    WHERE a.type_id = b.id;

CREATE TABLE rejected_reports(
    id bigserial PRIMARY KEY NOT NULL,
    source INTEGER REFERENCES servers(id),
    destination INTEGER REFERENCES servers(id),
    body TEXT NOT NULL DEFAULT '',
    response TEXT NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'error' CHECK(status IN('pending', 'ready', 'inprogress', 'failed', 'error', 'expired', 'completed', 'canceled')),
    statuscode text DEFAULT '',
    errors TEXT DEFAULT '', -- indicative response message
    submissionid INTEGER NOT NULL DEFAULT 0,
    week TEXT DEFAULT '', -- reporting week
    month TEXT DEFAULT '', -- reporting month
    year INTEGER, -- year of submission
    msisdn TEXT NOT NULL DEFAULT '',
    raw_msg TEXT NOT NULL DEFAULT '',
    facility TEXT NOT NULL DEFAULT '',
    district TEXT NOT NULL DEFAULT '',
    report_type TEXT NOT NULL DEFAULT '',
    extras TEXT NOT NULL DEFAULT '',
    is_edited BOOLEAN NOT NULL DEFAULT 'f',
    edited_raw_msg TEXT NOT NULL DEFAULT '',
    created timestamptz DEFAULT current_timestamp,
    updated timestamptz DEFAULT current_timestamp
);

CREATE INDEX rejected_reports_idx1 ON rejected_reports(submissionid);
CREATE INDEX rejected_reports_idx2 ON rejected_reports(status);
CREATE INDEX rejected_reports_idx3 ON rejected_reports(statuscode);
CREATE INDEX rejected_reports_idx4 ON rejected_reports(week);
CREATE INDEX rejected_reports_idx5 ON rejected_reports(month);
CREATE INDEX rejected_reports_idx6 ON rejected_reports(year);
CREATE INDEX rejected_reports_idx7 ON rejected_reports(ctype);
CREATE INDEX rejected_reports_idx8 ON rejected_reports(msisdn);
CREATE INDEX rejected_reports_idx9 ON rejected_reports(facility);
CREATE INDEX rejected_reports_idx10 ON rejected_reports(district);


CREATE TABLE bulletin(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    message TEXT,
    district INTEGER,
    subcounties INTEGER [] DEFAULT '{}'::INT[],
    facilities INTEGER [] DEFAULT '{}'::INT[],
    roles INTEGER [] DEFAULT '{}'::INT[],
    is_global BOOLEAN DEFAULT FALSE,
    created timestamptz DEFAULT current_timestamp,
    updated timestamptz DEFAULT current_timestamp
);

--FUNCTIONS
CREATE OR REPLACE FUNCTION public.get_children(loc_id integer)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
    BEGIN
        FOR r IN SELECT * FROM locations_view WHERE tree_parent_id = loc_id
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION public.get_descendants(loc_id bigint)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft > our_lft AND rght < our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_descendants_including_self(loc_id bigint)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft >= our_lft AND rght <= our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_ancestors(loc_id integer)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft <= our_lft AND rght >= our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.add_node(treeid integer, node_name text, p_id integer)
 RETURNS BIGINT
 LANGUAGE plpgsql
AS $function$
    DECLARE
    new_lft INTEGER;
    lvl INTEGER;
    dummy TEXT;
    node_type INTEGER;
    child_type INTEGER;
    new_id BIGINT;
    BEGIN
        IF node_name = '' THEN
            RAISE NOTICE 'Node name cannot be empty string';
            RETURN FALSE;
        END IF;
        SELECT level INTO lvl FROM locationtype WHERE id = (SELECT type_id FROM locations WHERE id = p_id);
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Cannot add node: failed to find level';
        END IF;
        SELECT rght, type_id INTO new_lft, node_type FROM locations WHERE id =  p_id AND tree_id = treeid;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No such node id= % ', p_id;
        END IF;

        SELECT id INTO child_type FROM locationtype WHERE level = lvl + 1 AND tree_id = tree_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'You cannot add to root node';
        END IF;

        SELECT name INTO dummy FROM locations WHERE name = node_name
            AND tree_id = treeid AND type_id = child_type AND tree_parent_id = p_id;
        IF FOUND THEN
            RAISE NOTICE 'Node already exists : %', node_name;
            RETURN FALSE;
        END IF;

        UPDATE locations SET lft = lft + 2 WHERE lft > new_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght + 2 WHERE rght >= new_lft AND tree_id = treeid;
        INSERT INTO locations (name, code, lft, rght, tree_id,type_id, tree_parent_id)
        VALUES (node_name, generate_uid(), new_lft, new_lft+1, treeid, child_type, p_id)
        RETURNING id INTO new_id;
        RETURN new_id;
    END;
$function$;


CREATE OR REPLACE FUNCTION add_node(node_name text, p_id integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
    DECLARE
        new_lft INTEGER;
        lvl INTEGER;
        dummy TEXT;
        node_type INTEGER;
        child_type INTEGER;
        new_id BIGINT;
    BEGIN
        IF node_name = '' THEN
            RAISE NOTICE 'Node name cannot be empty string';
            RETURN NULL;
        END IF;

        SELECT level INTO lvl FROM locationtype WHERE id = (SELECT type_id FROM locations WHERE id = p_id);
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Cannot add node: failed to find level';
        END IF;

        SELECT rght INTO new_lft FROM locations WHERE id =  p_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No such node id= % ', p_id;
        END IF;

        SELECT id INTO child_type FROM locationtype WHERE level = lvl + 1;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'You cannot add to root node';
        END IF;

        SELECT name INTO dummy FROM locations WHERE name = node_name
            AND type_id = child_type AND parent_id = p_id;
        IF FOUND THEN
            RAISE NOTICE 'Node already exists : %', node_name;
            RETURN NULL;
        END IF;

        UPDATE locations SET lft = lft + 2 WHERE lft > new_lft;
        UPDATE locations SET rght = rght + 2 WHERE rght >= new_lft;

        INSERT INTO locations (name, code, lft, rght, type_id, level, parent_id)
        VALUES (node_name, generate_uid(), new_lft, new_lft+1, child_type, lvl + 1, p_id)
        RETURNING id INTO new_id;

        RETURN new_id;
    END;
$function$;

CREATE OR REPLACE FUNCTION delete_node(treeid INT, node_id BIGINT)
    RETURNS boolean AS $delim$
    DECLARE
        node_lft INTEGER;
    BEGIN
        SELECT lft INTO node_lft FROM locations
            WHERE id = node_id AND tree_id = treeid;
        IF NOT FOUND THEN RETURN FALSE; END IF;
        UPDATE locations SET lft = lft - 2 WHERE lft > node_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght - 2 WHERE rght > node_lft AND tree_id = treeid;
        DELETE FROM locations WHERE id = node_id;
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;

CREATE TABLE orgunit_groups(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    dhis2id TEXT NOT NULL DEFAULT '',
    cdate TIMESTAMP DEFAULT NOW()
);

-- this is used for synchronizing with DHIS2
CREATE TABLE facilities(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    dhis2id TEXT NOT NULL DEFAULT '',
    district TEXT NOT NULL DEFAULT '',
    is_033b BOOLEAN DEFAULT 'f',
    level TEXT NOT NULL DEFAULT '',
    subcounty TEXT NOT NULL DEFAULT '',
    cdate TIMESTAMP DEFAULT NOW(),
    ldate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE healthfacility_type(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT UNIQUE NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE healthfacilities(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    type_id INTEGER NOT NULL REFERENCES healthfacility_type(id),
    name TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '', --dhis2id
    district_id BIGINT REFERENCES locations,
    district TEXT NOT NULL DEFAULT '',
    location BIGINT REFERENCES locations(id), --subcounty
    location_name TEXT NOT NULL DEFAULT '', -- these are done for performance reasons
    is_033b BOOLEAN DEFAULT 't',
    is_active BOOLEAN DEFAULT 't',
    last_reporting_date DATE,
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX healthfacilities_idx ON healthfacilities(code);
CREATE INDEX healthfacilities_idx1 ON healthfacilities(district);

CREATE TABLE reporters(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    telephone TEXT NOT NULL DEFAULT '',
    alternate_tel TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    imei TEXT NOT NULL DEFAULT '',
    smscode TEXT NOT NULL DEFAULT '',
    reporting_location BIGINT REFERENCES locations(id), --village
    uuid TEXT NOT NULL DEFAULT '', -- this is the rapidpro uuid
    uuid2 TEXT NOT NULL DEFAULT '', -- rapidpro uuid for alternate_tel
    district_id BIGINT REFERENCES locations,
    reporting_location_name text not null default '',
    is_active BOOLEAN NOT NULL DEFAULT 't',
    total_reports INTEGER NOT NULL DEFAULT 0,
    last_reporting_date DATE,
    created_by INTEGER REFERENCES users(id), -- like actor id
    facilityid INTEGER REFERENCES healthfacilities(id),
    groups INTEGER [],
    jparents JSON DEFAULT '{}',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX reporters_idx1 ON reporters(telephone);
CREATE INDEX reporters_idx2 ON reporters(alternate_tel);
CREATE INDEX reporters_idx3 ON reporters(created);
CREATE INDEX reporters_idx4 ON reporters(district_id);
CREATE INDEX reporters_idx5 ON reporters(uuid);

CREATE TABLE reporter_healthfacility(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    reporter_id BIGINT NOT NULL REFERENCES reporters(id),
    facility_id BIGINT REFERENCES healthfacilities(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reporter_groups(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    descr TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reporter_groups_reporters(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    group_id INTEGER REFERENCES reporter_groups(id),
    reporter_id BIGINT REFERENCES reporters(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE  dhis2_mtrack_indicators_mapping(
    id SERIAL PRIMARY KEY NOT NULL,
    form TEXT NOT NULL DEFAULT '', -- mTrac Form e.g cases, death
    slug TEXT NOT NULL DEFAULT '', -- command variable in mTrac
    cmd TEXT NOT NULL DEFAULT '', -- mTrac commands e.g ma, ch, tf
    form_order INTEGER, -- order they appear in case of HTML form generation
    description TEXT NOT NULL DEFAULT '',
    shortname TEXT NOT NULL DEFAULT '',
    dataset TEXT NOT NULL DEFAULT '',
    dataelement TEXT NOT NULL DEFAULT '',
    category_combo TEXT NOT NULL DEFAULT '',
    threshold INTEGER,
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX dhis2_mtrack_indicators_mapping_idx ON dhis2_mtrack_indicators_mapping(form);
CREATE INDEX dhis2_mtrack_indicators_mapping_idx1 ON dhis2_mtrack_indicators_mapping(slug);
CREATE INDEX dhis2_mtrack_indicators_mapping_idx3 ON dhis2_mtrack_indicators_mapping(dataelement);

-- used for scheduling messages
CREATE TABLE schedules(
    id SERIAL PRIMARY KEY NOT NULL,
    type TEXT NOT NULL DEFAULT 'sms', -- also 'push_contact'
    params JSON NOT NULL DEFAULT '{}'::json,
    run_time TIMESTAMP NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'ready',
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX schedules_idx ON schedules(run_time);
CREATE INDEX schedules_idx1 ON schedules(type);
CREATE INDEX schedules_idx2 ON schedules(status);

CREATE TABLE alerts(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    district_id BIGINT REFERENCES locations(id),
    reporting_location BIGINT REFERENCES locations(id),
    alert TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE kannel_stats(
    id SERIAL PRIMARY KEY NOT NULL,
    month TEXT NOT NULL DEFAULT '',
    stats JSON NOT NULL DEFAULT '{}'::json,
    created TIMESTAMP NOT NULL DEFAULT NOW(),
    updated TIMESTAMP NOT NULL DEFAULT NOW()
);

-- used to prevent spamming
CREATE TABLE bulksms_log (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    user_id BIGINT REFERENCES users(id),
    msg TEXT,
    groups TEXT,
    districts TEXT,
    facilities TEXT,
    created TIMESTAMP NOT NULL DEFAULT NOW(),
    updated TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX bulksms_log_userid ON bulksms_log(user_id);
CREATE INDEX bulksms_log_msg ON bulksms_log(msg);
CREATE INDEX bulksms_log_groups ON bulksms_log(groups);
CREATE INDEX bulksms_log_districts ON bulksms_log(districts);
CREATE INDEX bulksms_log_created ON bulksms_log(created);

CREATE TABLE bulksms_limits(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    user_id BIGINT REFERENCES users(id),
    day DATE,
    sms_queued BIGINT NOT NULL DEFAULT 0,
    created TIMESTAMP NOT NULL DEFAULT NOW(),
    updated TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX bulksms_limits_userid ON bulksms_limits(user_id);

CREATE VIEW anonymousreports_view AS
    SELECT
        a.id, a.report, a.topic, a.action, a.action_center, a.action_taken, a.comment,
        a.created, a.facilityid, a.districtid, b.name AS facility, c.name AS district
    FROM
        anonymousreports a
        LEFT OUTER JOIN healthfacilities b ON (a.facilityid = b.id)
        LEFT OUTER JOIN locations c ON (a.districtid = c.id);

CREATE VIEW sms_stats AS
    SELECT
        id,
        month,
        stats->>'mtn_in' as mtn_in,
        stats->>'mtn_out' as mtn_out,
        stats->>'airtel_in' as airtel_in,
        stats->>'airtel_out' as airtel_out,
        stats->>'africel_in' as africel_in,
        stats->>'africel_out' as africel_out,
        stats->>'utl_in' as utl_in,
        stats->>'utl_out' as utl_out,
        stats->>'others_in' as others_in,
        stats->>'others_out' as others_out,
        stats->>'total_in' as total_in,
        stats->>'total_out' as total_out,
        created,
        updated
    FROM kannel_stats;


INSERT INTO user_roles(name, descr)
VALUES('Administrator','For the Administrators'), ('District Users', 'For the district users'), ('Partners', 'The partners');

INSERT INTO user_role_permissions(user_role, sys_module,sys_perms)
VALUES
        ((SELECT id FROM user_roles WHERE name ='Administrator'),'Users','rw');

INSERT INTO users(firstname,lastname,username,telephone,password,email,user_role,is_system_user)
VALUES
        ('Samuel','Sekiwere','admin', '+256782820208', crypt('admin',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Administrator'),'t'),
        ('Guest','User','guest', '+256753475676', crypt('guest',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='District Users'),'t'),
        ('Ivan','Muguya','ivan', '+256756253430', crypt('ivan',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Partners'),'f');

INSERT INTO reporter_groups (name, descr)
VALUES
    ('VHT', 'Village Health Team Members'),
    ('HC', 'Health Workers'),
    ('', ''),
    ('DHO', 'District Health Officer'),
    ('', '');

INSERT INTO healthfacility_type(name) values
    ('HC II'), ('HC III'), ('HC IV'), ('General Hospital'), ('NR Hospital'), ('RR Hospital'), ('Clinic');

CREATE OR REPLACE FUNCTION public.get_district(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r TEXT := '';
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT name into r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'district');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_district_id(loc_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r BIGINT;
        our_lft BIGINT;
        our_rght BIGINT;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT id INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'district');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_subcounty_id(loc_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r BIGINT;
        our_lft BIGINT;
        our_rght BIGINT;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT id INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'subcounty');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_ancestor_by_type(loc_id bigint, atype text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r TEXT := '';
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT name INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = atype);
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_location_name(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
        xname TEXT;
    BEGIN
        SELECT INTO xname name FROM locations WHERE id = loc_id;
        IF xname IS NULL THEN
            RETURN '';
        END IF;
        RETURN xname;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_reporter_groups(_reporter_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
    r TEXT;
    p TEXT;
    BEGIN
        r := '';
        FOR p IN SELECT name FROM reporter_groups WHERE id IN
            (SELECT group_id FROM reporter_groups_reporters WHERE reporter_id = _reporter_id) LOOP
            r := r || p || ',';
        END LOOP;
        RETURN rtrim(r,',');
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_reporter_groups2(_reporter_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
    r TEXT;
    p TEXT;
    BEGIN
        r := '';
        FOR p IN SELECT name FROM reporter_groups WHERE id IN
            (SELECT unnest(groups) FROM reporters WHERE id = _reporter_id) LOOP
            r := r || p || ',';
        END LOOP;
        RETURN rtrim(r,',');
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_reporter_location(tel text)
    RETURNS bigint
    LANGUAGE plpgsql
AS $function$
    DECLARE
        location_id bigint;
    BEGIN
        SELECT INTO location_id reporting_location FROM reporters
        WHERE telephone = tel OR alternate_tel = tel;
        IF location_id IS NULL THEN
            RETURN 0;
        END IF;
        RETURN location_id;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_reporter_name(tel text)
    RETURNS text
    LANGUAGE plpgsql
AS $function$
    DECLARE
        xname text;
    BEGIN
        SELECT INTO xname firstname || ' ' || lastname  FROM reporters
        WHERE telephone = tel OR alternate_tel = tel;
        IF xname IS NULL THEN
            RETURN '';
        END IF;
        RETURN xname;
    END;
$function$;



CREATE OR REPLACE FUNCTION public.get_facility_week_reports(facilitycode text, yr int, wk text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
    r TEXT;
    p TEXT;
    BEGIN
        r := '';
        FOR p IN SELECT distinct report_type FROM requests WHERE facility = facilitycode
            AND year = yr AND week = wk AND status IN ('inprogress', 'pending', 'ready', 'failed', 'completed') LOOP
            r := r || p || ',';
        END LOOP;
        RETURN rtrim(r,',');
    END;
$function$;

CREATE OR REPLACE FUNCTION pp_json(j TEXT, sort_keys BOOLEAN = TRUE, indent TEXT = '    ')
RETURNS TEXT AS $$
    import json
    return json.dumps(json.loads(j), indent=2, sort_keys=True)
$$ LANGUAGE plpython3u;

CREATE OR REPLACE FUNCTION urlencode(msg TEXT)
RETURNS TEXT AS $$
    import requests
    return requests.utils.quote(msg)
$$ LANGUAGE plpython3u;


-- Dispatcher-2.1 comes with thes as well
CREATE OR REPLACE FUNCTION is_valid_json(p_json text)
  RETURNS BOOLEAN
AS $$
	BEGIN
		return (p_json::json is not null);
		EXCEPTION WHEN OTHERS THEN
			return false;
	END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE EXTENSION IF NOT EXISTS xml2;
CREATE OR REPLACE FUNCTION xml_pretty(xml text)
RETURNS xml AS $$
        SELECT xslt_process($1,
'<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:strip-space elements="*" />
<xsl:output method="xml" indent="yes" />
<xsl:template match="node() | @*">
<xsl:copy>
<xsl:apply-templates select="node() | @*" />
</xsl:copy>
</xsl:template>
</xsl:stylesheet>')::xml
$$ LANGUAGE SQL IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION body_pprint(body text)
    RETURNS TEXT AS $$
    BEGIN
        IF xml_is_well_formed_document(body) THEN
            return xml_pretty(body)::text;
        ELSIF is_valid_json(body) THEN
            return pp_json(body, 't', '    ');
        ELSE
            return body;
        END IF;
    END;
$$ LANGUAGE plpgsql;

CREATE VIEW reporters_view AS
    SELECT a.id, a.firstname, a.lastname, a.telephone, a.alternate_tel, a.email,
        a.reporting_location, a.created_by, a.district_id, a.total_reports, a.last_reporting_date, a.is_active, a.uuid,
        get_reporter_groups(a.id) as role, a.created, b.name as loc_name,
        b.code as location_code, d.name as facility, c.facility_id as facilityid, d.code as facilitycode
    FROM reporters a, locations b, reporter_healthfacility c, healthfacilities d
    WHERE a.reporting_location = b.id AND (a.id = c.reporter_id AND d.id = c.facility_id);

-- REQUESTS VIEW -- run only after dispatcher2 runs
CREATE VIEW requests_view AS
    SELECT a.id, a.source, a.destination, a.body, a.ctype, a.status, a.statuscode, a.errors,
        a.submissionid, a.week, a.month, a.year, a.msisdn, a.facility, a.district, a.report_type, a.raw_msg,
        a.edited_raw_msg, a.is_edited,
        a.created, b.name facility_name, a.extras
    FROM requests a, healthfacilities b
    WHERE a.facility = b.code AND body_is_query_param = 'f';

CREATE VIEW rejected_reports_view AS
    SELECT a.id, a.source, a.destination, a.body, a.response, a.status, a.statuscode, a.errors,
        a.submissionid, a.week, a.month, a.year, a.msisdn, a.facility, a.district, a.report_type, a.raw_msg,
        a.edited_raw_msg, a.is_edited,
        a.created, b.name facility_name, a.extras
    FROM rejected_reports a, healthfacilities b
    WHERE a.facility = b.code;



DROP VIEW IF EXISTS reporters_view1;
CREATE view reporters_view1 AS
SELECT a.id,
    a.firstname, a.lastname, (a.firstname || ' '::text) || a.lastname AS name,
    a.telephone, a.alternate_tel, a.email, a.imei, a.smscode, a.reporting_location, a.created_by, a.district_id,
    a.uuid, a.uuid2, a.total_reports, a.last_reporting_date, get_reporter_groups2(a.id) AS role, a.created, a.updated,
    b.name AS loc_name, b.code AS location_code, d.name AS facility, a.facilityid,
    a.jparents->>'p' as parishid, a.jparents->>'s' as subcountyid, d.code AS facilitycode
   FROM reporters a,
    locations b,
    healthfacilities d
  WHERE a.reporting_location = b.id AND d.id = a.facilityid;


CREATE OR REPLACE FUNCTION requests_after_insert() RETURNS TRIGGER AS
$delim$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            IF NEW.msisdn IS NOT NULL AND NEW.facility IS NOT NULL THEN
                UPDATE reporters SET last_reporting_date = NOW(), total_reports = total_reports + 1
                    WHERE telephone = NEW.msisdn OR alternate_tel = NEW.msisdn;
                UPDATE healthfacilities SET last_reporting_date = NOW()
                    WHERE code = NEW.facility;
            END IF;
            RETURN NEW;
        END IF;
    END;
$delim$ LANGUAGE plpgsql;

CREATE TRIGGER requests_after_insert AFTER INSERT ON requests
    FOR EACH ROW EXECUTE PROCEDURE requests_after_insert();

-- Polling tables
CREATE TABLE polls(
    id SERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(8) NOT NULL CHECK(type IN('yn', 't', 'n')),
    question TEXT NOT NULL DEFAULT '',
    default_response TEXT NOT NULL DEFAULT '',
    start_date timestamptz,
    end_date timestamptz,
    districts INTEGER [] DEFAULT '{}'::INT[],
    groups INTEGER [] DEFAULT '{}'::INT[],
    recipient_count INTEGER NOT NULL DEFAULT 0,
    response_count INTEGER NOT NULL DEFAULT 0,
    created timestamptz DEFAULT current_timestamp,
    updated timestamptz DEFAULT current_timestamp
);
CREATE INDEX polls_idx1 ON polls(name);

CREATE TABLE poll_recipients(
    id bigserial PRIMARY KEY NOT NULL,
    poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    reporter_id INTEGER NOT NULL REFERENCES reporters(id) ON DELETE CASCADE
);
CREATE INDEX poll_recipients_idx1 ON poll_recipients(poll_id);

CREATE TABLE poll_responses(
    id bigserial PRIMARY KEY NOT NULL,
    poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    reporter_id INTEGER NOT NULL REFERENCES reporters(id) ON DELETE CASCADE,
    message TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '', -- what this response has been categorized as
    created timestamptz DEFAULT current_timestamp,
    UNIQUE(poll_id, reporter_id)
);
CREATE INDEX poll_responses_idx1 ON poll_responses(poll_id);

CREATE OR REPLACE FUNCTION poll_responses_after_insert() RETURNS TRIGGER AS
$delim$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            IF NEW.poll_id IS NOT NULL THEN
                UPDATE polls SET response_count = response_count + 1
                WHERE id = NEW.poll_id;
            END IF;
            RETURN NEW;
        END IF;
    END;
$delim$ LANGUAGE plpgsql;

CREATE TRIGGER poll_responses_after_insert AFTER INSERT ON poll_responses
    FOR EACH ROW EXECUTE PROCEDURE poll_responses_after_insert();

CREATE OR REPLACE FUNCTION poll_recipients_after_insert() RETURNS TRIGGER AS
$delim$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            IF NEW.poll_id IS NOT NULL THEN
                UPDATE polls SET recipient_count = recipient_count + 1
                WHERE id = NEW.poll_id;
            END IF;
            RETURN NEW;
        END IF;
    END;
$delim$ LANGUAGE plpgsql;

CREATE TRIGGER poll_recipients_after_insert AFTER INSERT ON poll_recipients
    FOR EACH ROW EXECUTE PROCEDURE poll_recipients_after_insert();

CREATE VIEW polls_view AS
    SELECT
        a.firstname || ' ' || a.lastname as name,
        a.telephone, b.name as distrtict, c.name as facility,
        d.poll_id, d.message, d.category, to_char(d.created, 'YYYY-mm-dd HH:MI') as created
    FROM
        reporters a, locations b, healthfacilities c, poll_responses d
    WHERE
        d.reporter_id = a.id
        AND
        a.district_id = b.id
        AND
        c.id = a.facilityid;

CREATE OR REPLACE FUNCTION update_facility_reporters_location (fid BIGINT) RETURNS BOOLEAN AS
$delim$
    DECLARE
    loc_id bigint;
    loc_name text;
    d_id bigint;
    dname text;
    fcode text;
    BEGIN
        SELECT code, location, location_name, district_id, district INTO fcode, loc_id, loc_name, d_id, dname FROM
            healthfacilities WHERE id = fid;
        UPDATE reporters SET (reporting_location, reporting_location_name, district_id, updated)
            = (loc_id, loc_name, d_id, NOW()) WHERE facilityid = fid;
        UPDATE requests SET district = dname WHERE facility = fcode;
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;


-- Add tables for transfers
CREATE TABLE transfers(
    id bigserial PRIMARY KEY NOT NULL,
    from_district BIGINT REFERENCES locations(id),
    to_district BIGINT REFERENCES locations(id),
    reporting_location BIGINT REFERENCES locations(id),
    facilityid BIGINT REFERENCES healthfacilities(id),
    reason TEXT,  
    created timestamptz DEFAULT current_timestamp,
    updated timestamptz DEFAULT current_timestamp
);
