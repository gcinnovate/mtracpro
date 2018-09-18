import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class Approve:
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

        if session.role == 'District User':
            district = '%s' % session.username.capitalize()
            criteria = "district='%s'" % district
            dic = lit(
                relations='requests_view',
                fields=(
                    "id, facility, facility_name, district, msisdn, body, "
                    "raw_msg, year, week, created, report_type, is_edited, edited_raw_msg"),
                criteria=criteria + " AND status='pending'",
                order="id desc",
                limit=limit, offset=start)
        else:
            dic = lit(
                relations='requests_view',
                fields=(
                    "id, facility, facility_name, district, msisdn, body, "
                    "raw_msg, year, week, created, report_type, is_edited, edited_raw_msg"),
                criteria="status='pending'",
                order="id desc",
                limit=limit, offset=start)

        reports = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "approve", "?page=")

        l = locals()
        del l['self']
        return render.approve(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(page="1", ed="", d_id="", abtn="", reqid=[])
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.abtn == 'Approve Selected':
                if params.reqid:
                    for val in params.reqid:
                        db.update(
                            'requests', status='ready', updated='NOW()', where="id = %s" % val)
                db.transaction().commit()
                return web.seeother("/approve")
            if params.abtn == 'Cancel Selected':
                if params.reqid:
                    for val in params.reqid:
                        db.update(
                            'requests', status='canceled', updated='NOW()', where="id = %s" % val)
                db.transaction().commit()
                return web.seeother("/approve")

        l = locals()
        del l['self']
        return render.approve(**l)
