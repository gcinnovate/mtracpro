import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import audit_log
import json
from http import HTTPStatus


class AdminUnits:
    @require_login
    def GET(self):
        params = web.input(d_id="", ed="")
        session = get_session()
        districts = db.query(
            "SELECT id, name FROM locations WHERE type_id = "
            "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
        district = {}
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        if params.ed and allow_edit:
            res = db.query("SELECT name FROM locations WHERE id = $id", {'id': edit_val})
            if res:
                loc = res[0]
                location_name = loc['name']
                print(location_name)
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level > 1 ORDER BY level DESC;", {'loc': edit_val})
                if ancestors:
                    for loc in ancestors:
                        if loc['level'] == 5:
                            village = loc
                        elif loc['level'] == 4:
                            parish = loc
                            villages = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        elif loc['level'] == 3:
                            subcounty = loc
                            parishes = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        elif loc['level'] == 2:
                            district = loc
                            subcounties = db.query("SELECT id, name FROM get_children($id)", {'id': loc['id']})
                else:
                    district = edit_val
        l = locals()
        del l['self']
        return render.adminunits(**l)

    @csrf_protected
    @require_login
    def POST(self):
        session = get_session()
        params = web.input(ed="", d_id="", location_name="", parish="", location="")
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                r = db.query(
                    "UPDATE locations SET name = $name WHERE id = $id",
                    {'name': params.location_name, 'id': params.location})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Edit', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Edit Village Name (id:%s)=>%s' % (
                            params.location, params.location_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/adminunits")
            else:  # adding village
                parent = params.parish if params.parish else 0
                village_name = params.location_name
                r = db.query("SELECT add_node(1, $village_name, $parent)", {
                    'village_name': village_name, 'parent': parent})
                if r:
                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created Village(parent:%s)=>%s' % (
                            parent, village_name),
                        'user': session.sesid
                    }
                    audit_log(db, log_dict)
                return web.seeother("/adminunits")


def json_response(data, status=HTTPStatus.OK):
    #web.ctx.status = f"{status.value} {status.phrase}"
    web.header('Content-Type', 'application/json')
    return json.dumps(data)

class GetTree:
    def GET(self):
        web.header('Content-Type', 'application/json; charset=utf-8')
        params = web.input(parent_id=None)

        parent_id = params.parent_id
        if parent_id in (None, '', 'null', '#'):
            # Load root nodes
            q = """
                SELECT id, name
                FROM locations
                WHERE tree_parent_id IS NULL
                ORDER BY lft
            """
            rows = db.query(q)
        else:
            # Load children of given parent
            q = """
                SELECT id, name
                FROM locations
                WHERE tree_parent_id = $parent_id
                ORDER BY lft
            """
            rows = db.query(q, vars={'parent_id': parent_id})

        nodes = []
        for r in rows:
            # Check if this node has any children
            exists_q = """
                SELECT EXISTS (
                    SELECT 1 FROM locations WHERE tree_parent_id = $id
                ) AS has_children
            """
            exists_row = db.query(exists_q, vars={'id': r.id}).list()
            has_children = exists_row[0].has_children if exists_row else False

            nodes.append({
                'id':       r.id,
                'text':     r.name,
                'children': has_children,
            })

        return json.dumps(nodes)

class SearchTree:
    def GET(self):
        web.header('Content-Type', 'application/json; charset=utf-8')
        params = web.input(q=None)
        query = (params.q or '').strip()
        if not query:
            # missing q param  400
            web.ctx.status = '400 Bad Request'
            return json.dumps({'error': 'Missing query'})

        # run the ILIKE search
        try:
            sql = """
                SELECT id, name, path
                  FROM locations
                 WHERE name ILIKE $search
                    OR code ILIKE $search
                 LIMIT 50
            """
            rows = db.query(sql, vars={'search': '%%%s%%' % query})
        except Exception as e:
            # logging.error('searchTree query failed: %s', e)
            web.ctx.status = '500 Internal Server Error'
            return json.dumps({'error': str(e)})

        results = []
        for r in rows:
            path_str = r.path or ''
            # split "/a/b/c/" → ['a','b','c']
            codes = [p for p in path_str.strip('/').split('/') if p]
            id_path = []

            # look up each code → its numeric ID
            for code in codes:
                recs = list(db.query(
                    "SELECT id FROM locations WHERE code = $code",
                    vars={'code': code}
                ))
                if recs:
                    id_path.append(recs[0].id)

            if len(id_path) > 0:
                results.append({
                    'id':   r.id,
                    'text': r.name,
                    'path': id_path,
                })

        return json.dumps(results)


class EditNode:
    def POST(self):
        # Parse JSON body
        try:
            payload = json.loads(web.data())
        except ValueError:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # Validate required fields
        for field in ('id', 'name', 'code', 'dhis2id'):
            if field not in payload:
                return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # Perform the update
        try:
            db.query("""
                UPDATE locations
                   SET name    = $name,
                       code    = $code,
                       dhis2id = $dhis2id
                 WHERE id      = $id
            """, vars={
                'name':    payload['name'],
                'code':    payload['code'],
                'dhis2id': payload['dhis2id'],
                'id':      int(payload['id']),
            })
        except Exception as e:
            return json_response({'error': 'update failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # Return 200 OK with empty body
        web.ctx.status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        web.header('Content-Type', 'application/json')
        return ''


class GetNodeDetails:
    def GET(self):
        params = web.input(id=None)
        node_id = params.id

        if not node_id:
            return json_response({'error': 'Missing id'}, status=HTTPStatus.BAD_REQUEST)

        query = """
            SELECT l.id,
                   l.name,
                   l.code,
                   l.dhis2id,
                   COALESCE(l.path, '') AS path,
                   l.level,
                   COALESCE(p.name, '') AS parent_name
              FROM locations l
              LEFT JOIN locations p
                     ON l.tree_parent_id = p.id
             WHERE l.id = $id
        """

        # Execute the query
        try:
            rows = list(db.query(query, vars={'id': node_id}))
        except Exception as e:
            return json_response({'error': 'query failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # If we got a row, unpack and respond
        if rows:
            r = rows[0]
            return json_response({
                'id':          r.id,
                'name':        r.name,
                'code':        r.code,
                'dhis2id':     r.dhis2id,
                'path':        r.path,
                'level':       r.level,
                'parent_name': r.parent_name,
            }, status=HTTPStatus.OK)

        # No rows → 404
        return json_response({'error': 'node not found'}, status=HTTPStatus.NOT_FOUND)


class EditNode:
    def POST(self):
        # 1. Parse JSON body
        try:
            payload = json.loads(web.data())
        except ValueError:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # 2. Validate required fields
        for field in ('id', 'name', 'code', 'dhis2id'):
            if field not in payload:
                return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # 3. Perform the update
        try:
            db.query(
                """
                UPDATE locations
                   SET name    = $name,
                       code    = $code,
                       dhis2id = $dhis2id
                 WHERE id      = $id
                """,
                vars={
                    'name':    payload['name'],
                    'code':    payload['code'],
                    'dhis2id': payload['dhis2id'],
                    'id':      int(payload['id']),
                }
            )
        except Exception as e:
            return json_response({'error': 'update failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # 4. Success → 200 OK with empty JSON body
        web.ctx.status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        web.header('Content-Type', 'application/json')
        return ''


class RefreshHierarchy:
    def POST(self):
        try:
            db.query("SELECT refresh_hierarchy();")
        except Exception as e:
            return json_response({'error': 'refresh failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        web.ctx.status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        web.header('Content-Type', 'application/json')
        return ''


class MoveNode:
    def POST(self):
        try:
            payload = json.loads(web.data())
        except ValueError:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # 2. Validate required fields
        if 'id' not in payload or 'parent' not in payload:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        node_id = int(payload['id'])
        parent_id = payload['parent']  # can be None

        # 3. Perform updates
        try:
            # Update the tree parent
            db.query(
                "UPDATE locations SET tree_parent_id = $parent WHERE id = $id",
                vars={'parent': parent_id, 'id': node_id}
            )
            # Recalculate the MPTT structure
            db.query("SELECT refresh_hierarchy()")
        except Exception as e:
            return json_response({'error': 'move failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # 4. Success → 200 OK, empty body
        web.ctx.status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        web.header('Content-Type', 'application/json')
        return ''


class DeleteNode:
    def POST(self):
        # 1. Parse JSON body
        try:
            payload = json.loads(web.data())
        except ValueError:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # 2. Validate required field
        if 'id' not in payload:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        node_id = int(payload['id'])

        # 3. Perform deletion and re-calc
        try:
            db.query(
                "DELETE FROM locations WHERE id = $id",
                vars={'id': node_id}
            )
            db.query("SELECT refresh_hierarchy();")
        except Exception as e:
            return json_response({'error': 'delete failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # 4. Success → 200 OK, empty body
        web.ctx.status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        web.header('Content-Type', 'application/json')
        return ''


class CreateNode:
    def POST(self):
        # 1. Parse JSON body
        try:
            payload = json.loads(web.data())
        except ValueError:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        # 2. Validate required fields
        if 'text' not in payload or 'parent' not in payload:
            return json_response({'error': 'invalid input'}, status=HTTPStatus.BAD_REQUEST)

        text = payload['text']
        parent = payload['parent']  # can be None

        # 3. Insert new node and recalculate MPTT
        try:
            # Run INSERT ... RETURNING id
            rows = list(db.query(
                """
                INSERT INTO locations(name, tree_parent_id)
                VALUES ($text, $parent)
                RETURNING id
                """,
                vars={'text': text, 'parent': parent}
            ))
            new_id = rows[0].id if rows else None
            if new_id is None:
                raise Exception("no id returned")

            # Recalculate the MPTT hierarchy
            db.query("SELECT refresh_hierarchy();")
        except Exception as e:
            return json_response({'error': 'create failed'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # 4. Return the newly created ID
        return json_response({'id': new_id}, status=HTTPStatus.OK)

