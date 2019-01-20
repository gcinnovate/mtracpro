import json
import web
# import settings
from . import db
from app.tools.utils import get_basic_auth_credentials, auth_user
# from settings import config


class IndicatorsAPI:
    """Returns mappins.json file used by the android client"""
    def GET(self):
        # params = web.input(form="")
        web.header("Content-Type", "application/json; charset=utf-8")

        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})

        indicators = db.query(
            "SELECT id, form_order, form, slug, cmd, description, shortname, dataset, dataelement, "
            "category_combo, threshold FROM dhis2_mtrack_indicators_mapping "
            "ORDER BY form, form_order")
        ret = {}
        for i in indicators:
            ret[i["slug"]] = {
                'categoryOptionCombo': i['category_combo'],
                'dataElement': i['dataelement'],
                'descr': i['description'],
            }
        return json.dumps(ret)
