import requests
import json
import web
import re
import base64
import phonenumbers
import simplejson
import datetime
import psycopg2.extras
from settings import config
from settings import DELIMITER, CASES_POSITIONS, KEYWORDS_DATA_LENGTH


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    if not msisdn and len(msisdn) < 10:
        return None
    msisdn = msisdn.replace(' ', '')
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)


def lit(**keywords):
    return keywords


def get_webhook_msg_old(params, label='msg'):
    """Returns value of given lable from rapidpro webhook data"""
    values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
    msg_list = [v.get('value') for v in values if v.get('label') == label]
    if msg_list:
        msg = msg_list[0].strip()
        if msg.startswith('.'):
            msg = msg[1:]
        return msg
    return ""


def get_webhook_msg(payload, label='msg'):
    """Returns value of given lable from rapidpro webhook data"""
    results = payload.get('results', {})
    msg_list = results.get(label, {})
    if msg_list:
        msg = msg_list.get('value', '').strip()
        if msg.startswith('.'):
            msg = msg[1:]
            return msg
    return ""


def default(*args):
    p = [i for i in args if i or i == 0]
    if p.__len__():
        return p[0]
    if args.__len__():
        return args[args.__len__() - 1]
    return None


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def auth_user(db, username, password):
    sql = (
        "SELECT a.id, a.firstname, a.lastname, b.name as role "
        "FROM users a, user_roles b "
        "WHERE username = $username AND password = crypt($passwd, password) "
        "AND a.user_role = b.id AND is_active = 't'")
    res = db.query(sql, {'username': username, 'passwd': password})
    if not res:
        return False, "Wrong username or password"
    else:
        return True, res[0]


def audit_log(db, log_dict={}):
    sql = (
        "INSERT INTO audit_log (logtype, actor, action, remote_ip, detail, created_by) "
        " VALUES ($logtype, $actor, $action, $ip, $descr, $user) "
    )
    db.query(sql, log_dict)
    return None


def get_basic_auth_credentials():
    auth = web.ctx.env.get('HTTP_AUTHORIZATION')
    if not auth:
        return (None, None)
    auth = re.sub('^Basic ', '', auth)
    username, password = base64.decodestring(auth).split(':')
    return username, password


def get_location_role_reporters(db, location_id, roles=[], include_alt=True):
    """Returns a contacts list of reporters of specified roles attached to a location
    include_alt allows to add alternate telephone numbers to returned list
    """
    SQL = (
        "SELECT telephone, alternate_tel FROM reporters_view2 WHERE "
        "role IN (%s) " % ','.join(["'%s'" % i for i in roles]))
    SQL += " AND reporting_location = $location"
    res = db.query(SQL, {'location': location_id})
    ret = []
    if res:
        for r in res:
            telephone = r['telephone']
            alternate_tel = r['alternate_tel']
            if telephone:
                ret.append(format_msisdn(telephone))
            if alternate_tel and include_alt:
                ret.append(format_msisdn(alternate_tel))
    return list(set(ret))


def queue_schedule(db, params, run_time, user=None, stype='sms'):  # params has the text, recipients and other params
    res = db.query(
        "INSERT INTO schedules (params, run_time, type, created_by) "
        " VALUES($params, $runtime, $type, $user) RETURNING id",
        {
            'params': psycopg2.extras.Json(params, dumps=simplejson.dumps),
            'runtime': run_time,
            'user': user,
            'type': stype
        })
    if res:
        return res[0]['id']
    return None


def update_queued_sms(db, sched_id, params, run_time, user=None):
    db.query(
        "UPDATE schedules SET params=$params, run_time=$runtime, updated_by=$user, "
        " status='ready', updated=now() WHERE id=$id",
        {
            'params': psycopg2.extras.Json(params, dumps=simplejson.dumps),
            'runtime': run_time,
            'user': user,
            'id': sched_id
        })


def log_schedule(db, distribution_log_id, sched_id, level, triggered_by=1):
    db.query(
        "INSERT INTO distribution_log_schedules(distribution_log_id, schedule_id, level, triggered_by) "
        "VALUES($log_id, $sched_id, $level, $triggered_by)", {
            'log_id': distribution_log_id, 'sched_id': sched_id,
            'level': level, 'triggered_by': triggered_by})


def get_reporting_week(date):
    """Given date, return the reporting week in the format 2016W01
    reports coming in this week are for previous one.
    """
    offset_from_last_sunday = date.weekday() + 1
    last_sunday = date - datetime.timedelta(days=offset_from_last_sunday)
    year, weeknum, _ = last_sunday.isocalendar()
    return "%sW%d" % (year, weeknum)


def parse_message(msg, kw=""):
    msg = msg.strip().lower()
    msg = msg.replace(',', '.')
    separators = []
    segments = []
    separator = DELIMITER or '\\s'
    search_str = '[%s]+' % separator
    match = re.search(search_str, msg)
    while match:
        segment = msg[0:match.start()]
        separator = msg[match.start():match.end()]
        segments.append(segment)
        separators.append(separator)
        msg = msg[match.end():]
        match = re.search(search_str, msg)
    segments.append(msg)

    # remove empty segments
    stripped_segments = []
    for segment in segments:
        segment = segment.strip()
        if len(segment):
            stripped_segments.append(segment)

    segments = stripped_segments
    # do more cleaning here for stuff like ma2 instead of ma.2
    # get stuff like ma2, split it accordingly and put it back in right position
    outliers = filter(lambda x: not x.isalpha() and not x.isdigit(), segments)
    for i in outliers:
        idx = segments.index(i)
        match_num = re.search('[0-9]', i)
        if match_num:
            command_segment = i[0:match_num.start()]
            num_segment = i[match_num.start():match_num.end()]
            segments.insert(idx, command_segment)
            segments[idx + 1] = num_segment

    if not len(segments) % 2 == 0:
        return "not all commands have a value"
    command_value_pairs = []
    dummy_resp = ['0' for i in range(KEYWORDS_DATA_LENGTH[kw])]

    for idx, segment in enumerate(segments):
        if segment in CASES_POSITIONS:
            cmd = segment
            if (idx + 1) <= (len(segments) - 1):
                val = segments[idx + 1]
                dummy_resp[CASES_POSITIONS[segment]] = val
            else:
                # return an error
                val = 0
            command_value_pairs.append((cmd, val))
        else:
            continue
    # print segments
    return '.'.join(dummy_resp)


def post_request_to_dispatcher2(data, url=config['dispatcher2_queue_url'], ctype="xml", params={}):
    coded = base64.b64encode(
        "%s:%s" % (config['dispatcher2_username'], config['dispatcher2_password']))
    if ctype == 'xml':
        ct = 'text/xml'
    elif ctype == 'json':
        ct = 'application/json'
    else:
        ct = 'text/plain'
    response = requests.post(
        url, data=data, headers={
            'Content-Type': ct,
            'Authorization': 'Basic ' + coded},
        verify=False, params=params  # , cert=config['dispatcher2_certkey_file']
    )
    return response


def get_request(url):
    response = requests.get(url, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def queue_submission(db, serverid, post_xml, year, week):
    """Queue request and return True if successfully queued"""
    try:
        db.query(
            "INSERT INTO requests (serverid, request_body, week, year) "
            "VALUES(%s, %s, %s, %s)", (serverid, post_xml, week, year))
    except:
        return False
    return True


def queue_request(db, params):
    try:
        db.query(
            "INSERT INTO requests (source, destination, body, week, year, district, facility, "
            "msisdn, raw_msg, report_type) "
            "VALUES($source, $destination, $body, $week, $year, $district, $facility, "
            "$msisdn, $raw_msg, $report_type)", params)
    except Exception as e:
        print ">>> FAILED <<<<", str(e)
        return False
    return True


def generate_raw_message(db, form, data, add_commads=False):
    """ Returns a mTrac-like coded SMS given form and data dictionary of indicators and
    thier values """
    res = db.query(
        "SELECT slug, form_order, cmd FROM dhis2_mtrack_indicators_mapping "
        "WHERE form =  $form", {'form': form})
    values = ["0" for i in range(len(res))]
    if add_commads:
        ret = []
    indicator_order_dict = {}
    commands_dict = {}
    for r in res:
        indicator_order_dict[r['slug']] = r['form_order']
        commands_dict[r['slug']] = r['cmd']
    for k, v in data.iteritems():
        values[indicator_order_dict[k]] = v
        if add_commads:
            ret.append("%s.%s" % (commands_dict[k], v))
    if add_commads:
        return '.'.join(ret)
    return '.'.join(values)
