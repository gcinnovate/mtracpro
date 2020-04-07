import web
import json
from . import csrf_protected, db, require_login, render, get_session
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class Permissions:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="", caller="")
        edit_val = params.ed
        session = get_session()
        try:
            page = int(params.page)
        except:
            page = 1
        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        if params.ed:
            r = db.query(
                "SELECT id, name, codename, sys_module FROM permissions WHERE id = $id", {'id': params.ed})
            if r and (session.role == 'Administrator'):
                p = r[0]
                name = p.name
                codename = p.codename
                sys_module = p.sys_module

        if params.d_id:
            if session.role == 'Administrator':
                db.query("DELETE FROM user_role_permissions WHERE permission_id=$id", {'id': params.d_id})
                db.query("DELETE FROM user_permissions WHERE permission_id=$id", {'id': params.d_id})
                db.query("DELETE FROM permissions WHERE id=$id", {'id': params.d_id})
                if params.caller == "api":
                    return json.dumps({"message": "success"})

        dic = lit(
            relations='permissions',
            fields='id, name, codename, sys_module',
            criteria='',
            order='sys_module, id',
            limit=limit, offset=start)

        perms = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "permissions", "?page=")
        l = locals()
        del l['self']
        return render.permissions(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", codename="", sys_module="", page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                db.query(
                    "UPDATE permissions SET (name, codename, sys_module) = ($name, $codename, $sys_module) "
                    "WHERE id = $id",
                    {'name': params.name, 'codename': params.codename,
                        'sys_module': params.sys_module, 'id': params.ed})

                return web.seeother("/permissions")
            else:
                r = db.query(
                    "INSERT INTO permissions (name, codename, sys_module) "
                    " VALUES ($name, $codename, $sys_module) RETURNING id",
                    {'name': params.name, 'codename': params.codename, 'sys_module': params.sys_module})

                return web.seeother("/permissions")

        l = locals()
        del l['self']
        return render.permissions(**l)
