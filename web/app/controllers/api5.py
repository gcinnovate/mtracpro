import json
import web
import datetime
from . import db
from app.tools.utils import get_webhook_msg_old, get_webhook_msg, queue_schedule
from settings import USE_OLD_WEBHOOKS, CARAMAL_RESEARCH_TEAM


class CaramalReminders:
    def POST(self):
        params = web.input(district="", subcounty="")
        if params.district and params.subcounty:
            if USE_OLD_WEBHOOKS:
                patient_id = get_webhook_msg_old(params, 'patient_id')
                patient_age = get_webhook_msg_old(params, 'patient_age')
                patient_sex = get_webhook_msg_old(params, 'patient_sex')
            else:
                payload = json.loads(web.data())
                patient_id = get_webhook_msg(payload, 'patient_id')
                patient_age = get_webhook_msg(payload, 'patient_age')
                patient_sex = get_webhook_msg(payload, 'patient_sex')

            district_contacts = CARAMAL_RESEARCH_TEAM.get(params.district, '')
            if district_contacts:
                subcounty_team_contacts = district_contacts.get(params.subcounty, '')
                if subcounty_team_contacts:
                    # time to schedule reminder accordingly
                    msg = (
                        "Patient with ID %s, age of %s and sex %s is "
                        "due for follow up 3 days from now." % (
                            patient_id, int(float(patient_age)), patient_sex))
                    sms_params = {'text': msg, 'to': subcounty_team_contacts}

                    current_time = datetime.datetime.now()
                    run_time = current_time + datetime.timedelta(days=25)
                    queue_schedule(db, sms_params, run_time, None, 'sms')
                    return json.dumps({"message": "scheduled successfully"})

        return json.dumps({"message": "success"})
