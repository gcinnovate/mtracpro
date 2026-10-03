import json
import unittest
from unittest import mock

from webapp.app.controllers import api8


class DispatchBodyTest(unittest.TestCase):
    def setUp(self):
        self.templates = api8.KEYWORD_MESSAGE_TEMPLATE

    def tearDown(self):
        api8.KEYWORD_MESSAGE_TEMPLATE = self.templates

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
