import web
from . import csrf_protected, db, require_login, render, get_session
from webapp.app.tools.pagination2 import doquery, countquery, getPaginationString
from webapp.app.tools.utils import default, lit
from webapp.settings import PAGE_LIMIT


class Groups:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
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
                "SELECT id, name, descr FROM user_roles WHERE id = $id", {'id': params.ed})
            if r and (session.role == 'Administrator'):
                g = r[0]
                name = g.name
                description = g.descr

                permission_ids = []
                rx = db.query(
                    "SELECT permission_id AS id FROM user_role_permissions WHERE user_role = $user_role ",
                    {'user_role': params.ed})
                for p in rx:
                    permission_ids.append(p['id'])

        if params.d_id:
            if session.role == 'Administrator':
                pass
                # db.query("DELETE FROM user_role_permissions WHERE user_role=$id", {'id': params.d_id})
                # db.query("DELETE FROM user_roles WHERE id=$id", {'id': params.d_id})

        dic = lit(
            relations='user_roles',
            fields='id, name, descr',
            criteria='',
            order='name',
            limit=limit, offset=start)

        groups = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "groups", "?page=")
        l = locals()
        del l['self']
        return render.groups(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", descr="", page="1", ed="", d_id="", permissions=[])
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                db.query(
                    "UPDATE user_roles SET (name, descr) = ($name, $descr) "
                    "WHERE id = $id", {'name': params.name, 'descr': params.descr, 'id': params.ed})
                newPermissions = [int(x) for x in params.permissions]
                previousPermissions = []
                rx = db.query(
                    "SELECT permission_id FROM user_role_permissions WHERE user_role = $user_role",
                    {'user_role': params.ed})
                for p in rx:
                    previousPermissions.append(p['permission_id'])

                for perm in newPermissions:
                    if perm in previousPermissions:
                        continue
                    else:
                        db.query(
                            "INSERT INTO user_role_permissions (user_role, permission_id) "
                            "VALUES($user_role, $permission_id)",
                            {'user_role': params.ed, 'permission_id': perm})
                for perm in previousPermissions:
                    if perm not in newPermissions:
                        db.query(
                            "DELETE FROM user_role_permissions WHERE "
                            "user_role=$user_role AND permission_id = $permission_id",
                            {'user_role': params.ed, 'permission_id': perm})

                return web.seeother("/groups")
            else:
                r = db.query(
                    "INSERT INTO user_roles (name, descr) "
                    " VALUES ($name, $descr) RETURNING id",
                    {'name': params.name, 'descr': params.descr})
                newPermissions = [int(x) for x in params.permissions]
                if r:
                    newGroup = r[0]
                    for perm in newPermissions:
                        db.query(
                            "INSERT INTO user_role_permissions (user_role, permission_id) "
                            "VALUES($user_role, $permission_id)",
                            {'user_role': newGroup.id, 'permission_id': perm})
                return web.seeother("/groups")

        l = locals()
        del l['self']
        return render.groups(**l)
