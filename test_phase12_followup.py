import sys
import os
import unittest
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.deadline_service import normalize_deadline
from app.services.providers.base_calendar import BaseCalendarProvider
from app.services.providers.mock_calendar import MockCalendarProvider
from app.services.providers.google_calendar import GoogleCalendarProvider
from app.services.providers.base_email import BaseEmailProvider
from app.services.providers.mock_email import MockEmailProvider
from app.services.providers.gmail_provider import GmailEmailProvider

client = TestClient(app)

class TestPhase12FollowUpAutomation(unittest.TestCase):
    """
    Phase 12 Comprehensive Test Suite:
    - Deadline Normalization Service
    - Calendar Provider Abstraction
    - Email Provider Abstraction
    - Follow-Up Center Endpoints
    - User Settings & Timezones
    - Reminders Engine
    - Strict User Isolation & Security
    - Grounding & Evidence Preservation
    """

    def setUp(self):
        # Register User A
        self.user_a_email = f"user_a_{datetime.now().timestamp()}@example.com"
        self.user_a_password = "Password123!"
        resp_a = client.post("/api/v1/auth/register", json={
            "email": self.user_a_email,
            "password": self.user_a_password
        })
        self.assertIn(resp_a.status_code, [200, 201], resp_a.text)
        self.user_a_token = resp_a.json()["access_token"]
        self.headers_a = {"Authorization": f"Bearer {self.user_a_token}"}

        # Register User B (for isolation tests)
        self.user_b_email = f"user_b_{datetime.now().timestamp()}@example.com"
        self.user_b_password = "Password123!"
        resp_b = client.post("/api/v1/auth/register", json={
            "email": self.user_b_email,
            "password": self.user_b_password
        })
        self.assertIn(resp_b.status_code, [200, 201], resp_b.text)
        self.user_b_token = resp_b.json()["access_token"]
        self.headers_b = {"Authorization": f"Bearer {self.user_b_token}"}

    def test_deadline_normalization_service(self):
        """Verify deadline normalization converts explicit terms to datetime and keeps 'soon' as None."""
        user_tz = "UTC"
        
        # 1. Explicit term: tomorrow at 3 PM
        dt_tomorrow, tz = normalize_deadline("tomorrow at 3 PM", user_tz=user_tz)
        self.assertIsNotNone(dt_tomorrow)
        self.assertTrue(isinstance(dt_tomorrow, datetime))
        
        # 2. ISO format string
        dt_iso, tz = normalize_deadline("2026-10-15T14:30:00Z", user_tz=user_tz)
        self.assertIsNotNone(dt_iso)
        self.assertEqual(dt_iso.year, 2026)
        self.assertEqual(dt_iso.month, 10)
        self.assertEqual(dt_iso.day, 15)

        # 3. Unresolvable vague terms ("soon", "ASAP", "tbd") MUST return None
        dt_soon, tz = normalize_deadline("soon", user_tz=user_tz)
        self.assertIsNone(dt_soon, "Vague term 'soon' must return None without guessing")

        dt_asap, tz = normalize_deadline("ASAP", user_tz=user_tz)
        self.assertIsNone(dt_asap, "Vague term 'ASAP' must return None without guessing")

    def test_provider_abstractions(self):
        """Verify Calendar and Email Provider abstractions."""
        # Calendar Provider Test
        cal_provider = MockCalendarProvider()
        now = datetime.now(timezone.utc)
        created_event = cal_provider.create_event(
            title="Follow up on Security Audit",
            start_time=now,
            end_time=now,
            description="Discuss open vulnerability findings",
            timezone="UTC"
        )
        self.assertIsNotNone(created_event["external_event_id"])
        self.assertEqual(created_event["status"], "confirmed")
        self.assertTrue(cal_provider.delete_event(created_event["external_event_id"]))

        # Email Provider Test
        email_provider = MockEmailProvider()
        sent_email = email_provider.send_email(
            recipient="bob@example.com",
            subject="Meeting Action Item Update",
            body="Hi Bob, please find the summary attached."
        )
        self.assertIsNotNone(sent_email["external_id"])
        self.assertEqual(sent_email["status"], "SENT")

    def test_user_settings_and_timezone(self):
        """Verify user settings retrieval and updates."""
        # Get default settings
        res = client.get("/api/v1/settings", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        settings = res.json()
        self.assertEqual(settings["timezone"], "Asia/Kolkata")

        # Update settings to UTC
        res_update = client.put("/api/v1/settings", headers=self.headers_a, json={
            "timezone": "UTC",
            "remind_24h_before": 1,
            "remind_when_overdue": 1,
            "remind_questions_days": 5
        })
        self.assertEqual(res_update.status_code, 200)
        updated = res_update.json()
        self.assertEqual(updated["timezone"], "UTC")
        self.assertEqual(updated["remind_questions_days"], 5)

    def test_followup_center_and_action_item_workflow(self):
        """Verify end-to-end follow-up workflow: meeting -> action item -> schedule -> calendar event & email draft."""
        # 1. Create a meeting for User A
        res_m = client.post("/api/v1/meetings/upload", headers=self.headers_a, files={
            "file": ("notes.txt", b"Alice will complete the security audit report by tomorrow at 5 PM. Bob has a question about budget.", "text/plain")
        })
        self.assertIn(res_m.status_code, [200, 201], res_m.text)
        meeting_id = res_m.json()["meeting"]["id"]

        # 2. Trigger transcript processing & AI Analysis
        res_p = client.post(f"/api/v1/meetings/{meeting_id}/process-transcript", headers=self.headers_a)
        self.assertEqual(res_p.status_code, 200)

        res_ana = client.post(f"/api/v1/meetings/{meeting_id}/analyze", headers=self.headers_a)
        self.assertEqual(res_ana.status_code, 200)

        # 3. Query Follow-Up Center
        res_fc = client.get("/api/v1/follow-ups", headers=self.headers_a)
        self.assertEqual(res_fc.status_code, 200)
        fc_data = res_fc.json()
        self.assertIn("overdue_actions", fc_data)
        self.assertIn("due_soon_actions", fc_data)
        self.assertIn("open_questions", fc_data)
        self.assertIn("risks_blockers", fc_data)
        self.assertIn("suggestions", fc_data)
        self.assertIn("calendar_events", fc_data)
        self.assertIn("email_drafts", fc_data)

        # Get an action item from the analysis
        analysis = client.get(f"/api/v1/meetings/{meeting_id}/analysis", headers=self.headers_a).json()
        self.assertTrue(len(analysis["action_items"]) > 0)
        action_item = analysis["action_items"][0]

        # 4. Prepare schedule follow-up suggestion
        res_prep = client.post(f"/api/v1/follow-ups/{action_item['id']}/schedule", headers=self.headers_a)
        self.assertEqual(res_prep.status_code, 200)
        prep_data = res_prep.json()
        self.assertIn("suggested_duration_minutes", prep_data)
        self.assertIn("evidence_quote", prep_data)

        # 5. Create Calendar Event explicitly (User Confirmation Rule)
        now_str = datetime.now(timezone.utc).isoformat()
        res_cal = client.post("/api/v1/calendar/events", headers=self.headers_a, json={
            "action_item_id": action_item["id"],
            "title": f"Follow-up: {action_item['task_description']}",
            "description": "Follow-up calendar event",
            "start_time": now_str,
            "end_time": now_str
        })
        self.assertIn(res_cal.status_code, [200, 201], res_cal.text)
        cal_event = res_cal.json()
        self.assertEqual(cal_event["title"], f"Follow-up: {action_item['task_description']}")

        # Verify action item follow_up_status updated to SCHEDULED
        analysis_updated = client.get(f"/api/v1/meetings/{meeting_id}/analysis", headers=self.headers_a).json()
        item_updated = next(a for a in analysis_updated["action_items"] if a["id"] == action_item["id"])
        self.assertEqual(item_updated["follow_up_status"], "SCHEDULED")

        # 6. Create Email Draft
        res_draft = client.post("/api/v1/email/drafts", headers=self.headers_a, json={
            "action_item_id": action_item["id"],
            "recipient": "alice@example.com",
            "subject": f"Follow-up: {action_item['task_description']}",
            "body": "Hi Alice, please update on the progress."
        })
        self.assertIn(res_draft.status_code, [200, 201], res_draft.text)
        draft = res_draft.json()
        self.assertEqual(draft["status"], "DRAFT")

        # 7. Explicit Send Email (User Confirmation)
        res_send = client.post(f"/api/v1/email/send?draft_id={draft['id']}", headers=self.headers_a)
        self.assertEqual(res_send.status_code, 200)
        sent_draft = res_send.json()
        self.assertEqual(sent_draft["status"], "SENT")

        # 8. Verify Reminders Endpoint
        res_rem = client.get("/api/v1/reminders", headers=self.headers_a)
        self.assertEqual(res_rem.status_code, 200)

    def test_user_isolation_and_security(self):
        """Verify strict user isolation for all Phase 12 endpoints."""
        # User A creates a calendar event
        now_str = datetime.now(timezone.utc).isoformat()
        res_cal = client.post("/api/v1/calendar/events", headers=self.headers_a, json={
            "title": "User A Private Event",
            "description": "Secret notes",
            "start_time": now_str,
            "end_time": now_str
        })
        self.assertIn(res_cal.status_code, [200, 201], res_cal.text)
        event_a_id = res_cal.json()["id"]

        # User B attempts to delete User A's calendar event -> 404 (or 403)
        res_del = client.delete(f"/api/v1/calendar/events/{event_a_id}", headers=self.headers_b)
        self.assertEqual(res_del.status_code, 404)

        # User B queries calendar events -> Must NOT see User A's event
        res_list_b = client.get("/api/v1/calendar/events", headers=self.headers_b)
        self.assertEqual(res_list_b.status_code, 200)
        events_b = res_list_b.json()
        event_ids_b = [e["id"] for e in events_b]
        self.assertNotIn(event_a_id, event_ids_b)

        # User B attempts to send email draft created by User A
        res_draft_a = client.post("/api/v1/email/drafts", headers=self.headers_a, json={
            "recipient": "confidential@example.com",
            "subject": "User A Private Draft",
            "body": "Private content"
        })
        self.assertIn(res_draft_a.status_code, [200, 201], res_draft_a.text)
        draft_a_id = res_draft_a.json()["id"]

        res_send_b = client.post(f"/api/v1/email/send?draft_id={draft_a_id}", headers=self.headers_b)
        self.assertEqual(res_send_b.status_code, 404)

if __name__ == "__main__":
    unittest.main()
