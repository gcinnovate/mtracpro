# -*- coding: utf-8 -*-

"""Mako template options which are used, basically, by all handler modules in
controllers of the app.
"""

# from web.contrib.template import render_mako
import web
from web.contrib.template import render_jinja
from settings import (absolute, config)
import json

# Mako Template options
# render = render_mako(
#   directories=[absolute('app/views')],
#   module_directory=absolute('tmp/mako_modules'),
#   cache_dir=absolute('tmp/mako_cache'),
#   input_encoding='utf-8',
#   output_encoding='utf-8',
#   default_filters=['decode.utf8'],
#   encoding_errors='replace',
#   filesystem_checks=DEBUG,
#   collection_size=512
# )

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

SESSION = ''
APP = None

dataElements = {}
rs = db.query("SELECT dataelement, description FROM dhis2_mtrack_indicators_mapping")
for r in rs:
    dataElements[r['dataelement']] = r['description']

ourDistricts = []
rs = db.query("SELECT id, name FROM  locations WHERE type_id = 3")
for r in rs:
    ourDistricts.append({'id': r['id'], 'name': r['name']})

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

myFilters = {
    'datetimeformat': datetimeformat,
    'formatmsg': formatmsg,
    'facilityLevel': facilityLevel
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