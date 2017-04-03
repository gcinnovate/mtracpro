import web
from . import csrf_protected, db, require_login, render


class FSync:
    @require_login
    def GET(self):
        # params = web.input(d_id="")
        l = locals()
        del l['self']
        return render.fsync(**l)
