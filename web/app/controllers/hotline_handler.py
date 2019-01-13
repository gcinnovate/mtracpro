
import web
from . import csrf_protected, db, require_login, render, get_session, allDistrictsByName
from app.tools.utils import audit_log, default, lit
from app.tools.pagination2 import doquery, countquery, getPaginationString
from settings import PAGE_LIMIT


class Hotline:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")

        try:
            page = int(params.page)
        except:
            page = 1
        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        session = get_session()
        if session.role == 'District User':
            district_id = allDistrictsByName['%s' % session.username.capitalize()]
            criteria = "districtid = %s" % district_id
            dic = lit(
                relations="anonymousreports_view",
                fields=(
                    "id, facility, district, created, report, action, topic, "
                    "action_taken, action_center, comment"),
                criteria=criteria,
                order="id desc",
                limit=limit, offset=start)
        else:
            criteria = ""
            dic = lit(
                relations="anonymousreports_view",
                fields=(
                    "id, facility, district, created, report, action, topic, "
                    "action_taken, action_center, comment"),
                criteria=criteria,
                order="id desc",
                limit=limit, offset=start)

        anonymous_reports = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "hotline", "?page=")
        l = locals()
        del l['self']
        return render.hotline(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", descr="", page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.ed:
                return web.seeother("/hotline")
            else:
                return web.seeother("/hotline")

        l = locals()
        del l['self']
        return render.hotline(**l)
