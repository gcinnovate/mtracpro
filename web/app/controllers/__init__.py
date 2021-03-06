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
from settings import (
    COMPLETE_REPORTS_KEYWORDS,
    THRESHOLD_ALERT_ROLES,
    GENERAL_ALERT_ROLES)

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

roles = []
rolesById = {}
reporterRolesByName = {}
rs = db.query("SELECT id, name from reporter_groups order by name")
for r in rs:
    roles.append({'id': r['id'], 'name': r['name']})
    rolesById[r['id']] = r['name']
    reporterRolesByName[r['name']] = r['id']

userRolePermissions = {}  # eg {'Administrator': []}
userRolesByName = {}
rs = db.query("SELECT id, name from user_roles order by name")
for r in rs:
    userRolesByName[r['name']] = r['id']
    userRolePermissions[r['name']] = []

# Populate userRolePermissions
rs = db.query(
    "SELECT a.name, b.codename "
    "FROM user_roles a, permissions b, user_role_permissions c "
    "WHERE (c.user_role = a.id) AND (c.permission_id = b.id)")
for r in rs:
    userRolePermissions[r['name']].append(r['codename'])

Permissions = []
rs = db.query("SELECT id, name || ' -> [' || sys_module || ']' As name FROM permissions ORDER BY sys_module, id")
for r in rs:
    Permissions.append({'id': r['id'], 'name': r['name']})

notifyingParties = {}
ourDistricts = []
allDistricts = {}
allDistrictsByName = {}  # make use in pages easy
rs = db.query("SELECT id, name FROM  locations WHERE type_id = 3 ORDER BY name")
for r in rs:
    ourDistricts.append({'id': r['id'], 'name': r['name']})
    allDistricts[r['id']] = r['name']
    allDistrictsByName[r['name']] = r['id']

    if r['id'] not in notifyingParties:
        notifyingParties[r['id']] = {
            'threshold_alert_contacts': [], 'general_alert_contacts': []}

    # here we save telephone numbers of threshold notifying parties at district level
    threshold_alert_roles = [
        int(reporterRolesByName[x]) for x in THRESHOLD_ALERT_ROLES if x in reporterRolesByName]
    rxx = db.query(
        "SELECT uuid, telephone, facilityid FROM reporters WHERE district_id = $districtid AND "
        " (groups && '%s'::INT[])" % str(threshold_alert_roles).replace(
            '[', '{').replace(']', '}').replace('\'', '\"'), {'districtid': r['id']})

    for contact in rxx:
        notifyingParties[r['id']]['threshold_alert_contacts'].append(contact['uuid'])

    general_alert_roles = [
        int(reporterRolesByName[x]) for x in GENERAL_ALERT_ROLES if x in reporterRolesByName]
    ryy = db.query(
        "SELECT uuid, telephone, facilityid FROM reporters WHERE district_id = $districtid AND "
        " (groups && '%s'::INT[])" % str(general_alert_roles).replace(
            '[', '{').replace(']', '}').replace('\'', '\"'), {'districtid': r['id']})

    for contact in ryy:
        notifyingParties[r['id']]['general_alert_contacts'].append(contact['uuid'])

facilityLevels = {}
rs = db.query("SELECT id, name FROM healthfacility_type")
for r in rs:
    facilityLevels[r['id']] = r['name']

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

IndicatorMapping = {}  # {'slug': {'descr': 'Malaria Cases', 'dhis2_id': '', 'dhis2_combo_id': '', 'threshold': ''}}
Indicators = {}  # Form: {'cases': {'dataelement': {'slug': 'cases_ma'}, 'dataelement', {'slug': 'cases_me'}}}
IndicatorsByFormOrder = {}  # {'cases': [{'slug': 'cases_ma', 'description': 'Malaria Cases'}, {}, {}, ...]}
IndicatorsDataSet = {}  # {'cases': 'V4....', 'epc': '....', 'epd': ''} # mapping forms to datasets
DataElementPosition = {}
CategoryComboPosition = {}  # position for category combo - combos are different for forms like mat
IndicatorsCategoryCombos = {}
rs = db.query(
    "SELECT form, slug, description, dataelement, dataset, category_combo, threshold, form_order "
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
        'descr': r['description'], 'dhis2_id': r['dataelement'],
        'dhis2_combo_id': r['category_combo'], 'threshold': r['threshold']}
    if r['form'] not in IndicatorsCategoryCombos:
        IndicatorsCategoryCombos[r['form']] = {}
        IndicatorsCategoryCombos[r['form']][r['slug']] = r['category_combo']
    else:
        IndicatorsCategoryCombos[r['form']][r['slug']] = r['category_combo']

    if r['form'] not in IndicatorsDataSet:
        IndicatorsDataSet[r['form']] = r['dataset']

if settings.DEBUG:
    import pprint
    pprint.pprint(Indicators)
    pprint.pprint(IndicatorsByFormOrder)
    pprint.pprint(IndicatorsCategoryCombos)
    pprint.pprint(IndicatorMapping)
    pprint.pprint(DataElementPosition)
    pprint.pprint(notifyingParties)
    pprint.pprint(IndicatorsDataSet)


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
    ret_list = ['' for i in range(23)]  # make 12 here MAX_INDICATORS
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
                if form in getattr(settings, 'SPECIAL_FORMS', ['mat']):
                    # ret += "%s" % d['value'] + " " + categoryOptionCombos[d['categoryOptionCombo']] + "\n"
                    ret_list[CategoryComboPosition[d['categoryOptionCombo']]] = (
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
    year, week = get_current_week(datetime.datetime.now())
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


def anonymous_report_responses(report_id):
    ret = "<ul>"
    x = db.query(
        "SELECT message, direction FROM anonymousreport_messages "
        "WHERE report_id = $id ORDER by id", {'id': report_id})
    for rpt in x:
        if rpt['direction'] == 'O':
            prefix = ">> "
        else:
            prefix = "<< "
        ret += "<li>%s</li>" % (prefix + rpt['message'])
    ret += "</ul>"
    return ret


def fromAndroid(sid):
    if serversById[sid] == 'mTracPro_android':
        return True
    return False


def hasPermission(perm, user_group, user_perms):
    if user_group in userRolePermissions:
        if perm in userRolePermissions[user_group]:
            return True
    if perm in user_perms:
        return True
    return False

myFilters = {
    'datetimeformat': datetimeformat,
    'datetimeformat2': datetimeformat2,
    'formatmsg': formatmsg,
    'facilityLevel': facilityLevel,
    'getDistrict': getDistrict,
    'hasCompleteReport': hasCompleteReport,
    'server_apps': server_apps,
    'fromAndroid': fromAndroid,
    'anonymousResponses': anonymous_report_responses,
    'hasPermission': hasPermission
}

# Jinja2 Template options
render = render_jinja(
    absolute('app/views'),
    encoding='utf-8'
)

render._lookup.globals.update(
    ses=get_session(), roles=roles, districts=ourDistricts, permissions=Permissions,
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
