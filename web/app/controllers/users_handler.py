import web
from . import csrf_protected, db, get_session, require_login, render, userRolesByName
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class Users:
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
                "SELECT a.id, a.firstname, a.lastname, a.username, a.email, a.telephone, "
                "a.is_active, a.districts, b.id as role, b.name role_name "
                "FROM users a, user_roles b "
                "WHERE a.id = $id AND a.user_role = b.id", {'id': params.ed})
            if r and (session.role == 'Administrator' or '%s' % session.sesid == edit_val):
                u = r[0]
                firstname = u.firstname
                lastname = u.lastname
                telephone = u.telephone
                email = u.email
                username = u.username
                user_role = u.role
                role_name = u.role_name
                is_active = u.is_active
                is_super = True if u.role == 'Administrator' else False
                district_ids = []
                rx = db.query(
                    "SELECT id FROM locations WHERE id IN "
                    "(select unnest(districts) from users where id = $id)", {'id': params.ed})
                for d in rx:
                    district_ids.append(d['id'])

                permission_ids = []
                rx = db.query(
                    "SELECT permission_id AS id FROM user_permissions WHERE user_id = $user_id ",
                    {'user_id': params.ed})
                for p in rx:
                    permission_ids.append(p['id'])

        if params.d_id:
            if session.role == 'Administrator':
                db.query("DELETE FROM users WHERE id=$id", {'id': params.d_id})

        roles = db.query("SELECT id, name FROM user_roles ORDER by name")
        current_role_id = userRolesByName[session.role]
        criteria = ""
        if session.role == 'Administrator':
            dic = lit(
                relations='users a, user_roles b',
                fields="a.id, a.firstname, a.lastname, a.username, a.email, a.telephone, b.name as role ",
                criteria="a.user_role = b.id",
                order="a.firstname, a.lastname",
                limit=limit, offset=start)
        else:
            dic = lit(
                relations='users a, user_roles b',
                fields="a.id, a.firstname, a.lastname, a.username, a.email, a.telephone, b.name as role ",
                criteria="a.user_role = b.id AND a.id=%s" % session.sesid,
                order="a.firstname, a.lastname",
                limit=limit, offset=start)

        users = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "users", "?page=")
        l = locals()
        del l['self']
        return render.users(**l)

    @csrf_protected
    def POST(self):
        params = web.input(
            firstname="", lastname="", telephone="", username="", email="", passwd="", districts=[],
            cpasswd="", is_active="", is_super="", page="1", ed="", d_id="", user_role="", permissions=[])
        try:
            page = int(params.page)
        except:
            page = 1
        is_active = 't' if params.is_active == "on" else 'f'
        # role = 'Administrator' if params.is_super == "on" else 'Basic'
        with db.transaction():
            if params.ed:
                db.query(
                    "UPDATE users SET firstname=$firstname, lastname=$lastname, "
                    "telephone=$telephone, email=$email, username=$username, "
                    "password = crypt($cpasswd, gen_salt('bf')), "
                    "is_active=$is_active, "
                    "user_role=$role, districts=$districts "
                    "WHERE id = $id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'username': params.username, 'cpasswd': params.cpasswd,
                        'role': params.user_role, 'is_active': is_active, 'id': params.ed,
                        'districts': str([int(x) for x in params.districts]).replace(
                            '[', '{').replace(']', '}').replace('\'', '\"')
                    }
                )

                newPermissions = [int(x) for x in params.permissions]
                previousPermissions = []
                rx = db.query(
                    "SELECT permission_id FROM user_permissions WHERE user_id = $user_id",
                    {'user_id': params.ed})
                for p in rx:
                    previousPermissions.append(p['permission_id'])

                for perm in newPermissions:
                    if perm in previousPermissions:
                        continue
                    else:
                        db.query(
                            "INSERT INTO user_permissions (user_id, permission_id) "
                            "VALUES($user_id, $permission_id)",
                            {'user_id': params.ed, 'permission_id': perm})
                for perm in previousPermissions:
                    if perm not in newPermissions:
                        db.query(
                            "DELETE FROM user_permissions WHERE "
                            "user_id=$user_id AND permission_id = $permission_id",
                            {'user_id': params.ed, 'permission_id': perm})
                return web.seeother("/users")
            else:
                r = db.query(
                    "INSERT INTO users (firstname, lastname, telephone, email, "
                    "username, password, is_active, user_role, districts) "
                    "VALUES($firstname, $lastname, $telephone, $email, $username, "
                    "crypt($cpasswd, gen_salt('bf')), $is_active, "
                    "$role, $districts) RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'telephone': params.telephone, 'email': params.email,
                        'username': params.username, 'cpasswd': params.cpasswd,
                        'role': params.user_role, 'is_active': is_active, 'id': params.ed,
                        'districts': str([int(x) for x in params.districts]).replace(
                            '[', '{').replace(']', '}').replace('\'', '\"')
                    }
                )
                newPermissions = [int(x) for x in params.permissions]
                if r:
                    newUser = r[0]
                    for perm in newPermissions:
                        db.query(
                            "INSERT INTO user_permissions (user_id, permission_id) "
                            "VALUES($user_id, $permission_id)",
                            {'user_id': newUser.id, 'permission_id': perm})
                return web.seeother("/users")
        l = locals()
        del l['self']
        return render.users(**l)
