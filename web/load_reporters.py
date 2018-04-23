import phonenumbers
import getopt
import sys
import psycopg2
import psycopg2.extras
from settings import config

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

with open(filename, 'r') as f:
    for l in f:
        reporter = l.strip().split("#")
        name, phone, district, facility, roles, is_active, facility_code = tuple(reporter)
        print tuple(reporter)
        names = name.split(' ', 1)
        if len(names) > 1:
            firstname = names[1]
            lastname = names[0]
        else:
            firstname = ''
            lastname = names[0]
        cur.execute("SELECT id FROM reporters WHERE telephone='%s'" % phone)
        res = cur.fetchone()
        if res:  # we already have reporter
            reporter_id = res['id']
            cur.execute(
                "SELECT id, district_id, location, location_name "
                "FROM healthfacilities WHERE code = %s", [facility_code])
            f = cur.fetchone()
            if f:
                cur.execute(
                    "UPDATE reporters SET (firstname, lastname, district_id, reporting_location, "
                    " reporting_location_name) = (%s, %s, %s, %s, %s) WHERE id = %s",
                    [firstname, lastname, f['district_id'], f['location'], f['location_name'], reporter_id])
                cur.execute(
                    "UPDATE reporter_healthfacility SET facility_id = %s "
                    "WHERE reporter_id = %s", [f['id'], reporter_id])
                cur.execute("DELETE FROM reporter_groups_reporters WHERE reporter_id = %s", [reporter_id])
                reporter_roles = roles.split(',')
                for role in reporter_roles:
                    cur.execute(
                        "INSERT INTO reporter_groups_reporters (reporter_id, group_id) "
                        "VALUES (%s, (SELECT id FROM reporter_groups WHERE name=%s))",
                        [reporter_id, role])
                conn.commit()

        else:  # new reporter
            cur.execute(
                "SELECT id, district_id, location, location_name "
                "FROM healthfacilities WHERE code = %s", [facility_code])
            f = cur.fetchone()
            if f:
                reporterSQL = (
                    "INSERT INTO reporters(firstname, lastname, telephone, district_id, "
                    "reporting_location, reporting_location_name) "
                    "VALUES(%s, %s, %s, %s, %s, %s) RETURNING id"
                )
                cur.execute(reporterSQL, [
                    firstname, lastname, phone, f['district_id'],
                    f['location'], f['location_name']])
                conn.commit()
                rs = cur.fetchone()
                if rs:
                    reporter_id = rs['id']
                    cur.execute(
                        "INSERT INTO reporter_healthfacility (reporter_id, facility_id) "
                        "VALUES (%s, %s)", [reporter_id, f['id']])
                    reporter_roles = roles.split(',')
                    for role in reporter_roles:
                        cur.execute(
                            "INSERT INTO reporter_groups_reporters (reporter_id, group_id) "
                            "VALUES (%s, (SELECT id FROM reporter_groups WHERE name=%s))",
                            [reporter_id, role])
                    conn.commit()
            else:
                # try DHO's Office
                if facility.__contains__('DHO'):
                    cur.execute(
                        "SELECT id, district_id FROM healthfacilities WHERE name = %s",
                        [district + " DHO's Office"])
                    dres = cur.fetchone()
                    if dres:
                        f = dres
                        reporterSQL = (
                            "INSERT INTO reporters(firstname, lastname, telephone, district_id, "
                            "reporting_location, reporting_location_name) "
                            "VALUES(%s, %s, %s, %s, %s, %s) RETURNING id"
                        )
                        cur.execute(reporterSQL, [
                            firstname, lastname, phone, f['district_id'],
                            f['location'], f['location_name']])
                        conn.commit()
                        rs = cur.fetchone()
                        if rs:
                            reporter_id = rs['id']
                            cur.execute(
                                "INSERT INTO reporter_healthfacility (reporter_id, facility_id) "
                                "VALUES (%s, %s)", [reporter_id, f['id']])
                            reporter_roles = roles.split(',')
                            for role in reporter_roles:
                                cur.execute(
                                    "INSERT INTO reporter_groups_reporters (reporter_id, group_id) "
                                    "VALUES (%s, (SELECT id FROM reporter_groups WHERE name=%s))",
                                    [reporter_id, role])
                            conn.commit()
                    print district, phone, facility_code
conn.close()
