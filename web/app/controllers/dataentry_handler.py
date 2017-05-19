import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import get_reporting_week
import datetime


class DataEntry:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
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
        rweek = get_reporting_week(datetime.datetime.now())
        year, week = rweek.split('W')
        reporting_weeks = []
        for i in range(1, int(week)):
            reporting_weeks.append("%sW%s" % (year, i))

        l = locals()
        del l['self']
        return render.dataentry(**l)

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
                return web.seeother("/dataentry")
            else:
                return web.seeother("/dataentry")

        l = locals()
        del l['self']
        return render.dataentry(**l)
