import web
from . import csrf_protected, db, require_login, render


class DataEntry:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed

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
