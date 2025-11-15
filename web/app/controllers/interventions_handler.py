import web
import tempfile
import json
import os
from string import Template
from . import db, require_login, render
from .tasks import send_sms_from_excel
from app.tools.utils import store_file_on_samba_server


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
        file_name = f.name
        f.close()
        file_saved = store_file_on_samba_server(file_name)
        if not file_saved:
            return json.dumps({
                "message": "Failed to upload file", "status": "Failed"})
        send_sms_from_excel.delay(os.path.basename(file_name), data.msg)
        os.unlink(file_name)
        return json.dumps({
            "message": "Results submission queued!", "status": "Success"})

        with db.transaction():
            return web.seeother("/interventions")

        l = locals()
        del l['self']
        return render.interventions(**l)


class Preview:
    def GET(self):
        params = web.input(msg="")
        kws = {
            'name': 'Samuel', 'Name': 'Samuel',
            'results': 'Negative', 'Results': 'Negative',
            'result': 'Negative', 'Result': 'Negative',
            'labid': 'UVRI-COV-02', 'LabID': 'UVRI-COV-02',
            'date': '20/04/2020', 'Date': '20/04/2020'
        }
        message = Template(params.msg).safe_substitute(kws)
        print(message)
        return "<p>{}</p>".format(message)
