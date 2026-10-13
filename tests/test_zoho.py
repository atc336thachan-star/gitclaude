from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from leads import zoho
from leads.models import ContactMessage, Lead, QuoteRequest

CFG = dict(ZOHO_CLIENT_ID="id", ZOHO_CLIENT_SECRET="sec", ZOHO_REFRESH_TOKEN="rt")


def fake_request(calls, fail_on=None):
    def f(method, url, data=None, headers=None, timeout=15):
        calls.append((method, url, data))
        if fail_on and fail_on in url:
            raise zoho.ZohoError("boom")
        if "oauth/v2/token" in url:
            return {"access_token": "AT", "expires_in": 3600}
        return {"data": [{"status": "success", "details": {"id": "Z123"}}]}
    return f


@override_settings(**CFG)
class ZohoSync(TestCase):
    def setUp(self):
        zoho._token.update(value="", exp=0.0)
        self.lead = Lead.objects.create(name="An", phone="0988123456", source="quote")
        self.q = QuoteRequest.objects.create(lead=self.lead, product_text="Sàn gỗ", quantity=20, unit="m²",
                                             province="Hà Nội", need_delivery=True)

    def test_disabled_without_keys(self):
        with override_settings(ZOHO_REFRESH_TOKEN=""), mock.patch("leads.zoho._request") as r:
            self.assertFalse(zoho.enabled())
            self.assertFalse(zoho.sync_quote(self.q))
            r.assert_not_called()

    def test_sync_quote_creates_lead_then_note_and_marks_synced(self):
        calls = []
        with mock.patch("leads.zoho._request", fake_request(calls)):
            self.assertTrue(zoho.sync_quote(self.q))
        urls = [c[1] for c in calls]
        self.assertTrue(urls[0].endswith(tuple(["oauth/v2/token?refresh_token=rt&client_id=id&client_secret=sec&grant_type=refresh_token"])))
        self.assertTrue(urls[1].endswith("/crm/v6/Leads/upsert"))
        self.assertTrue(urls[2].endswith("/crm/v6/Notes"))
        self.assertEqual(calls[1][2]["duplicate_check_fields"], ["Phone"])
        self.assertIn("Sàn gỗ", calls[2][2]["data"][0]["Note_Content"])
        self.lead.refresh_from_db(); self.q.refresh_from_db()
        self.assertEqual(self.lead.zoho_lead_id, "Z123")
        self.assertIsNotNone(self.q.zoho_synced_at)

    def test_second_event_reuses_zoho_id(self):
        calls = []
        m = ContactMessage.objects.create(lead=self.lead, message="Cần tư vấn")
        with mock.patch("leads.zoho._request", fake_request(calls)):
            zoho.sync_quote(self.q)
            self.lead.refresh_from_db()
            zoho.sync_message(ContactMessage.objects.select_related("lead").get(pk=m.pk))
        self.assertEqual(sum(c[1].endswith("Leads/upsert") for c in calls), 1)
        self.assertEqual(sum(c[1].endswith("/Notes") for c in calls), 2)
        self.assertEqual(sum("oauth/v2/token" in c[1] for c in calls), 1)  # token được cache

    def test_failure_is_swallowed_and_not_marked(self):
        with mock.patch("leads.zoho._request", fake_request([], fail_on="Leads/upsert")):
            self.assertFalse(zoho.sync_quote(self.q))
        self.q.refresh_from_db()
        self.assertIsNone(self.q.zoho_synced_at)

    def test_zoho_rejection_raises_zoho_error(self):
        with self.assertRaises(zoho.ZohoError):
            zoho._detail_id({"data": [{"status": "error", "code": "INVALID_DATA", "message": "x"}]})

    def test_retry_command_syncs_only_pending(self):
        from django.core.management import call_command
        QuoteRequest.objects.create(lead=self.lead, product_text="Đã gửi", zoho_synced_at=timezone.now())
        calls = []
        with mock.patch("leads.zoho._request", fake_request(calls)):
            call_command("sync_zoho")
        self.assertEqual(sum(c[1].endswith("/Notes") for c in calls), 1)


@override_settings(ZOHO_CLIENT_ID="id", ZOHO_CLIENT_SECRET="sec")
class ZohoTokenCommand(TestCase):
    def run_cmd(self, response, env_text):
        import tempfile
        from io import StringIO
        from pathlib import Path
        from django.core.management import call_command
        with tempfile.TemporaryDirectory() as d, override_settings(BASE_DIR=Path(d)):
            (Path(d) / ".env").write_text(env_text, encoding="utf-8")
            out = StringIO()
            with mock.patch("leads.zoho._request", return_value=response) as r:
                call_command("zoho_token", code="CODE1", stdout=out)
            return (Path(d) / ".env").read_text(encoding="utf-8"), out.getvalue(), r

    def test_writes_token_without_printing_it(self):
        env, out, r = self.run_cmd({"refresh_token": "SECRET_RT"}, "A=1\nZOHO_REFRESH_TOKEN=\nB=2\n")
        self.assertEqual(env, "A=1\nZOHO_REFRESH_TOKEN=SECRET_RT\nB=2\n")
        self.assertNotIn("SECRET_RT", out)
        self.assertIn("code=CODE1", r.call_args[0][1])

    def test_appends_when_key_missing(self):
        env, _, _ = self.run_cmd({"refresh_token": "RT"}, "A=1")
        self.assertEqual(env, "A=1\nZOHO_REFRESH_TOKEN=RT\n")

    def test_error_when_no_refresh_token(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.run_cmd({"error": "invalid_code"}, "A=1\n")
