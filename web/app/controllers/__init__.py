# -*- coding: utf-8 -*-

"""Mako template options which are used, basically, by all handler modules in
controllers of the app.
"""

# from web.contrib.template import render_mako
import web
import json
import datetime
from web.contrib.template import render_jinja
from settings import (absolute, config)
from settings import COMPLETE_REPORTS_KEYWORDS

db_host = config['db_host']
db_name = config['db_name']
db_user = config['db_user']
db_passwd = config['db_passwd']
db_port = config['db_port']

db = web.database(
    dbn='postgres',
    user=db_user,
    pw=db_passwd,
    db=db_name,
    host=db_host,
    port=db_port
)


def get_current_week(date=datetime.datetime.now()):
    """Given date, return the reporting week in the format 2016, 01
    reports coming in this week are for previous one.
    """
    offset_from_last_sunday = datetime.datetime.now().weekday() + 1
    last_sunday = date - datetime.timedelta(days=offset_from_last_sunday)
    year, weeknum, _ = last_sunday.isocalendar()
    return (year, weeknum)

SESSION = ''
APP = None

dataElements = {}
rs = db.query("SELECT dataelement, description FROM dhis2_mtrack_indicators_mapping")
for r in rs:
    dataElements[r['dataelement']] = r['description']

ourDistricts = []
allDistricts = {}
allDistrictsByName = {}  # make use in pages easy
rs = db.query("SELECT id, name FROM  locations WHERE type_id = 3")
for r in rs:
    ourDistricts.append({'id': r['id'], 'name': r['name']})
    allDistricts[r['id']] = r['name']
    allDistrictsByName[r['name']] = r['id']

facilityLevels = {}
rs = db.query("SELECT id, name FROM healthfacility_type")
for r in rs:
    facilityLevels[r['id']] = r['name']


def put_app(app):
    global APP
    APP = app


def get_app():
    global APP
    return APP


def get_session():
    global SESSION
    return SESSION


def datetimeformat(value, fmt='%Y-%m-%d'):
    if not value:
        return ''
    return value.strftime(fmt)


def formatmsg(msg):
    ret = "<ul>"
    try:
        body = json.loads(msg)
    except:
        body = {}
    if body:
        datavalues = body['dataValues']
        for d in datavalues:
            ret += "<li><small>%s" % d['value'] + " " + dataElements[d['dataElement']] + "</small></li>"
    ret += "</ul>"
    return ret


def facilityLevel(facilityid):
    return facilityLevels[facilityid]


def getDistrict(districtid):
    return allDistricts[districtid]


def hasCompleteReport(facilitycode):
    year, week = get_current_week()
    res = db.query(
        "SELECT get_facility_week_reports($fcode, $yr, $wk) as reports",
        {'fcode': facilitycode, 'yr': year, 'wk': '%s' % week})
    if res:
        reports = res[0]['reports']
        no_of_reports = len(reports.split(','))
        if no_of_reports >= len(COMPLETE_REPORTS_KEYWORDS):
            return True
    return False

myFilters = {
    'datetimeformat': datetimeformat,
    'formatmsg': formatmsg,
    'facilityLevel': facilityLevel,
    'getDistrict': getDistrict,
    'hasCompleteReport': hasCompleteReport
}

# Jinja2 Template options
render = render_jinja(
    absolute('app/views'),
    encoding='utf-8'
)

render._lookup.globals.update(
    ses=get_session()
)
render._lookup.filters.update(myFilters)


def put_session(session):
    global SESSION
    SESSION = session
    render._lookup.globals.update(ses=session)


def csrf_token():
    session = get_session()
    if 'csrf_token' not in session:
        from uuid import uuid4
        session.csrf_token = uuid4().hex
    return session.csrf_token


def csrf_protected(f):
    def decorated(*args, **kwargs):
        inp = web.input()
        session = get_session()
        if not ('csrf_token' in inp and inp.csrf_token == session.pop('csrf_token', None)):
            raise web.HTTPError(
                "400 Bad request",
                {'content-type': 'text/html'},
                """Cross-site request forgery (CSRF) attempt (or stale browser form).
<a href="/"></a>.""")  # Provide a link back to the form
        return f(*args, **kwargs)
    return decorated

render._lookup.globals.update(csrf_token=csrf_token)


def require_login(f):
    """usage
    @require_login
    def GET(self):
        ..."""
    def decorated(*args, **kwargs):
        session = get_session()
        if not session.loggedin:
            session.logon_err = "Please Logon"
            return web.seeother("/")
        else:
            session.logon_err = ""
        return f(*args, **kwargs)

    return decorated
