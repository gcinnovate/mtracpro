import web
from . import db, basic_auth_required
import json
from app.tools.utils import parse_pagination, fields_clause_from_param, where_clause_from_conditions


ALLOWED_SERVER_FIELDS = [
    'id', 'name', 'username', 'ipaddress', 'url', 'auth_method', 'use_ssl',
    'ssl_client_certkey_file', 'start_submission_period', 'end_submission_period',
    'xml_response_xpath', 'json_response_jsonpath', 'created', 'updated',
    'http_method', 'parse_responses', 'suspended', 'json_response_xpath',
    'auth_token', 'allowed_sources'
]


class ServersAPI:
    @basic_auth_required
    def GET(self):
        user_input = web.input(
            id=None, name=None, ipaddress=None, auth_method=None,
            http_method=None, suspended=None, from_date=None, to_date=None,
            updated_from=None, updated_to=None, page=1, page_size=50, fields=None)

        conditions = []
        params = {}

        if user_input.id:
            conditions.append("id = $id")
            params['id'] = user_input.id

        if user_input.name:
            conditions.append("name ILIKE $name")
            params['name'] = "%{}%".format(user_input.name)

        if user_input.ipaddress:
            conditions.append("ipaddress = $ipaddress")
            params['ipaddress'] = user_input.ipaddress

        if user_input.auth_method:
            conditions.append("auth_method = $auth_method")
            params['auth_method'] = user_input.auth_method

        if user_input.http_method:
            conditions.append("http_method = $http_method")
            params['http_method'] = user_input.http_method

        if user_input.suspended is not None:
            # accept 't'/'f', 'true'/'false', '1'/'0'
            val = str(user_input.suspended).lower() in ('t', 'true', '1')
            conditions.append("suspended = $suspended")
            params['suspended'] = val

        # created range
        if user_input.from_date and user_input.to_date:
            conditions.append("DATE(created) BETWEEN $from_date AND $to_date")
            params['from_date'] = user_input.from_date
            params['to_date'] = user_input.to_date
        elif user_input.from_date:
            conditions.append("DATE(created) >= $from_date")
            params['from_date'] = user_input.from_date
        elif user_input.to_date:
            conditions.append("DATE(created) <= $to_date")
            params['to_date'] = user_input.to_date

        # updated range
        if user_input.updated_from and user_input.updated_to:
            conditions.append("DATE(updated) BETWEEN $updated_from AND $updated_to")
            params['updated_from'] = user_input.updated_from
            params['updated_to'] = user_input.updated_to
        elif user_input.updated_from:
            conditions.append("DATE(updated) >= $updated_from")
            params['updated_from'] = user_input.updated_from
        elif user_input.updated_to:
            conditions.append("DATE(updated) <= $updated_to")
            params['updated_to'] = user_input.updated_to

        page, page_size, offset = parse_pagination(user_input.page, user_input.page_size)
        fields_clause = fields_clause_from_param(user_input.fields, ALLOWED_SERVER_FIELDS)
        where_clause = where_clause_from_conditions(conditions)

        query = "SELECT {} FROM servers {} ORDER BY created DESC LIMIT {} OFFSET {};".format(
            fields_clause, where_clause, page_size, offset)
        count_query = "SELECT COUNT(*) AS count FROM servers {};".format(where_clause)

        total_records = db.query(count_query, vars=params)[0].count
        results = list(db.query(query, vars=params))

        web.header('Content-Type', 'application/json')
        return json.dumps({
            'page': page,
            'page_size': page_size,
            'total_records': total_records,
            'servers': results
        }, default=str)


class ServerSuspend:
    @basic_auth_required
    def POST(self, server_id):
        try:
            sid = int(server_id)
        except ValueError:
            web.ctx.status = '400 Bad Request'
            return json.dumps({'error': 'Invalid server id'})

        existing = list(db.select('servers', where='id=$id', vars={'id': sid}))
        if not existing:
            web.ctx.status = '404 Not Found'
            return json.dumps({'error': 'Server not found'})

        # If already suspended, just return success
        if existing[0].suspended:
            return json.dumps({'id': sid, 'suspended': True, 'message': 'Already suspended'})

        db.update('servers', where='id=$id', vars={'id': sid}, suspended=True)
        return json.dumps({'id': sid, 'suspended': True})


class ServerResume:
    @basic_auth_required
    def POST(self, server_id):
        try:
            sid = int(server_id)
        except ValueError:
            web.ctx.status = '400 Bad Request'
            return json.dumps({'error': 'Invalid server id'})

        existing = list(db.select('servers', where='id=$id', vars={'id': sid}))
        if not existing:
            web.ctx.status = '404 Not Found'
            return json.dumps({'error': 'Server not found'})

        if not existing[0].suspended:
            return json.dumps({'id': sid, 'suspended': False, 'message': 'Already active'})

        db.update('servers', where='id=$id', vars={'id': sid}, suspended=False)
        return json.dumps({'id': sid, 'suspended': False})