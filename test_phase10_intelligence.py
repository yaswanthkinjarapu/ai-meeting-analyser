import sys
import json
import uuid
import urllib.request
import urllib.error
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase10_intelligence_suite():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent
    unique_suffix = uuid.uuid4().hex[:6]

    print("\n==============================================")
    print("   PHASE 10 ADVANCED INTELLIGENCE TEST SUITE   ")
    print("==============================================")

    # 1. Register User A and User B for User Isolation tests
    email_a = f"alice_p10_{unique_suffix}@example.com"
    email_b = f"bob_p10_{unique_suffix}@example.com"

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

    token_a, user_a_id = register_user(email_a, full_name="Alice P10")
    token_b, user_b_id = register_user(email_b, full_name="Bob P10")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    print(f"Registered User A ({email_a}) & User B ({email_b}).")

    # 2. Upload transcript for User A
    txt_path = base_dir / f"test_p10_transcript_{unique_suffix}.txt"
    txt_content = """[00:00:05] Alice: Welcome team. Today we will discuss the Cloud Migration project and API Redesign.
[00:00:15] Bob: For Cloud Migration, we need AWS credentials before setting up Terraform scripts. Task B setting up Terraform depends on Task A getting AWS credentials.
[00:00:35] Alice: Risk: Database migration might experience 10 minutes of downtime on Sunday due to large table indexing. We should schedule it during off-peak hours.
[00:00:55] Bob: Maybe we should also consider GCP as an alternative option?
[00:01:10] Alice: Decision: We officially decide to proceed with AWS.
[00:01:25] Bob: Action item: Bob will complete the Terraform configuration by Friday.
[00:01:40] Alice: Unresolved question: Who will approve the security compliance report?"""

    txt_path.write_text(txt_content, encoding="utf-8")

    boundary = f"----WebKitFormBoundaryPhase10_{unique_suffix}"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Phase 10 Intelligence Meeting",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{txt_path.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        txt_path.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    body_data = b"\r\n".join(parts)
    up_headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token_a}"
    }

    req_up = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=body_data,
        headers=up_headers,
        method="POST"
    )
    with urllib.request.urlopen(req_up) as resp_up:
        meeting_data = json.loads(resp_up.read().decode())["meeting"]
        meeting_id = meeting_data["id"]
        print(f"Uploaded Phase 10 test transcript as Meeting ID: {meeting_id}")

    # Clean up test text file
    if txt_path.exists():
        txt_path.unlink()

    # 3. Analyze meeting
    req_an = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/analyze",
        headers=headers_a,
        method="POST"
    )
    with urllib.request.urlopen(req_an) as resp_an:
        assert resp_an.status == 200
        print("Meeting analysis triggered successfully.")

    # 4. Verify /intelligence endpoint
    print("\n[Test 1] GET /{meeting_id}/intelligence")
    req_intel = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/intelligence",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_intel) as resp_intel:
        intel = json.loads(resp_intel.read().decode())
        assert intel["meeting_id"] == meeting_id
        summary = intel["summary"]
        assert summary["executive_summary"] is not None
        assert summary["detailed_summary_json"] is not None
        assert summary["conversational_tone"] is not None
        assert summary["meeting_outcome"] is not None
        assert intel["topics"] is not None
        assert intel["risks_blockers"] is not None
        assert intel["dependencies"] is not None
        assert intel["timeline_events"] is not None
        print("--> GET /intelligence verified successfully!")

    # 5. Verify /topics endpoint
    print("\n[Test 2] GET /{meeting_id}/topics")
    req_top = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/topics",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_top) as resp_top:
        top_data = json.loads(resp_top.read().decode())
        topics = top_data["topics"]
        assert len(topics) >= 1
        top_titles = [t["title"] for t in topics]
        print(f"Extracted topics: {top_titles}")
        print("--> GET /topics verified successfully!")

    # 6. Verify /timeline endpoint
    print("\n[Test 3] GET /{meeting_id}/timeline")
    req_time = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/timeline",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_time) as resp_time:
        time_data = json.loads(resp_time.read().decode())
        timeline = time_data["timeline"]
        assert len(timeline) >= 1
        assert "timestamp_seconds" in timeline[0]
        assert "event_title" in timeline[0]
        print(f"Extracted {len(timeline)} timeline events.")
        print("--> GET /timeline verified successfully!")

    # 7. Verify /risks endpoint
    print("\n[Test 4] GET /{meeting_id}/risks")
    req_risks = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/risks",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_risks) as resp_risks:
        r_data = json.loads(resp_risks.read().decode())
        risks = r_data["risks_blockers"]
        assert len(risks) >= 1
        downtime_risk = next((r for r in risks if "downtime" in r["description"].lower() or "risk" in r["description"].lower() or "downtime" in r["title"].lower()), None)
        assert downtime_risk is not None
        print(f"Detected risk: {downtime_risk['title']} - {downtime_risk['description']}")
        print("--> GET /risks verified successfully!")

    # 8. Verify /dependencies endpoint
    print("\n[Test 5] GET /{meeting_id}/dependencies")
    req_deps = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/dependencies",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_deps) as resp_deps:
        d_data = json.loads(resp_deps.read().decode())
        deps = d_data["dependencies"]
        assert len(deps) >= 1
        print(f"Extracted {len(deps)} task dependencies.")
        print("--> GET /dependencies verified successfully!")

    # 9. Verify /follow-up endpoint (Separation of facts vs suggestions)
    print("\n[Test 6] GET /{meeting_id}/follow-up")
    req_fol = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/follow-up",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_fol) as resp_fol:
        fol_data = json.loads(resp_fol.read().decode())
        assert "confirmed_facts" in fol_data
        assert "open_items" in fol_data
        assert "ai_suggestions" in fol_data
        
        decisions = fol_data["confirmed_facts"]["decisions"]
        suggestions = fol_data["ai_suggestions"]

        # Proceed with AWS is a confirmed decision
        aws_dec = next((d for d in decisions if "AWS" in d.get("decision_text", "")), None)
        assert aws_dec is not None, "AWS decision not found in confirmed decisions!"

        # GCP suggestion should be in suggestions or marked as suggestion
        gcp_sug = next((s for s in suggestions if "GCP" in s["suggestion_text"]), None)
        if gcp_sug:
            assert gcp_sug["is_suggestion"] is True

        print("--> GET /follow-up verified (Facts vs Suggestions separated)!")

    # 10. Verify User Isolation on Phase 10 Endpoints
    print("\n[Test 7] Phase 10 Endpoint User Isolation")
    isolated_endpoints = [
        f"/api/v1/meetings/{meeting_id}/intelligence",
        f"/api/v1/meetings/{meeting_id}/topics",
        f"/api/v1/meetings/{meeting_id}/timeline",
        f"/api/v1/meetings/{meeting_id}/risks",
        f"/api/v1/meetings/{meeting_id}/dependencies",
        f"/api/v1/meetings/{meeting_id}/follow-up",
    ]
    for ep in isolated_endpoints:
        req_iso = urllib.request.Request(f"{base_url}{ep}", headers=headers_b, method="GET")
        try:
            with urllib.request.urlopen(req_iso) as resp_iso:
                assert False, f"User B should not access User A's endpoint {ep}"
        except urllib.error.HTTPError as e:
            assert e.code in (403, 404), f"Expected 403/404 for {ep}, got {e.code}"
    print("--> User isolation verified across all Phase 10 endpoints!")

    # 11. Verify Multi-entity Search
    print("\n[Test 8] Multi-entity Search")
    req_srch = urllib.request.Request(
        f"{base_url}/api/v1/meetings/search?q=downtime",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_srch) as resp_srch:
        srch_res = json.loads(resp_srch.read().decode())
        assert len(srch_res) >= 1
        m_res = srch_res[0]
        assert m_res["id"] == meeting_id
        print("--> Multi-entity search for risk keyword 'downtime' verified successfully!")

    # 12. Verify Export (Markdown and JSON)
    print("\n[Test 9] Phase 10 Export Formats")
    # Markdown
    req_exp_md = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/export?format=markdown",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_exp_md) as resp_exp_md:
        md_text = resp_exp_md.read().decode("utf-8")
        assert "# Meeting Intelligence Report" in md_text
        assert "Executive Summary" in md_text
        assert "Key Discussion Topics" in md_text
        assert "Risks & Blockers" in md_text
        print("--> Markdown export contains Phase 10 intelligence!")

    # JSON
    req_exp_json = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/export?format=json",
        headers=headers_a,
        method="GET"
    )
    with urllib.request.urlopen(req_exp_json) as resp_exp_json:
        json_exp = json.loads(resp_exp_json.read().decode("utf-8"))
        assert "summary" in json_exp
        assert "topics" in json_exp
        assert "risks_and_blockers" in json_exp
        assert "task_dependencies" in json_exp
        print("--> JSON export contains Phase 10 intelligence!")

    print("\n==============================================")
    print("   ALL PHASE 10 TESTS PASSED (100% SUCCESS)    ")
    print("==============================================\n")

if __name__ == "__main__":
    test_phase10_intelligence_suite()
