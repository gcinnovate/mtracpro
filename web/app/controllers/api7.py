import json
import web
from . import db, anonymous_report_responses
from settings import USE_OLD_WEBHOOKS
from app.tools.utils import get_webhook_msg_old, get_webhook_msg
from app.tools.utils import queue_anonymous_report
from .tasks import sendsms_to_uuids_task


class AnonymousReports:
    def POST(self):
        params = web.input(
            contact_uuid="", msg="")
        contact_uuid = params.contact_uuid
        msg = params.msg
        # if USE_OLD_WEBHOOKS:
        #     msg = get_webhook_msg_old(params, 'msg')
        # else:
        #     payload = json.loads(web.data())
        #     msg = get_webhook_msg(payload, 'msg')
        print(contact_uuid + "=> " + msg)
        extra_params = {'contact_uuid': contact_uuid, 'report': msg}
        report_id, has_report = queue_anonymous_report(db, extra_params)
        if has_report:
            resp_msg = "Thank you for your consistent feedback about this health facility."
        else:
            resp_msg = (
                "Your report has been sent to relevant authorities. You can also call Ministry "
                "of Health on 0800100066 (toll free) for further help and inquires. "
                "If this is an emergency contact your nearest facility")

        return json.dumps({'message': resp_msg})


class AnonymousReportDetails:
    def GET(self, report_id):
        htmlStr = '<table class="table table-striped table-bordered table-hover">'
        htmlStr += "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
        rs = db.query(
            "SELECT id, facility, district, created, report, action, topic, "
            "action_taken, action_center, comment FROM anonymousreports_view "
            "WHERE id = $id", {'id': report_id})
        if rs:
            rpt = rs[0]
            htmlStr += "<tr><td>Facility</td><td>%s</td></tr>" % rpt['facility']
            htmlStr += "<tr><td>District</td><td>%s</td></tr>" % rpt['district']
            htmlStr += "<tr><td>Date</td><td>%s</td></tr>" % rpt['created']
            htmlStr += "<tr><td>Reports</td><td>%s</td></tr>" % rpt['report']
            htmlStr += "<tr><td>Topic</td><td>%s</td></tr>" % rpt['topic']
            htmlStr += "<tr><td>Action</td><td>%s</td></tr>" % rpt['action']
            htmlStr += "<tr><td>Action Center</td><td>%s</td></tr>" % rpt['action_center']
            htmlStr += "<tr><td>Comments</td><td>%s</td></tr>" % rpt['comment']
            htmlStr += "<tr><td>Action Taken</td><td>%s</td></tr>" % rpt['action_taken']
            htmlStr += "<tr><td>Responses</td><td>%s</td></tr>" % anonymous_report_responses(rpt['id'])

        htmlStr += "</tbody></table>"
        return htmlStr


class AnonReport:
    def GET(self, report_id):
        web.header("Content-Type", "application/json; charset=utf-8")
        rs = db.query(
            "SELECT id, facility, district, to_char(created, 'YYYY-MM-DD HH:MI:SS') AS created,"
            "report, action, topic, action_taken, action_center, comment, "
            "districtid, facilityid FROM anonymousreports_view "
            "WHERE id = $id", {'id': report_id})
        if rs:
            rpt = rs[0]

            report = {
                'id': rpt['id'], 'facility': rpt['facility'], 'district': rpt['district'],
                'created': rpt['created'], 'report': rpt['report'], 'action': rpt['action'],
                'topic': rpt['topic'], 'action_taken': rpt['action_taken'],
                'action_center': rpt['action_center'], 'comment': rpt['comment'],
                'facilityid': rpt['facilityid'], 'districtid': rpt['districtid'],
                'responses': anonymous_report_responses(rpt['id'])
            }
            return json.dumps(report)
        return json.dumps({})

    def POST(self, report_id):
        web.header("Content-Type", "application/json; charset=utf-8")
        params = web.input()
        rs = db.query(
            "SELECT contact_uuid, action_taken FROM anonymousreports WHERE id = $id",
            {'id': report_id})
        if rs:
            rpt = rs[0]

            db.query(
                "UPDATE anonymousreports SET (facilityid, districtid, action, action_center, "
                "topic, action_taken) = ($facility, $district, $action, $action_center, "
                "$topic, $action_taken) "
                " WHERE id = $id", {
                    'id': report_id, 'facility': params.facility if params.facility else None,
                    'district': params.district if params.district else None,
                    'action': params.action,
                    'action_center': params.action_center, 'topic': params.topic,
                    'action_taken': params.action_taken})

            if params.action_taken and (rpt['action_taken'] != params.action_taken):
                # send action taken to use
                sendsms_to_uuids_task.delay([rpt['contact_uuid']], params.action_taken)
                db.query(
                    "INSERT INTO anonymousreport_messages (report_id, message, direction) "
                    "VALUES($report_id, $msg, 'O') ", {'report_id': report_id, 'msg': params.action_taken})

            return json.dumps({"message": "saved successfully.", "status": "success"})
