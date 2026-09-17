import sys
import json
import uuid
import urllib.request
import urllib.error
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase11_live_meeting_suite():
    base_url = "http://127.0.0.1:8000"
    unique_suffix = uuid.uuid4().hex[:6]

    print("\n==============================================")
    print("   PHASE 11 LIVE MEETING INTELLIGENCE TEST    ")
    print("==============================================")

    # 1. Register User A and User B for User Isolation tests
    email_a = f"alice_p11_{unique_suffix}@example.com"
    email_b = f"bob_p11_{unique_suffix}@example.com"

    def register_user(email, password="Password123!", full_name="Test User"):
        payload = json.dumps({"email": email, "password": password, "full_name": full_name}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/v1/auth/register",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data["access_token"], data["user"]["id"]

    token_a, user_a_id = register_user(email_a, full_name="Alice Live")
    token_b, user_b_id = register_user(email_b, full_name="Bob Live")

    headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

    print(f"Registered User A ({email_a}) & User B ({email_b}).")

    # 2. Start Live Meeting Session for User A
    print("\n[Test 1] Start Live Meeting Session (POST /api/v1/live-meetings)")
    start_payload = json.dumps({"title": "Live Architecture & Sprint Planning"}).encode("utf-8")
    req_start = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings",
        data=start_payload,
        headers=headers_a,
        method="POST"
    )
    with urllib.request.urlopen(req_start) as resp_start:
        assert resp_start.status == 201
        session_data = json.loads(resp_start.read().decode())
        session_id = session_data["session_id"]
        meeting_id = session_data["meeting_id"]
        assert session_data["status"] == "RECORDING"
        assert session_data["user_id"] == user_a_id
        print(f"--> Live session created! Session ID: {session_id}, Meeting ID: {meeting_id}")

    # 3. GET Live Session Details
    print("\n[Test 2] GET Live Session Details")
    req_get = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_get) as resp_get:
        get_data = json.loads(resp_get.read().decode())
        assert get_data["session_id"] == session_id
        assert get_data["status"] == "RECORDING"
        print("--> Live session details retrieved successfully.")

    # 4. User Isolation & Authentication Security Tests
    print("\n[Test 3] User Isolation Security Tests")
    # User B attempting to get User A's session -> HTTP 403
    req_b_get = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}",
        headers=headers_b,
        method="GET"
    )
    try:
        with urllib.request.urlopen(req_b_get) as resp_b:
            assert False, "User B should not be able to access User A's live session!"
    except urllib.error.HTTPError as e:
        assert e.code == 403, f"Expected 403 Forbidden, got {e.code}"
        print("--> User B rejected with 403 Forbidden as expected!")

    # Unauthenticated request -> HTTP 401
    req_unauth = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}",
        method="GET"
    )
    try:
        with urllib.request.urlopen(req_unauth) as resp_u:
            assert False, "Unauthenticated request should be rejected!"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401 Unauthorized, got {e.code}"
        print("--> Unauthenticated request rejected with 401 Unauthorized as expected!")

    # 5. Pause and Resume Live Meeting
    print("\n[Test 4] Pause & Resume Live Meeting State Machine")
    # Pause
    req_pause = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}/pause",
        headers=headers_a,
        method="POST"
    )
    with urllib.request.urlopen(req_pause) as resp_pause:
        p_data = json.loads(resp_pause.read().decode())
        assert p_data["status"] == "PAUSED"
        print("--> Session paused successfully.")

    # Resume
    req_resume = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}/resume",
        headers=headers_a,
        method="POST"
    )
    with urllib.request.urlopen(req_resume) as resp_resume:
        r_data = json.loads(resp_resume.read().decode())
        assert r_data["status"] == "RECORDING"
        print("--> Session resumed successfully.")

    # 6. Live Transcript & Incremental Intelligence Verification
    print("\n[Test 5] Live Transcript & Incremental Intelligence Processing")
    import sqlite3
    db_path = Path(__file__).resolve().parent / "data" / "meeting.db"

    # Insert live transcript segments into SQLite directly to simulate WebSocket ingestion
    live_chunks = [
        ("Alice", "Welcome team. Today we will discuss the database and API redesign.", 0.0, 10.0),
        ("Bob", "For the database, okay, let's use PostgreSQL for our production backend.", 12.0, 22.0),
        ("Bob", "Action item: I will complete the database schema migration by Friday.", 25.0, 35.0),
        ("Bob", "Someone should prepare the security compliance document.", 38.0, 48.0),
        ("Alice", "Risk: Database migration might experience 10 minutes of downtime on Sunday.", 50.0, 60.0),
        ("Bob", "Unresolved question: Who will sign off on the production deployment?", 62.0, 72.0)
    ]

    from app.services import live_session_service, ai_intelligence
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        for speaker, text, s_time, e_time in live_chunks:
            live_session_service.process_live_transcript_chunk(
                session_id=session_id,
                text=text,
                speaker_label=speaker,
                start_time=s_time,
                end_time=e_time,
                db=db
            )
        print(f"--> Ingested {len(live_chunks)} live transcript chunks.")

        ai_intelligence.process_meeting_analysis(meeting_id, db)
        print(f"--> Triggered AI intelligence analysis.")
    finally:
        db.close()

    # Verify extracted live intelligence via GET /meetings/{id}/intelligence
    req_intel = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/intelligence",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_intel) as resp_intel:
        intel = json.loads(resp_intel.read().decode())
        decisions = intel["decisions"]
        actions = intel["action_items"]
        questions = intel["unresolved_questions"]
        risks = intel["risks_blockers"]

        assert len(decisions) >= 1
        assert any("PostgreSQL" in d["decision_text"] for d in decisions)
        print(f"--> Live Decision Extracted: {decisions[0]['decision_text']}")

        assert len(actions) >= 2
        explicit_action = next(a for a in actions if "database schema migration" in a["task_description"])
        assert explicit_action["responsible_person"] == "Bob"
        assert explicit_action["deadline"] == "by Friday"

        unassigned_action = next(a for a in actions if "security compliance document" in a["task_description"])
        assert unassigned_action["responsible_person"] is None

        assert len(questions) >= 1
        assert len(risks) >= 1
        print("--> Incremental Live Intelligence (Decisions, Actions, Owners, Deadlines, Risks, Questions) verified 100%!")

    # 7. Stop Live Meeting Session
    print("\n[Test 6] Stop Live Session (POST /api/v1/live-meetings/{session_id}/stop)")
    req_stop = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}/stop",
        headers=headers_a,
        method="POST"
    )
    with urllib.request.urlopen(req_stop) as resp_stop:
        final_report = json.loads(resp_stop.read().decode())
        assert final_report["meeting_id"] == meeting_id
        assert final_report["status"] in ["COMPLETED", "ANALYZED"]
        print("--> Live Session stopped & final Phase 10 report generated successfully!")

    # Verify session status in DB is COMPLETED
    req_final_get = urllib.request.Request(
        f"{base_url}/api/v1/live-meetings/{session_id}",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_final_get) as resp_fget:
        f_data = json.loads(resp_fget.read().decode())
        assert f_data["status"] == "COMPLETED"
        print("--> Session status verified as COMPLETED in database!")

    print("\n==============================================")
    print("   ALL PHASE 11 TESTS PASSED (100% SUCCESS)   ")
    print("==============================================\n")

if __name__ == "__main__":
    test_phase11_live_meeting_suite()
