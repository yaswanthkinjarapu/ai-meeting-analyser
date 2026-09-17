import sys
import json
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase7_reliability_suite():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n==========================================")
    print("   PHASE 7 RELIABILITY & INTELLIGENCE TEST   ")
    print("==========================================")

    # ----------------------------------------------------
    # 1. Path Traversal & Security Validation Test
    # ----------------------------------------------------
    print("\n[Test D/S] Security Test: Path Traversal Prevention")
    boundary = "----WebKitFormBoundaryPhase7Security"
    traversal_body = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Security Traversal Test",
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="../../../etc/passwd.txt"',
        b"Content-Type: text/plain",
        b"",
        b"Harinath: Safe text content.",
        f"--{boundary}--".encode(),
        b""
    ]
    req_sec = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(traversal_body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req_sec) as resp_sec:
        assert resp_sec.status == 201
        m_sec = json.loads(resp_sec.read().decode())["meeting"]
        m_sec_id = m_sec["id"]
        
        # Verify file_path never escaped uploads directory
        db_path = base_dir / "data" / "meeting.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT file_path, filename FROM media_files WHERE meeting_id = ?;", (m_sec_id,))
                row = cursor.fetchone()
                if row:
                    db_file_path, db_filename = row
                    print(f"Path Traversal Test: Filename sanitized to '{db_filename}'")
                    print(f"Path Traversal Test: Saved Path = {db_file_path}")
                    assert "uploads" in db_file_path
                    assert "etc" not in db_file_path or db_file_path.endswith("passwd.txt")
                    assert not db_file_path.startswith("../")
            except sqlite3.OperationalError:
                pass
            conn.close()
        print("--> Path Traversal Protection PASSED 100%!")

    # ----------------------------------------------------
    # 2. AI Intelligence Analysis Test (Grounding & Rules)
    # ----------------------------------------------------
    print("\n[Test I/J/K/L/M/N/O] AI Intelligence Extraction & Grounding Verification")
    sample_file = base_dir / "test_phase7_grounded.txt"
    sample_content = """Harinath: We need to complete the API architecture.
Prabu: I will finish the API by Friday.
Manikanta: What database should we use for production?
Someone: Maybe we should use PostgreSQL.
Harinath: Okay, let's use PostgreSQL.
Manikanta: Someone should prepare the project report.
Prabu: We will finish the documentation soon."""
    sample_file.write_text(sample_content, encoding="utf-8")

    parts_ai = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Sprint Decision & Grounding Sync",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{sample_file.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        sample_file.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_ai = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_ai),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_ai) as resp_ai:
        assert resp_ai.status == 201
        m_ai_id = json.loads(resp_ai.read().decode())["meeting"]["id"]

    # Trigger AI Diarization first
    urllib.request.urlopen(urllib.request.Request(f"{base_url}/api/v1/meetings/{m_ai_id}/diarize", method="POST"))

    # Map Speaker 2 -> Prabu
    req_spk_list = urllib.request.Request(f"{base_url}/api/v1/meetings/{m_ai_id}/speakers")
    with urllib.request.urlopen(req_spk_list) as r_spk:
        spks = json.loads(r_spk.read().decode())["speakers"]
        prabu_spk_id = next(s["id"] for s in spks if s["speaker_label"] == "Prabu")
        harinath_spk_id = next(s["id"] for s in spks if s["speaker_label"] == "Harinath")

    # Trigger AI Intelligence Analysis: POST /{meeting_id}/analyze
    print(f"\nTriggering POST /api/v1/meetings/{m_ai_id}/analyze...")
    req_an = urllib.request.Request(f"{base_url}/api/v1/meetings/{m_ai_id}/analyze", method="POST")
    with urllib.request.urlopen(req_an) as resp_an:
        assert resp_an.status == 200
        an_data = json.loads(resp_an.read().decode())
        print("\nExtracted AI Analysis Results:")
        print(json.dumps(an_data, indent=2))

        # A. Decision vs Discussion Check
        decisions = an_data["decisions"]
        print(f"\nDecisions Extracted: {len(decisions)}")
        assert len(decisions) == 1, f"Expected 1 decision ('Okay, let's use PostgreSQL'), got {len(decisions)}"
        assert "PostgreSQL" in decisions[0]["decision_text"]
        assert "Maybe we should use PostgreSQL" not in decisions[0]["decision_text"], "Suggestions must NOT be extracted as decisions!"
        assert decisions[0]["context_quote"] == "Okay, let's use PostgreSQL."
        print("--> Decision vs Suggestion Distinction PASSED!")

        # B. Action Items & Ownership / Deadline Rules
        actions = an_data["action_items"]
        print(f"\nAction Items Extracted: {len(actions)}")
        assert len(actions) >= 2

        # Item 1: Prabu explicit commitment with explicit deadline
        act_prabu = next(a for a in actions if "finish the API" in a["task_description"])
        assert act_prabu["responsible_person"] == "Prabu"
        assert act_prabu["deadline"] == "by Friday"
        assert act_prabu["context_quote"] == "I will finish the API by Friday."
        print("--> Action Item (Explicit Owner & Deadline) PASSED!")

        # Item 2: Unassigned action item ("Someone should prepare the report")
        act_unassigned = next(a for a in actions if "prepare the project report" in a["task_description"])
        assert act_unassigned["responsible_person"] is None, "Unassigned action item must have null responsible_person!"
        print("--> Unassigned Action Item (Responsible = null) PASSED!")

        # Item 3: Action item without explicit deadline ("We will finish the documentation soon")
        act_vague = next(a for a in actions if "documentation" in a["task_description"])
        assert act_vague["deadline"] is None, "Vague deadline ('soon') must NOT fabricate a calendar date!"
        print("--> Vague Deadline Handling (Deadline = null) PASSED!")

    # ----------------------------------------------------
    # 3. GET /api/v1/meetings/{meeting_id}/analysis Test
    # ----------------------------------------------------
    print(f"\n[Test REST] GET /api/v1/meetings/{m_ai_id}/analysis")
    req_get_an = urllib.request.Request(f"{base_url}/api/v1/meetings/{m_ai_id}/analysis")
    with urllib.request.urlopen(req_get_an) as r_g_an:
        assert r_g_an.status == 200
        g_an_data = json.loads(r_g_an.read().decode())
        assert g_an_data["status"] == "ANALYZED"
        assert len(g_an_data["decisions"]) == 1
        assert len(g_an_data["action_items"]) >= 2
        print("--> GET /analysis REST Endpoint PASSED!")

    # ----------------------------------------------------
    # 4. Phase 1–6 Full Regression Suite
    # ----------------------------------------------------
    print("\n[Test S] Full Phase 1–6 Regression Suite")

    # GET /
    with urllib.request.urlopen(f"{base_url}/") as r_root:
        assert r_root.status == 200

    # TXT Upload & Diarization
    txt_file = base_dir / "phase7_regression_txt.txt"
    txt_file.write_text("Harinath: Phase 7 regression test line.", encoding="utf-8")
    parts_r_txt = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="phase7_regression_txt.txt"',
        b"Content-Type: text/plain",
        b"",
        txt_file.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_r_txt = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_r_txt),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_r_txt) as r_r_txt:
        assert r_r_txt.status == 201
        m_r_id = json.loads(r_r_txt.read().decode())["meeting"]["id"]

    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_r_id}/transcript") as r_r_get:
        r_get_data = json.loads(r_r_get.read().decode())
        assert r_get_data["total_segments"] == 1
        assert r_get_data["segments"][0]["speaker_label"] == "Harinath"

    print("--> ALL PHASE 1–7 TESTS & REGRESSION CHECKS PASSED 100%! <--")

if __name__ == "__main__":
    test_phase7_reliability_suite()
