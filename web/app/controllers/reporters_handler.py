import web
import json
from . import csrf_protected, db, require_login, get_session, render, allDistrictsByName
from app.tools.utils import audit_log, default, lit
from app.tools.pagination2 import doquery, countquery, getPaginationString
from settings import PAGE_LIMIT


class Reporters:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="", caller="web", search="")
        edit_val = params.ed
        session = get_session()
        if session.role == 'District User':
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') "
                "AND name = '%s'" % session.username.capitalize())
        else:
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")

        districts = db.query(districts_SQL)
        district = {}
        roles = db.query("SELECT id, name from reporter_groups order by name")
        allow_edit = False

        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        try:
            page = int(params.page)
        except:
            page = 1
        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        if params.ed and allow_edit:
            res = db.query(
                "SELECT id, firstname, lastname, telephone, email, "
                "reporting_location, role, alternate_tel, facilityid, facility "
                "FROM reporters_view "
                " WHERE id = $id", {'id': edit_val})
            if res:
                r = res[0]
                firstname = r.firstname
                lastname = r.lastname
                telephone = r.telephone
                email = r.email
                role = r.role.split(',')
                alt_telephone = r.alternate_tel
                location = r.reporting_location
                subcounty = ""
                facilityid = r.facilityid
                district = ""
                subcounties = []
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level > 1 ORDER BY level DESC;", {'loc': location})
                if ancestors:
                    for loc in ancestors:
                        if loc['level'] == 3:
                            subcounty = loc
                        elif loc['level'] == 2:
                            district = loc
                            subcounties = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                else:
                    district = location
                facilities = db.query(
                    "SELECT id, name FROM healthfacilities WHERE location=$loc", {'loc': location})
                if facilityid:
                    fres = db.query(
                        "SELECT id, name FROM healthfacilities WHERE id = $id", {'id': facilityid})
                    facility = fres[0]

        allow_del = False
        try:
            del_val = int(params.d_id)
            allow_del = True
        except ValueError:
            pass
        if params.d_id and allow_del:
            if session.role in ('District User', 'Administrator'):
                reporter = db.query(
                    "SELECT firstname || ' ' || lastname as name , telephone "
                    "FROM reporters WHERE id = $id", {'id': params.d_id})
                if reporter:
                    rx = reporter[0]
                    log_dict = {
                        'logtype': 'Web', 'action': 'Delete', 'actor': session.username,
                        'ip': web.ctx['ip'], 'descr': 'Deleted reporter %s:%s (%s)' % (
                            params.d_id, rx['name'], rx['telephone']),
                        'user': session.sesid
                    }
                    db.query("DELETE FROM reporter_groups_reporters WHERE reporter_id=$id", {'id': params.d_id})
                    db.query("DELETE FROM reporter_healthfacility WHERE reporter_id=$id", {'id': params.d_id})
                    db.query("DELETE FROM reporters WHERE id=$id", {'id': params.d_id})
                    audit_log(db, log_dict)
                    if params.caller == "api":  # return json if API call
                        web.header("Content-Type", "application/json; charset=utf-8")
                        return json.dumps({'message': "success"})

        if session.role == 'District User':
            district_id = allDistrictsByName['%s' % session.username.capitalize()]
            criteria = "district_id=%s" % district_id
            if params.search:
                criteria += (
                    " AND (telephone ilike '%%%s%%' OR "
                    "firstname ilike '%%%s%%' OR lastname ilike '%%%s%%')")
                criteria = criteria % (params.search, params.search, params.search)
                dic = lit(
                    relations='reporters_view',
                    fields=(
                        "id, firstname, lastname, telephone, district_id, "
                        "facility, role, total_reports, last_reporting_date, uuid "),
                    criteria=criteria,
                    order="facility, firstname, lastname",
                    limit=limit, offset=start)
            else:
                dic = lit(
                    relations='reporters_view',
                    fields=(
                        "id, firstname, lastname, telephone, district_id, "
                        "facility, role, total_reports, last_reporting_date, uuid "),
                    criteria=criteria,
                    order="",
                    limit=limit, offset=start)
        else:
            criteria = "TRUE "
            if params.search:
                criteria += (
                    " AND (telephone ilike '%%%(search)s%%' OR "
                    "firstname ilike '%%%(search)s%%' OR lastname ilike '%%%(search)s%%')")
                dic = lit(
                    relations='reporters_view',
                    fields=(
                        "id, firstname, lastname, telephone, district_id, "
                        "facility, role, total_reports, last_reporting_date, uuid"),
                    criteria=criteria % {'search': params.search},
                    order="facility, firstname, lastname",
                    limit=limit, offset=start)
            else:
                criteria = "id >  (SELECT max(id) - 250 FROM reporters)"
                dic = lit(
                    relations='reporters_view',
                    fields=(
                        "id, firstname, lastname, telephone, district_id, "
                        "facility, role, total_reports, last_reporting_date, uuid "),
                    criteria=criteria,
                    order="facility, firstname, lastname",
                    limit=limit, offset=start)

        reporters = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "reporters", "?page=")
        l = locals()
        del l['self']
        return render.reporters(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(
            firstname="", lastname="", telephone="", email="", location="",
            role=[], alt_telephone="", page="1", ed="", d_id="", district="")

        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                location = params.location if params.location else None
                r = db.query(
                    "UPDATE reporters SET firstname=$firstname, lastname=$lastname, "
                    "telephone=$telephone, email=$email, reporting_location=$location, "
                    "alternate_tel=$alt_tel, district_id = $district_id "
                    "WHERE id=$id RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'location': location, 'id': params.ed, 'alt_tel': params.alt_telephone,
                        'district_id': params.district
                    })
                if r:
                    for group_id in params.role:
                        rx = db.query(
                            "SELECT id FROM reporter_groups_reporters "
                            "WHERE reporter_id = $id AND group_id =$gid ",
                            {'gid': group_id, 'id': params.ed})
                        if not rx:
                            db.query(
                                "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                                " VALUES ($group_id, $reporter_id)",
                                {'group_id': group_id, 'reporter_id': params.ed})
                    # delete other groups
                    db.query(
                        "DELETE FROM reporter_groups_reporters WHERE "
                        "reporter_id=$id AND group_id NOT IN $roles",
                        {'id': params.ed, 'roles': params.role})
                    log_dict = {
                        'logtype': 'Web', 'action': 'Update', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated reporter %s:%s (%s)' % (
                            params.ed, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/reporters")
            else:
                location = params.location if params.location else None
                has_reporter = db.query(
                    "SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.telephone})
                if has_reporter:
                    session.rdata_err = (
                        "Reporter with Telephone:%s already registered" % params.telephone
                    )
                    return web.seeother("/reporters")
                session.rdata_err = ""
                r = db.query(
                    "INSERT INTO reporters (firstname, lastname, telephone, email, "
                    " reporting_location, alternate_tel, "
                    " district_id) VALUES "
                    " ($firstname, $lastname, $telephone, $email, $location, "
                    " $alt_tel, $district_id) RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'location': location, 'alt_tel': params.alt_telephone,
                        'district_id': params.district
                    })
                if r:
                    reporter_id = r[0]['id']
                    for group_id in params.role:
                        db.query(
                            "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                            " VALUES ($role, $reporter_id)",
                            {'role': group_id, 'reporter_id': reporter_id})

                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created reporter %s:%s (%s)' % (
                            reporter_id, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/reporters")

        l = locals()
        del l['self']
        return render.reporters(**l)
