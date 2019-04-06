import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class Polls:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="", search="")
        edit_val = params.ed
        session = get_session()
        if session.role == 'District User':
            districts_SQL = (
                "SELECT id, name FROM locations WHERE id = "
                "ANY('%s'::INT[]) ORDER BY name" % session.districts_array)
        else:
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")

        districts_1 = db.query(districts_SQL)
        districts_2 = db.query(districts_SQL)
        district = {}
        groups_2 = db.query("SELECT id, name FROM reporter_groups")

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
            r = db.query(
                "SELECT id, name, type, question, default_response, start_date "
                "FROM polls WHERE id=$id", {'id': params.ed})
            if r:
                p = r[0]
                name = p.name
                poll_type = p.type
                question = p.question
                default_response = p.default_response
                start_date = p.start_date
                if not start_date:
                    pass
                    return
                group_ids = []
                rx = db.query(
                    "SELECT id FROM reporter_groups WHERE id IN "
                    "(select unnest(groups) from polls where id = $id)", {'id': params.ed})
                for g in rx:
                    group_ids.append(g['id'])
                district_ids = []
                rx = db.query(
                    "SELECT id FROM locations WHERE id IN "
                    "(select unnest(districts) from polls where id = $id)", {'id': params.ed})
                for d in rx:
                    district_ids.append(d['id'])

        allow_del = False
        try:
            del_val = int(params.d_id)
            allow_del = True
        except ValueError:
            pass
        if params.d_id and allow_del:
            if session.role == 'Administrator':
                db.query("DELETE FROM polls WHERE id=$id", {'id': params.d_id})

        if session.role == 'District User':
            criteria = "user_id = %s " % session.sesid
            if params.search:
                criteria += (
                    " AND name ilike '%%%%%s%%%%' ")
                dic = lit(
                    relations='polls',
                    fields="id, name, question, start_date, end_date",
                    criteria=criteria,
                    order="id desc",
                    limit=limit, offset=start)
            else:
                dic = lit(
                    relations="polls",
                    fields="id, name, question, start_date, end_date",
                    criteria=criteria,
                    order="id desc",
                    limit=limit, offset=start)
        else:
            criteria = "TRUE "
            if params.search:
                criteria += (
                    " AND name ilike '%%%%%s%%%%' ")
                dic = lit(
                    relations='polls',
                    fields="id, name, question, start_date, end_date",
                    criteria=criteria,
                    order="id desc",
                    limit=limit, offset=start)
            else:
                dic = lit(
                    relations="polls",
                    fields="id, name, question, start_date, end_date",
                    criteria=criteria,
                    order="id desc",
                    limit=limit, offset=start)

        polls = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "polling", "?page=")
        l = locals()
        del l['self']
        return render.polls(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", question="", poll_type="", default_response="", groups=[],
            districts=[], start_now="", page="1", ed="", d_id="")
        session = get_session()
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                db.query("SELECT 1")
                return web.seeother("/polling")
            else:
                rx = db.query(
                    "INSERT INTO polls (name, user_id, type, question, default_response, "
                    "groups, districts) VALUES($name, $user, $type, $question, $default_response,"
                    "$groups, $districts) RETURNING id", {
                        'name': params.name, 'user': session.sesid, 'type': params.poll_type,
                        'question': params.question, 'default_response': params.default_response,
                        'groups': str([int(x) for x in params.groups]).replace(
                            '[', '{').replace(']', '}').replace('\'', '\"'),
                        'districts': str([int(x) for x in params.districts]).replace(
                            '[', '{').replace(']', '}').replace('\'', '\"')})

                return web.seeother("/polling")

        l = locals()
        del l['self']
        return render.polls(**l)
