import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class Facilities:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="", search="", subcounty="")
        edit_val = params.ed
        session = get_session()
        try:
            page = int(params.page)
        except:
            page = 1

        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0
        if session.role == 'District User':
            districts_SQL = (
                "SELECT id, name FROM locations WHERE id = "
                "ANY('%s'::INT[]) ORDER BY name" % session.districts_array)
            # criteria = "district='%s'" % session.username.capitalize()
            criteria = "is_active = 't' AND district_id = ANY('%s'::INT[]) " % session.districts_array
            if params.search:
                criteria += (" AND name ilike '%%%%%s%%%%' " % params.search )

            if params.subcounty:
                criteria += ( " AND location = %s " % params.subcounty)

        else:
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
            criteria = " is_active = 't' "

            if params.search:
                criteria += (" AND name ilike '%%%%%s%%%%' " % params.search )

            if params.subcounty:
                criteria += ( " AND location = %s " % params.subcounty)

        dic = lit(
            relations='healthfacilities', fields="id, name, type_id, district, location_name, is_033b, code, last_reporting_date",
            criteria=criteria,
            order="district, name asc",
            limit=limit, offset=start)
        facilities = doquery(db, dic)
        facilitiesx = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "facilities", "?page=")

        districts_1 = db.query(districts_SQL)
        districts_2 = db.query(districts_SQL)
        district = {}

        l = locals()
        del l['self']
        return render.facilities(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                return web.seeother("/facilities")
            else:
                return web.seeother("/facilities")

        l = locals()
        del l['self']
        return render.facilities(**l)
