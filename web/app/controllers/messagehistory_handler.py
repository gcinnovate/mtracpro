import web
import json
from . import csrf_protected, db, require_login, render
from settings import config
from app.tools.utils import get_request


class MessageHistory:
    @require_login
    def GET(self, phone):
        # params = web.input(d_id="")
        messages = {}
        phone = phone.replace("+", "")
        res = db.query(
            "SELECT id, uuid, firstname || ' ' || lastname as name "
            "FROM reporters WHERE replace(telephone, '+', '') = $tel "
            "OR replace(alternate_tel, '+', '') = $tel LIMIT 1", {'tel': phone})
        print(res)
        if res:
            telephone = phone
            reporter = res[0]
            uuid = reporter['uuid']
            name = reporter['name']
            try:
                resp = get_request(config['api_url'] + "messages.json?contact=%s" % uuid)
                messages = json.loads(resp.text)
                print(messages)
            except Exception as e:
                print(str(e))
                messages = {}
            if 'results' in messages:
                msgs = list(messages['results'])
                # msgs.reverse()
                chat_msgs = msgs[-4:]
        l = locals()
        del l['self']
        return render.messagehistory(**l)
