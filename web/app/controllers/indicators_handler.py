import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.utils import audit_log, default, lit
from app.tools.pagination2 import doquery, countquery, getPaginationString
from settings import PAGE_LIMIT


class Indicators:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        allow_edit = False

        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        try:
            page = int(params.page)
        except:
            page = 1
        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        if params.ed and allow_edit:
            res = db.query(
                "SELECT id, description, slug, cmd, form, form_order, dataset, dataelement, "
                "category_combo, threshold FROM dhis2_mtrack_indicators_mapping WHERE id = $id",
                {'id': edit_val})
            if res:
                r = res[0]
                name = r.description
                slug = r.slug
                cmd = r.cmd
                form = r.form
                form_order = r.form_order
                dataset = r.dataset
                dataelement = r.dataelement
                category_combo = r.category_combo
                threshold = r.threshold

        dic = lit(
            relations="dhis2_mtrack_indicators_mapping",
            fields=(
                "id, description, slug, form, form_order, cmd, dataset, "
                "dataelement, category_combo "),
            criteria="",
            order="dataset, form, form_order",
            limit=limit, offset=start
        )
        mappings = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "indicators", "?page=")

        l = locals()
        del l['self']
        return render.indicators(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            name="", form="", form_order="", slug="", cmd="",
            dataset="", dataelement="", category_combo="", threshold="", page="1", ed="", d_id="")

        session = get_session()
        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass

        with db.transaction():
            if params.ed and allow_edit:
                r = db.query(
                    "UPDATE dhis2_mtrack_indicators_mapping SET "
                    "(description, form, form_order, slug, cmd, dataset, dataelement, category_combo, threshold) "
                    "= ($descr, $form, $form_order, $slug, $cmd, $dataset, $dataelement, $category_combo, $threshold) "
                    "WHERE id = $id", {
                        'descr': params.name, 'form': params.form,
                        'form_order': params.form_order, 'slug': params.slug,
                        'cmd': params.cmd, 'dataset': params.dataset, 'threshold': params.threshold,
                        'dataelement': params.dataelement, 'category_combo': params.category_combo,
                        'id': params.ed}
                )
                log_dict = {
                    'logtype': 'Web', 'action': 'Update', 'actor': session.username,
                    'ip': web.ctx['ip'],
                    'descr': 'Updated Indicator Mapping. id:%s =>  Dataset %s: Form:%s Cmd:%s)' % (
                        params.ed, params.dataset, params.form, params.cmd),
                    'user': session.sesid
                }
                audit_log(db, log_dict)
                return web.seeother("/indicators")
            else:
                has_indicator = db.query(
                    "SELECT id FROM dhis2_mtrack_indicators_mapping "
                    "WHERE form=$form AND cmd=$cmd AND dataset=$dataset",
                    {'form': params.form, 'cmd': params.cmd, 'dataset': params.dataset})
                if has_indicator:
                    session.idata_err = (
                        "Indicator with Dataset:%s, From:%s, Command:%s "
                        "already registered" % (params.dataset, params.form, params.cmd)
                    )
                session.idata_err = ""
                r = db.query(
                    "INSERT INTO dhis2_mtrack_indicators_mapping (description, form, form_order, "
                    "slug, cmd, dataset, dataelement, category_combo, threshold) VALUES "
                    "($descr, $form, $form_order, $slug, $cmd, $dataset, $dataelement, "
                    "$category_combo, $threshold) RETURNING id", {
                        'descr': params.name, 'form': params.form,
                        'form_order': params.form_order, 'slug': params.slug,
                        'cmd': params.cmd, 'dataset': params.dataset, 'threshold': params.threshold,
                        'dataelement': params.dataelement, 'category_combo': params.category_combo}
                )

                log_dict = {
                    'logtype': 'Web', 'action': 'Create', 'actor': session.username,
                    'ip': web.ctx['ip'],
                    'descr': 'Created Indicator Mapping. Dataset %s: Form:%s Cmd:%s)' % (
                        params.dataset, params.form, params.cmd),
                    'user': session.sesid
                }
                audit_log(db, log_dict)
                return web.seeother("/indicators")

        l = locals()
        del l['self']
        return render.indicators(**l)
