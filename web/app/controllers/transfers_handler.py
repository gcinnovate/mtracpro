import web
from . import csrf_protected, db, require_login, render


class Transfers:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        l = locals()
        del l['self']
        return render.transfers(**l)

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
                return web.seeother("/transfers")
            else:
                return web.seeother("/transfers")

        l = locals()
        del l['self']
        return render.transfers(**l)
