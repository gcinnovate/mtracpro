# -*- coding: utf-8 -*-

"""Mako template options which are used, basically, by all handler modules in
controllers of the app.
"""

# from web.contrib.template import render_mako
import web
import json
import datetime
import settings
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
categoryOptionCombos = {}
rs = db.query("SELECT dataelement, description, category_combo FROM dhis2_mtrack_indicators_mapping")
for r in rs:
    dataElements[r['dataelement']] = r['description']
    categoryOptionCombos[r['category_combo']] = r['description']

ourDistricts = []
allDistricts = {}
allDistrictsByName = {}  # make use in pages easy
rs = db.query("SELECT id, name FROM  locations WHERE type_id = 3 ORDER BY name")
for r in rs:
    ourDistricts.append({'id': r['id'], 'name': r['name']})
    allDistricts[r['id']] = r['name']
    allDistrictsByName[r['name']] = r['id']

facilityLevels = {}
rs = db.query("SELECT id, name FROM healthfacility_type")
for r in rs:
    facilityLevels[r['id']] = r['name']

roles = []
rolesById = {}
rs = db.query("SELECT id, name from reporter_groups order by name")
for r in rs:
    roles.append({'id': r['id'], 'name': r['name']})
    rolesById[r['id']] = r['name']

userRolesByName = {}
rs = db.query("SELECT id, name from user_roles order by name")
for r in rs:
    userRolesByName[r['name']] = r['id']

ourServers = []
serversById = {}
serversByName = {}
serverApps = {}
rs = db.query("SELECT id, name FROM servers order BY name")
for r in rs:
    serversById[r['id']] = r['name']
    serversByName[r['name']] = r['id']
    ourServers.append({'id': r['id'], 'name': r['name']})
    x = db.query(
        "SELECT allowed_sources FROM server_allowed_sources WHERE server_id=$id",
        {'id': r['id']})
    if x:
        serverApps[r['id']] = x[0]['allowed_sources']

IndicatorMapping = {}  # {'slug': {'descr': 'Malaria Cases', 'dhis2_id': '', 'dhis2_combo_id': ''}}
Indicators = {}  # Form: {'cases': {'dataelement': {'slug': 'cases_ma'}, 'dataelement', {'slug': 'cases_me'}}}
IndicatorsByFormOrder = {}  # {'cases': [{'slug': 'cases_ma', 'description': 'Malaria Cases'}, {}, {}, ...]}
DataElementPosition = {}
CategoryComboPosition = {}  # position for category combo - combos are different for forms like mat
IndicatorsCategoryCombos = {}
rs = db.query(
    "SELECT form, slug, description, dataelement, category_combo, form_order "
    " FROM dhis2_mtrack_indicators_mapping "
    "ORDER BY form, form_order")
for r in rs:
    if r['form'] not in Indicators:
        Indicators[r['form']] = {}
        Indicators[r['form']][r['dataelement']] = {'slug': r['slug']}
    else:
        Indicators[r['form']][r['dataelement']] = {'slug': r['slug']}

    if r['form'] not in IndicatorsByFormOrder:
        IndicatorsByFormOrder[r['form']] = []
        IndicatorsByFormOrder[r['form']].append({'slug': r['slug'], 'description': r['description']})
    else:
        IndicatorsByFormOrder[r['form']].append({'slug': r['slug'], 'description': r['description']})
    DataElementPosition[r['dataelement']] = r['form_order']
    CategoryComboPosition[r['category_combo']] = r['form_order']
    IndicatorMapping[r['slug']] = {
        'descr': r['description'], 'dhis2_id': r['dataelement'], 'dhis2_combo_id': r['category_combo']}
    if r['form'] not in IndicatorsCategoryCombos:
        IndicatorsCategoryCombos[r['form']] = {}
        IndicatorsCategoryCombos[r['form']][r['slug']] = r['category_combo']
    else:
        IndicatorsCategoryCombos[r['form']][r['slug']] = r['category_combo']
import pprint
# pprint.pprint(Indicators)
# pprint.pprint(IndicatorsByFormOrder)
pprint.pprint(IndicatorsCategoryCombos)
pprint.pprint(IndicatorMapping)
# pprint.pprint(DataElementPosition)


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


def datetimeformat2(value, fmt='%Y-%m-%d %H:%M'):
    if not value:
        return ''
    return value.strftime(fmt)


def formatmsg(msg, form='cases'):
    ret = "<ul>"
    ret_list = ['' for i in range(20)]  # make 12 here MAX_INDICATORS
    try:
        body = json.loads(msg)
    except:
        body = {}
    if body:
        datavalues = body['dataValues']
        for d in datavalues:
            try:  # XXX for cases where we dont have the key
                if form in getattr(settings, 'SPECIAL_FORMS', ['mat']):  # the mat form is a special case
                    # ret += "<li><small>%s" % d['value'] + " " + categoryOptionCombos[d['categoryOptionCombo']] + "</small></li>"
                    ret_list[CategoryComboPosition[d['categoryOptionCombo']]] = (
                        "<li><small>%s %s</small></li>") % (
                            d['value'], categoryOptionCombos[d['categoryOptionCombo']])
                else:
                    # ret += "<li><small>%s" % d['value'] + " " + dataElements[d['dataElement']] + "</small></li>"
                    ret_list[DataElementPosition[d['dataElement']]] = (
                        "<li><small>%s %s</small></li>") % (
                            d['value'], dataElements[d['dataElement']])
            except:
                pass
        ret += ''.join(ret_list)
    ret += "</ul>"
    return ret


def formatMsgForAndroid(msg, form='cases'):
    ret = "You reported:\n"
    ret_list = ['' for i in range(20)]  # make 12 here MAX_INDICATORS
    try:
        body = json.loads(msg)
    except:
        body = {}
    if body:
        datavalues = body['dataValues']
        for d in datavalues:
            try:  # XXX for cases where we dont have the key
                if form == 'mat':
                    # ret += "%s" % d['value'] + " " + categoryOptionCombos[d['categoryOptionCombo']] + "\n"
                    ret_list[DataElementPosition[d['dataElement']]] = (
                        "%s %s\n") % (d['value'], categoryOptionCombos[d['categoryOptionCombo']])
                else:
                    # ret += "%s" % d['value'] + " " + dataElements[d['dataElement']] + "\n"
                    ret_list[DataElementPosition[d['dataElement']]] = (
                        "%s %s\n") % (d['value'], dataElements[d['dataElement']])
            except:
                pass
        ret += ''.join(ret_list)
    else:
        return ""
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


def server_apps(val):
    ret = "<ul>"
    if val not in serverApps or not serverApps[val]:
        x = db.query(
            "SELECT allowed_sources FROM server_allowed_sources WHERE server_id = $id", {'id': val})
        if x:
            serverApps[val] = x[0]['allowed_sources']
    for i in serverApps[val]:
        ret += "<li>%s</li>" % serversById[i]

    ret += "</ul>"
    return ret

myFilters = {
    'datetimeformat': datetimeformat,
    'datetimeformat2': datetimeformat2,
    'formatmsg': formatmsg,
    'facilityLevel': facilityLevel,
    'getDistrict': getDistrict,
    'hasCompleteReport': hasCompleteReport,
    'server_apps': server_apps
}

# Jinja2 Template options
render = render_jinja(
    absolute('app/views'),
    encoding='utf-8'
)

render._lookup.globals.update(
    ses=get_session(), roles=roles, districts=ourDistricts,
    year=datetime.datetime.now().strftime('%Y')
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
