import web
from . import csrf_protected, db, require_login, render


class AppSettings:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed

        l = locals()
        del l['self']
        return render.appsettings(**l)

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
                return web.seeother("/appsettings")
            else:
                return web.seeother("/appsettings")

        l = locals()
        del l['self']
        return render.appsettings(**l)
