import web
import tempfile
import json
from . import csrf_protected, db, require_login, render
from tasks import send_sms_from_excel


class Interventions:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        l = locals()
        del l['self']
        return render.interventions(**l)

    @require_login
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        data = web.input(excel_file={}, msg="")
        fp = data.excel_file
        print(data.msg)
        if 'vnd.openxmlformats-officedocument' not in getattr(fp, 'type'):
            return json.dumps({
                "message": "File type unsupported. use .xlsx files", "status": "Failed"})
        f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        f.write(fp.file.read())
        print(f.name)
        # os.unlink(f.name)
        send_sms_from_excel.delay(f.name, data.msg)
        return json.dumps({
            "message": "Results submission queued!", "status": "Success"})

        with db.transaction():
            return web.seeother("/interventions")

        l = locals()
        del l['self']
        return render.interventions(**l)
