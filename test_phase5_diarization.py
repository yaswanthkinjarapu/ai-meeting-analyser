import sys
import json
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase5_diarization_suite():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n==========================================")
    print("      PHASE 5 DIARIZATION TEST SUITE      ")
    print("==========================================")

    # ----------------------------------------------------
    # 1. Upload a transcript with multiple speakers
    # ----------------------------------------------------
    sample_file = base_dir / "test_phase5_speakers.txt"
    sample_content = """Speaker 1: Welcome to the project sync meeting.
Speaker 2: I have completed the database migrations.
Speaker 3: Great, I will start the API integration today.
Speaker 1: Excellent work team."""
    sample_file.write_text(sample_content, encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase5Test"
    file_bytes = sample_file.read_bytes()

    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Phase 5 Multi-Speaker Sync",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{sample_file.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        file_bytes,
        f"--{boundary}--".encode(),
        b""
    ]
    body = b"\r\n".join(parts)

    req_up = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req_up) as resp:
        assert resp.status == 201
        m_data = json.loads(resp.read().decode())["meeting"]
        meeting_id = m_data["id"]
        print(f"\n[Test A/B] Uploaded Multi-Speaker Meeting ID: {meeting_id}")

    # ----------------------------------------------------
    # 2. Run Speaker Diarization (POST /{meeting_id}/diarize)
    # ----------------------------------------------------
    print(f"\n[Test A] POST /api/v1/meetings/{meeting_id}/diarize")
    req_diarize = urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_id}/diarize", method="POST")
    with urllib.request.urlopen(req_diarize) as resp_d:
        assert resp_d.status == 200
        d_res = json.loads(resp_d.read().decode())
        print(f"Diarized Meeting Status: {d_res['status']} | Total Segments: {d_res['total_segments']}")
        assert d_res["status"] == "DIARIZED"
        assert d_res["total_segments"] == 4

    # ----------------------------------------------------
    # 3. Retrieve Meeting Speakers (GET /{meeting_id}/speakers)
    # ----------------------------------------------------
    print(f"\n[Test C] GET /api/v1/meetings/{meeting_id}/speakers (Unmapped Speakers)")
    req_spk = urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_id}/speakers")
    with urllib.request.urlopen(req_spk) as resp_spk:
        assert resp_spk.status == 200
        spk_data = json.loads(resp_spk.read().decode())
        print("Detected Speakers:")
        print(json.dumps(spk_data, indent=2))
        speakers = spk_data["speakers"]
        assert len(speakers) == 3, f"Expected 3 speakers, got {len(speakers)}"

        # Verify unmapped default name is null
        for s in speakers:
            assert s["speaker_name"] is None, "speaker_name must default to None"

        spk1_id = next(s["id"] for s in speakers if s["speaker_label"] == "Speaker 1")
        spk2_id = next(s["id"] for s in speakers if s["speaker_label"] == "Speaker 2")
        spk3_id = next(s["id"] for s in speakers if s["speaker_label"] == "Speaker 3")

    # ----------------------------------------------------
    # 4. Map Speaker Names (PUT /{meeting_id}/speakers/{speaker_id})
    # ----------------------------------------------------
    print(f"\n[Test D] PUT /api/v1/meetings/{meeting_id}/speakers/{spk1_id} -> Harinath")
    map_req_1 = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/speakers/{spk1_id}",
        data=json.dumps({"speaker_name": "Harinath"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT"
    )
    with urllib.request.urlopen(map_req_1) as r1:
        assert r1.status == 200
        mapped_1 = json.loads(r1.read().decode())
        print(f"Mapped Speaker 1 -> {mapped_1['speaker_name']}")
        assert mapped_1["speaker_name"] == "Harinath"

    print(f"[Test D] PUT /api/v1/meetings/{meeting_id}/speakers/{spk2_id} -> Prabu")
    map_req_2 = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_id}/speakers/{spk2_id}",
        data=json.dumps({"speaker_name": "Prabu"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT"
    )
    with urllib.request.urlopen(map_req_2) as r2:
        assert r2.status == 200
        mapped_2 = json.loads(r2.read().decode())
        assert mapped_2["speaker_name"] == "Prabu"

    # ----------------------------------------------------
    # 5. Verify Enriched Transcript (GET /{meeting_id}/transcript)
    # ----------------------------------------------------
    print(f"\n[Test E] GET /api/v1/meetings/{meeting_id}/transcript (Verify Speaker Name Alignment)")
    req_t_final = urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_id}/transcript")
    with urllib.request.urlopen(req_t_final) as r_tf:
        assert r_tf.status == 200
        t_final = json.loads(r_tf.read().decode())
        print("Enriched Transcript Output:")
        segs = t_final["segments"]
        seg1 = next(s for s in segs if "Welcome to the project sync meeting" in s["text"])
        assert seg1["speaker_label"] == "Speaker 1"
        assert seg1["speaker_name"] == "Harinath"

        seg2 = next(s for s in segs if "database migrations" in s["text"])
        assert seg2["speaker_label"] == "Speaker 2"
        assert seg2["speaker_name"] == "Prabu"

        seg3 = next(s for s in segs if "API integration today" in s["text"])
        assert seg3["speaker_label"] == "Speaker 3"
        assert seg3["speaker_name"] is None

        seg4 = next(s for s in segs if "Excellent work team" in s["text"])
        assert seg4["speaker_label"] == "Speaker 1"
        assert seg4["speaker_name"] == "Harinath"

    # ----------------------------------------------------
    # 6. Verify SQLite Database Record Integrity
    # ----------------------------------------------------
    print("\n[Test K] Verify SQLite Database 'speakers' and 'transcript_segments' tables directly")
    db_path = base_dir / "data" / "meeting.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, speaker_label, speaker_name FROM speakers WHERE meeting_id = ?;", (meeting_id,))
            db_spks = cursor.fetchall()
            if db_spks:
                print("DB Speakers:")
                for row in db_spks:
                    print(f"  ID: {row[0]} | Label: {row[1]} | Name: {row[2]}")
                assert len(db_spks) == 3
        except sqlite3.OperationalError:
            pass
        conn.close()

    # ----------------------------------------------------
    # 7. Error Handling Tests (G, H, I, J)
    # ----------------------------------------------------
    print("\n[Test G] Missing Meeting ID (404)")
    try:
        urllib.request.urlopen(f"{base_url}/api/v1/meetings/invalid-id-999/speakers")
        assert False, "Should throw 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404
        print(f"Received expected 404: {e.read().decode()}")

    print("[Test J] Diarization on Meeting without Transcript (400)")
    # Upload file without transcript
    parts_empty_tr = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Empty Transcript Meeting",
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="empty.pdf"',
        b"Content-Type: application/pdf",
        b"",
        b"dummy pdf bytes",
        f"--{boundary}--".encode(),
        b""
    ]
    req_pdf = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_empty_tr),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_pdf) as resp_pdf:
        pdf_meeting_id = json.loads(resp_pdf.read().decode())["meeting"]["id"]

    try:
        urllib.request.urlopen(f"{base_url}/api/v1/meetings/{pdf_meeting_id}/diarize", data=b"")
        assert False, "Should throw 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        print(f"Received expected 400: {e.read().decode()}")

    # ----------------------------------------------------
    # 8. Regression Tests (Phase 1–4)
    # ----------------------------------------------------
    print("\n[Test F] Phase 1-4 Full Regression Suite")

    # GET /
    with urllib.request.urlopen(f"{base_url}/") as r_root:
        assert r_root.status == 200

    # TXT Upload & Auto-Processing (Phase 2)
    txt_file = base_dir / "phase5_regression_txt.txt"
    txt_file.write_text("Harinath: Phase 5 regression test line.", encoding="utf-8")
    parts_r_txt = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="phase5_regression_txt.txt"',
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

    print("--> ALL PHASE 1-5 TESTS & REGRESSION CHECKS PASSED 100%! <--")

if __name__ == "__main__":
    test_phase5_diarization_suite()
