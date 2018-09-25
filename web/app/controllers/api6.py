import json
import web
from settings import USE_OLD_WEBHOOKS
from app.tools.utils import get_webhook_msg_old
from app.tools.utils import parse_message, get_webhook_msg


class Errors:
    def GET(self):
        # params = web.input()
        if USE_OLD_WEBHOOKS:
            # msg = get_webhook_msg_old(params, 'msg')
            pass
        else:
            # payload = json.loads(web.data())
            # msg = get_webhook_msg(payload, 'msg')
            pass
        return json.dumps({"message": "success"})

    def POST(self):
        params = web.input()
        if USE_OLD_WEBHOOKS:
            msg = get_webhook_msg_old(params, 'msg')
        else:
            payload = json.loads(web.data())
            msg = get_webhook_msg(payload, 'msg')

        message = parse_message(msg, 'cases')

        return json.dumps({"message": message})
