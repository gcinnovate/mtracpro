import web
from . import db, basic_auth_required
import json
from app.tools.utils import parse_pagination, fields_clause_from_param, where_clause_from_conditions

ALLOWED_FIELDS = ['id', 'msisdn', 'facility', 'created', 'body', 'district', 'status',
                  'week', 'year', 'report_type', 'source', 'destination', 'ctype', 'statuscode',
                  'errors', 'submissionid', 'month', 'raw_msg', 'edited_raw_msg', 'is_edited',
                  'facility_name', 'extras']



# create a webpy endpoint that returns searchable requests from the requests table
class RequestsAPI:
    @basic_auth_required
    def GET(self):
        user_input = web.input(
            msisdn=None, facility=None, from_date=None, to_date=None,
            body=None, district=None, status=None,
            week=None, year=None, report_type=None, page=1, page_size=50, fields=None)

        conditions = []
        params = {}

        if user_input.msisdn:
            conditions.append("msisdn LIKE $msisdn")
            params['msisdn'] = "%{}%".format(user_input.msisdn)

        if user_input.facility:
            conditions.append("facility = $facility")
            params['facility'] = user_input.facility

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

        if user_input.body:
            conditions.append("body ILIKE $body")
            params['body'] = "%{}%".format(user_input.body)

        if user_input.district:
            conditions.append("district = $district")
            params['district'] = user_input.district

        if user_input.status:
            conditions.append("status = $status")
            params['status'] = user_input.status

        if user_input.week:
            conditions.append("week::text = $week")
            params['week'] = user_input.week

        if user_input.year:
            conditions.append("year::text = $year")
            params['year'] = user_input.year

        if user_input.report_type:
            conditions.append("report_type = $report_type")
            params['report_type'] = user_input.report_type

        page, page_size, offset = parse_pagination(user_input.page, user_input.page_size)
        fields_clause = fields_clause_from_param(user_input.fields, ALLOWED_FIELDS)
        where_clause = where_clause_from_conditions(conditions)

        query = "SELECT {} FROM requests_view {} ORDER BY created DESC LIMIT {} OFFSET {};".format(
            fields_clause, where_clause, page_size, offset)
        count_query = "SELECT COUNT(*) AS count FROM requests_view {};".format(where_clause)

        total_records = db.query(count_query, vars=params)[0].count
        results = list(db.query(query, vars=params))

        for result in results:
            if 'body' in result and isinstance(result['body'], str):
                try:
                    result['body'] = json.loads(result['body'])
                except ValueError:
                    pass


        web.header('Content-Type', 'application/json')
        return json.dumps({
            'page': page,
            'page_size': page_size,
            'total_records': total_records,
            'requests': results
        }, default=str)