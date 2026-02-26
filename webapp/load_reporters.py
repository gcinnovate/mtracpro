import phonenumbers
import getopt
import sys
import simplejson
import psycopg2
import psycopg2.extras
from webapp.settings import config

cmd = sys.argv[1:]
opts, args = getopt.getopt(cmd, 'f:', [])
filename = ''
for option, parameter in opts:
        if option == '-f':
            filename = parameter

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


def format_msisdn(msisdn=""):
    """ given a msisdn, return in E164 format """
    if not msisdn:
        return ""
    msisdn = msisdn.replace(' ', '')
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return ""
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)

with open(filename) as f:
    for l in f:
        reporter = l.strip().split("#")
        name, phone, district, facility, roles, is_active, facility_code = tuple(reporter)
        # print tuple(reporter)
        names = name.split(' ', 1)
        if len(names) > 1:
            firstname = names[1].title()
            lastname = names[0].title()
        else:
            firstname = ''
            lastname = names[0].title()
        if is_active == 'f':
            continue
        cur.execute("SELECT id FROM reporters WHERE telephone='%s'" % phone)
        res = cur.fetchone()
        if res:  # we already have reporter
            # XXX # XXX XXX
            # continue
            # XXX # XXX XXX
            print("Updating Reporter:", phone)

            reporter_id = res['id']
            cur.execute(
                "SELECT id, district_id, location, location_name "
                "FROM healthfacilities WHERE code = %s", [facility_code])
            f = cur.fetchone()
            if f:
                print("Falcility Exists", facility_code, f['district_id'])
                cur.execute(
                    "UPDATE reporters SET (firstname, lastname, district_id, reporting_location, "
                    " reporting_location_name, facilityid, groups, updated) = (%s, %s, %s, %s, %s, %s,"
                    "(SELECT array_agg(id) FROM reporter_groups WHERE name IN "
                    "(SELECT name FROM  regexp_split_to_table(%s, E',') as name)), NOW()) WHERE id = %s",
                    [
                        firstname, lastname, f['district_id'],
                        f['location'], f['location_name'],
                        f['id'], roles, reporter_id])
                conn.commit()

        else:  # new reporter
            # print tuple(reporter)
            cur.execute(
                "SELECT id, district_id, location, location_name "
                "FROM healthfacilities WHERE code = %s", [facility_code])
            f = cur.fetchone()
            if f:
                reporterSQL = (
                    "INSERT INTO reporters(firstname, lastname, telephone, district_id, "
                    "reporting_location, reporting_location_name, facilityid, groups, jparents) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, "
                    "(SELECT array_agg(id) FROM reporter_groups WHERE name IN "
                    "(SELECT name FROM  regexp_split_to_table(%s, E',') as name))::INT[], "
                    "%s::json) RETURNING id"
                )
                ancestor_locations = psycopg2.extras.Json({
                    'd': f['district_id'],
                    's': f['location']}, dumps=simplejson.dumps)
                cur.execute(reporterSQL, [
                    firstname, lastname, phone, f['district_id'],
                    f['location'], f['location_name'], f['id'], roles, ancestor_locations])
                conn.commit()
            else:
                # try DHO's Office
                if facility.__contains__('DHO') or facility == district or True:
                    cur.execute(
                        "SELECT id, district_id, location, location_name FROM healthfacilities WHERE name = %s",
                        [district + " DHO Office"])
                    dres = cur.fetchone()
                    if dres:
                        f = dres
                        reporterSQL = (
                            "INSERT INTO reporters(firstname, lastname, telephone, district_id, "
                            "reporting_location, reporting_location_name, facilityid, groups) "
                            "VALUES(%s, %s, %s, %s, %s, %s, %s, "
                            "(SELECT array_agg(id) FROM reporter_groups WHERE name IN "
                            "(SELECT name FROM  regexp_split_to_table(%s, E',') as name))::INT[]) RETURNING id"
                        )
                        cur.execute(reporterSQL, [
                            firstname, lastname, phone, f['district_id'],
                            f['location'], f['location_name'], f['id'], roles])

                        conn.commit()
                        rs = cur.fetchone()
                    print(district, phone, facility_code)
                else:
                    # facilities not synchronized
                    print("Other=>", l.strip())
conn.close()
