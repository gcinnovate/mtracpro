#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"
import pprint
import psycopg2
import psycopg2.extras
from settings import config
import getopt
import sys
import datetime
import xlsxwriter
from settings import BASE_DIR

DOWNLOADS_DIR = BASE_DIR + "/static/downloads/"

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 's:e:d:t:h',
    ['start-date', 'end-date', 'district', 'reporter-type'])


def usage():
    return """usage: python caramal_reports.py [-s <start-date>] [-e <end-date>] [-d <district>] [-t <reporter-type>] [-h]
    -s start date for exporting reports into excel
    -e end date for exporting reports into excel
    -d district for which to genereate reports
    -t type of reporter for whom to generate reports
    -h Show this message
    """

now = datetime.datetime.now()
sdate = now - datetime.timedelta(days=180, minutes=5)  # six month back
from_date = sdate.strftime('%Y-%m-%d %H:%M')
end_date = ""
district = ""

reporter_type = ""

for option, parameter in opts:
    if option == 's':
        from_date = parameter
    if option == 'e':
        end_date = parameter
    if option == '-d':
        district = parameter
    if option == '-t':
        reporter_type = "VHT"
    if option == '-h':
        print usage()
        sys.exit(1)

headings = [
    'Phone Number', 'Reporter Name', 'Report', 'Date', 'Week', 'Facility', 'District',
    'Sub-County', 'Parish', 'Village']

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

CARAMAL_INDICATROS = {}
headings_offset = len(headings)

cur.execute(
    "SELECT form, slug, description, dataelement, form_order "
    " FROM dhis2_mtrack_indicators_mapping WHERE form in ('car', 'ras') "
    "ORDER BY form, form_order"
)

res = cur.fetchall()

if res:
    for idx, r in enumerate(res):
        CARAMAL_INDICATROS[r['dataelement']] = {
            'heading': r['description'], 'position': headings_offset + idx}
        headings.append(r['description'])
pprint.pprint(headings)
pprint.pprint(CARAMAL_INDICATROS)

SQL = (
    "SELECT msisdn, get_reporter_name(msisdn) as reporter_name, raw_msg AS report, "
    "to_char(created, 'YYYY-MM-DD HH24:MI') as date, year || 'W' || week AS week, "
    "facility_name, district, get_reporter_location(msisdn) AS reporter_location, "
    "body::json->'dataValues' AS datavalues, "
    "extras::json->>'reporter_type' AS reporter_type, report_type "
    "FROM requests_view WHERE report_type IN ('car', 'ras') AND created > '%s' ")

SQL = SQL % from_date
if end_date:
    SQL = SQL + " AND created <= '%s' " % end_date
if reporter_type:
    SQL = SQL + " AND reporter_type = '%s' " % reporter_type

print SQL

cur.execute(SQL)

sheet_rows = []

res = cur.fetchall()

for r in res:
    # get subcounty, parish, village for reporter
    cur.execute(
        "SELECT get_ancestor_by_type(%s, 'subcounty') AS subcounty, "
        "get_ancestor_by_type(%s, 'parish') AS parish, "
        "get_ancestor_by_type(%s, 'village') AS village", [
            r['reporter_location'], r['reporter_location'], r['reporter_location']])
    locs = cur.fetchone()
    subcounty, parish, village = ('', '', '')
    if locs:
        subcounty = locs['subcounty']
        parish = locs['parish']
        village = locs['village']

    row = ['' for i in range(18)]
    row[0] = r['msisdn']
    row[1] = r['reporter_name']
    row[2] = r['report']
    row[3] = r['date']
    row[4] = r['week']
    row[5] = r['facility_name']
    row[6] = r['district']
    row[7] = subcounty if subcounty is not None else ''
    row[8] = parish if parish is not None else ''
    row[9] = village if village is not None else ''

    datavalues = r['datavalues']
    for dv in datavalues:
        # put the indicators in their right positions in the row
        row[CARAMAL_INDICATROS[dv['dataElement']]['position']] = dv['value']

    sheet_rows.append(row)

# At this point we have the data to write in the sheet
# pprint.pprint(sheet_rows)

export_name = 'Caramal%sReports%s.xlsx' % (reporter_type, district)
workbook = xlsxwriter.Workbook(
    DOWNLOADS_DIR + export_name, {'default_date_format': 'dd/mm/yyyy'})
# set some formats
text_format = workbook.add_format()
text_format.set_num_format('@')
text_format.set_font_size(14)
date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
date_format.set_font_size(14)
bold = workbook.add_format({'bold': True})
bold.set_font_size(14)

worksheet = workbook.add_worksheet()
columns = ['' for i in range(18)]

for idx, heading in enumerate(headings):
    columns[idx] = {'header': heading}

for d in CARAMAL_INDICATROS.values():
    columns[d['position']] = {'header': d['heading']}

worksheet.add_table('A1:R%s' % (1 + len(sheet_rows)), {'data': sheet_rows, 'columns': columns})
worksheet.set_column("A:E", 18, text_format)
worksheet.set_column("C:C", 25, text_format)
worksheet.set_column("F:F", 22, text_format)
worksheet.set_column("G:J", 20, text_format)
worksheet.set_column("K:M", 33, text_format)
worksheet.set_column("N:N", 32, text_format)
worksheet.set_column("O:O", 28, text_format)
worksheet.set_column("P:R", 15, text_format)

workbook.close()

conn.close()
