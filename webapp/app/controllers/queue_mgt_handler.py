import web
from . import db, require_login, get_session, render
from webapp.app.tools.pagination2 import doquery, countquery, getPaginationString
from webapp.app.tools.utils import default, lit
from webapp.settings import PAGE_LIMIT



class QueueManagement:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed

        session = get_session()
        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        dic = lit(relations='servers', fields="*", criteria="", order="id desc", limit=limit, offset=start)
        servers = doquery(db, dic)
        servers2 = doquery(db, dic)

        report_types = db.query(
            "SELECT distinct(form) AS form FROM dhis2_mtrack_indicators_mapping ORDER BY form")
        dic = lit(
            relations='requests_view', fields="*",
            criteria=session.criteria,
            order="id desc",
            limit=limit, offset=start)
        res = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "management", "?page=")
        l = locals()
        del l['self']
        return render.management(**l)

    # @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", descr="", page="1", ed="", d_id="")
        try:
            page = int(params.page)
        except:
            page = 1
        session = get_session()

        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        dic = lit(relations='servers', fields="*", criteria="", order="id desc", limit=limit, offset=start)
        servers = doquery(db, dic)
        servers2 = doquery(db, dic)

        criteria = "TRUE "
        if params.submissionid:
            criteria += " AND submissionid = %s" % params.submissionid
        if params.status:
            criteria += " AND status = '%s' " % params.status
        if params.sdate:
            criteria += " AND created >= '%s'" % params.sdate
        if params.edate:
            criteria += " AND created <= '%s'" % params.edate
        if params.week:
            criteria += " AND week = '%s'" % params.week
        if params.body:
            criteria += " AND body ILIKE '%%%%%s%%%%'" % params.body
        if params.year:
            criteria += " AND year = '%s'" % params.year
        if params.msisdn:
            criteria += " AND msisdn LIKE '%%%%%s%%%%'" % params.msisdn
        if params.facility:
            criteria += " AND facility = '%s'" % params.facility
        if params.report_type:
            criteria += " AND report_type = '%s'" % params.report_type
        if params.formatting:
            if params.formatting == "xml":
                criteria += " AND xml_is_well_formed_document(body)"

        print(criteria)
        if len(criteria) > 5:
            session.criteria = criteria
        dic = lit(
            relations='requests_view', fields="*",
            criteria=criteria,
            order="id desc",
            limit=limit, offset=start)
        res = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "search", "?page=")

        with db.transaction():
            if params.abtn == 'Retry Selected':
                if params.reqid:
                    for val in params.reqid:
                        db.update('requests', where="id = %s" % val, status='ready')
            if params.abtn == 'Cancel Selected':
                if params.reqid:
                    for val in params.reqid:
                        db.update('requests', where="id = %s" % val, status='canceled')
            if params.abtn  == 'Replay Filtered':
                db.doquery("UPDATE requests SET status = 'ready' WHERE %s" % criteria)

            db.transaction().commit()

        l = locals()
        del l['self']
        return render.management(**l)
