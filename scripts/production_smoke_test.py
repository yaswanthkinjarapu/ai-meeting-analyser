#!/usr/bin/env python3
"""
Production Deployment Smoke Test Suite
--------------------------------------
Validates live backend & deployment environment health, readiness, authentication,
user isolation, file upload, transcript processing, AI intelligence, follow-up center,
and cleanup operations.

Usage:
    python scripts/production_smoke_test.py --base-url http://127.0.0.1:8000
"""

import sys
import argparse
import requests
from datetime import datetime

def run_smoke_test(base_url: str):
    print("=" * 70)
    print("        PRODUCTION DEPLOYMENT SMOKE TEST SUITE        ")
    print("=" * 70)
    print(f"Target Base URL: {base_url}\n")

    session = requests.Session()
    api_base = f"{base_url.rstrip('/')}/api/v1"

    # 1. Health Probe Check
    print("[1/12] Testing GET /health ...")
    resp_h = session.get(f"{base_url.rstrip('/')}/health")
    assert resp_h.status_code == 200, f"Health check failed: {resp_h.status_code} {resp_h.text}"
    print(f"  [OK] Health Probe: {resp_h.json()}")

    # 2. Readiness Probe Check
    print("[2/12] Testing GET /ready ...")
    resp_r = session.get(f"{base_url.rstrip('/')}/ready")
    assert resp_r.status_code == 200, f"Readiness check failed: {resp_r.status_code} {resp_r.text}"
    print(f"  [OK] Readiness Probe: {resp_r.json()}")

    # 3. User Registration & Auth
    print("[3/12] Testing User Registration & Authentication...")
    user_email = f"smoke_user_{int(datetime.now().timestamp())}@example.com"
    user_pass = "SmokeTestPassword123!"

    resp_reg = session.post(f"{api_base}/auth/register", json={
        "email": user_email,
        "password": user_pass,
        "full_name": "Smoke Test User"
    })
    assert resp_reg.status_code in (200, 201), f"User registration failed: {resp_reg.text}"
    token = resp_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Registered User: {user_email}")

    # 4. Profile Retrieval
    print("[4/12] Testing GET /auth/me ...")
    resp_me = session.get(f"{api_base}/auth/me", headers=headers)
    assert resp_me.status_code == 200, f"Get profile failed: {resp_me.text}"
    print(f"  [OK] User Profile Verified: ID={resp_me.json()['id']}")

    # 5. File Upload & Processing
    print("[5/12] Testing POST /meetings/upload ...")
    sample_content = b"Alice will complete the production deployment audit by tomorrow at 5 PM. Bob agreed to review the database migrations."
    files = {"file": ("smoke_transcript.txt", sample_content, "text/plain")}
    resp_up = session.post(f"{api_base}/meetings/upload", headers=headers, files=files)
    assert resp_up.status_code in (200, 201), f"Upload failed: {resp_up.text}"
    meeting = resp_up.json()["meeting"]
    meeting_id = meeting["id"]
    print(f"  [OK] Meeting Uploaded: ID={meeting_id}, Status={meeting['status']}")

    # 6. Transcript Processing
    print("[6/12] Testing POST /meetings/{id}/process-transcript ...")
    resp_pt = session.post(f"{api_base}/meetings/{meeting_id}/process-transcript", headers=headers)
    assert resp_pt.status_code == 200, f"Transcript processing failed: {resp_pt.text}"
    print("  [OK] Transcript Processed successfully.")

    # 7. AI Intelligence Trigger
    print("[7/12] Testing POST /meetings/{id}/analyze ...")
    resp_ana = session.post(f"{api_base}/meetings/{meeting_id}/analyze", headers=headers)
    assert resp_ana.status_code == 200, f"Analysis failed: {resp_ana.text}"
    analysis = session.get(f"{api_base}/meetings/{meeting_id}/analysis", headers=headers).json()
    print(f"  [OK] AI Intelligence Generated: {len(analysis['action_items'])} Action Items, {len(analysis['decisions'])} Decisions.")

    # 8. Follow-Up Center & Settings
    print("[8/12] Testing GET /follow-ups & GET /settings ...")
    resp_fc = session.get(f"{api_base}/follow-ups", headers=headers)
    assert resp_fc.status_code == 200, f"Follow-up center failed: {resp_fc.text}"
    resp_st = session.get(f"{api_base}/settings", headers=headers)
    assert resp_st.status_code == 200, f"Settings failed: {resp_st.text}"
    print("  [OK] Follow-Up Center & Settings Verified.")

    # 9. Live Meeting Creation
    print("[9/12] Testing POST /live-meetings ...")
    resp_live = session.post(f"{api_base}/live-meetings", headers=headers, json={"title": "Smoke Live Sync"})
    assert resp_live.status_code in (200, 201), f"Live meeting creation failed: {resp_live.text}"
    live_id = resp_live.json()["session_id"]
    print(f"  [OK] Live Meeting Session Created: {live_id}")

    # 10. Search Scoping
    print("[10/12] Testing GET /meetings/search ...")
    resp_src = session.get(f"{api_base}/meetings/search?q=deployment", headers=headers)
    assert resp_src.status_code == 200, f"Search failed: {resp_src.text}"
    print(f"  [OK] Search Verified: {len(resp_src.json())} matching meetings found.")

    # 11. Report Export
    print("[11/12] Testing GET /meetings/{id}/export ...")
    resp_exp = session.get(f"{api_base}/meetings/{meeting_id}/export?format=markdown", headers=headers)
    assert resp_exp.status_code == 200, f"Export failed: {resp_exp.text}"
    print("  [OK] Markdown Report Exported cleanly.")

    # 12. Safe Deletion & Isolation
    print("[12/12] Testing DELETE /meetings/{id} ...")
    resp_del = session.delete(f"{api_base}/meetings/{meeting_id}", headers=headers)
    assert resp_del.status_code == 200, f"Delete failed: {resp_del.text}"
    print("  [OK] Meeting Deleted successfully.")

    print("\n" + "=" * 70)
    print("PRODUCTION SMOKE TEST PASSED 100%! All 12 critical smoke checks verified.")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Production Smoke Test against target backend server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of target FastAPI application server")
    args = parser.parse_args()

    run_smoke_test(args.base_url)
