import json
import unittest
import uuid
from unittest import mock

from webapp.app.controllers import api8
from webapp.app.controllers import api as dispatch_api
from webapp.app.controllers.api import (
    _instance_queue_payload,
    _keyword_uses_message_template,
    _save_template_request,
)


class DispatchBodyTest(unittest.TestCase):
    def setUp(self):
        self.templates = api8.KEYWORD_MESSAGE_TEMPLATE
        self.dispatch_templates = dispatch_api.KEYWORD_MESSAGE_TEMPLATE

    def tearDown(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = self.templates
        dispatch_api.KEYWORD_MESSAGE_TEMPLATE = self.dispatch_templates

    def test_missing_template_preserves_legacy_payload(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {}

        body, content_type = api8._dispatch_body("unknown", "hello", "+256700")

        self.assertEqual(body, "message=hello&originator=+256700")
        self.assertEqual(content_type, "text/plain")

    def test_string_template_substitutes_message_values(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {
            "alert": "message=$raw_msg&originator=$msisdn"
        }

        body, content_type = api8._dispatch_body("alert", "hello", "+256700")

        self.assertEqual(body, "message=hello&originator=+256700")
        self.assertEqual(content_type, "text/plain")

    def test_structured_template_is_rendered_and_json_encoded(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {
            "alert": {
                "text": "$raw_msg",
                "recipients": ["$msisdn"],
            }
        }

        body, content_type = api8._dispatch_body("alert", "hello", "+256700")

        self.assertEqual(
            json.loads(body),
            {"text": "hello", "recipients": ["+256700"]},
        )
        self.assertEqual(content_type, "application/json")

    def test_template_lookup_is_case_insensitive(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {
            "info": {
                "data": "$raw_msg",
                "from": "$msisdn",
            }
        }

        body, content_type = api8._dispatch_body("INFO", "hello", "+256700")

        self.assertEqual(
            json.loads(body),
            {"data": "hello", "from": "+256700"},
        )
        self.assertEqual(content_type, "application/json")

    def test_instance_queue_uses_template_payload(self):
        templates = {
            "info": {
                "data": "$raw_msg",
                "from": "$msisdn",
            }
        }
        api8.KEYWORD_MESSAGE_TEMPLATE = templates
        dispatch_api.KEYWORD_MESSAGE_TEMPLATE = templates

        body, queue_content_type, is_qparams = _instance_queue_payload(
            "INFO", "hello", "2567")

        self.assertEqual(json.loads(body), {"data": "hello", "from": "2567"})
        self.assertEqual(queue_content_type, "json")
        self.assertEqual(is_qparams, "f")

    def test_template_detection_is_case_insensitive(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {"info": {"text": "$raw_msg"}}

        self.assertTrue(_keyword_uses_message_template("INFO"))
        self.assertFalse(_keyword_uses_message_template("unknown"))

    @mock.patch("webapp.app.controllers.api.queue_request")
    def test_template_request_persists_raw_message_separately(self, queue_request):
        queue_request.return_value = 42

        _save_template_request(
            '{"text": "hello"}', "json", "INFO", "hello", "2567",
            2026, 10, "mtrackpro", "dhis2")

        queue_request.assert_called_once()
        saved_params = queue_request.call_args.args[1]
        self.assertEqual(saved_params["raw_msg"], "hello")
        self.assertEqual(saved_params["body"], '{"text": "hello"}')
        self.assertEqual(saved_params["ctype"], "json")

    @mock.patch("webapp.app.controllers.api8.queue_request")
    def test_direct_dispatch_template_persistence_uses_raw_message(self, queue_request):
        queue_request.return_value = 42

        api8._save_template_request(
            '{"text": "hello"}', "json", "INFO", "hello", "2567", 2026, 10)

        saved_params = queue_request.call_args.args[1]
        self.assertEqual(saved_params["raw_msg"], "hello")
        self.assertEqual(saved_params["body"], '{"text": "hello"}')

    @mock.patch("webapp.app.controllers.api8.datetime.datetime")
    def test_date_placeholder_uses_request_time(self, datetime_class):
        datetime_class.now.return_value.strftime.return_value = "2026-10-03"
        api8.KEYWORD_MESSAGE_TEMPLATE = {
            "alert": {
                "date": "$date",
                "message": "$raw_msg",
            }
        }

        body, content_type = api8._dispatch_body("alert", "hello", "+256700")

        self.assertEqual(
            json.loads(body),
            {"date": "2026-10-03", "message": "hello"},
        )
        self.assertEqual(content_type, "application/json")

    def test_uuid_placeholder_is_generated_per_request(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {
            "alert": {
                "message_id": "$uuid",
                "metadata": {"message_id": "$uuid"},
            }
        }

        first_body, _ = api8._dispatch_body("alert", "hello", "+256700")
        second_body, _ = api8._dispatch_body("alert", "hello", "+256700")
        first = json.loads(first_body)
        second = json.loads(second_body)

        first_uuid = uuid.UUID(first["message_id"])
        second_uuid = uuid.UUID(second["message_id"])

        self.assertEqual(first["message_id"], first["metadata"]["message_id"])
        self.assertEqual(second["message_id"], second["metadata"]["message_id"])
        self.assertNotEqual(first_uuid, second_uuid)

    def test_template_is_not_mutated_between_requests(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {
            "alert": {"text": "$raw_msg"}
        }

        first_body, _ = api8._dispatch_body("alert", "first", "+256700")
        second_body, _ = api8._dispatch_body("alert", "second", "+256700")

        self.assertEqual(json.loads(first_body), {"text": "first"})
        self.assertEqual(json.loads(second_body), {"text": "second"})
        self.assertEqual(api8.KEYWORD_MESSAGE_TEMPLATE["alert"]["text"], "$raw_msg")

    def test_unknown_placeholders_are_preserved(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = {"alert": "$raw_msg-$unknown"}

        body, _ = api8._dispatch_body("alert", "hello", "+256700")

        self.assertEqual(body, "hello-$unknown")


if __name__ == "__main__":
    unittest.main()
