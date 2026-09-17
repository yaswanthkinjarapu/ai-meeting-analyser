import sys
import json
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.services.transcript_service import parse_txt_transcript

def test_speaker_parser_unit():
    sample_text = """Harinath: We need to complete the API.
Prabu: I will finish the API by Friday.
Manikanta: We still need to decide which database to use.
[00:01:10 - 00:01:25] Alice: Hello everyone.
Just an unlabelled commentary line."""

    segments = parse_txt_transcript(sample_text)
    print("\n--- Unit Test: Speaker Parser ---")
    for idx, s in enumerate(segments, 1):
        print(f"Seg {idx}: Speaker='{s['speaker_label']}' | Start={s['start_time']} | End={s['end_time']} | Text='{s['text']}'")

    assert len(segments) == 5, f"Expected 5 segments, got {len(segments)}"
    assert segments[0]["speaker_label"] == "Harinath"
    assert segments[0]["text"] == "We need to complete the API."
    assert segments[1]["speaker_label"] == "Prabu"
    assert segments[1]["text"] == "I will finish the API by Friday."
    assert segments[2]["speaker_label"] == "Manikanta"
    assert segments[2]["text"] == "We still need to decide which database to use."
    assert segments[3]["speaker_label"] == "Alice"
    assert segments[3]["start_time"] == 70.0
    assert segments[3]["end_time"] == 85.0
    assert segments[4]["speaker_label"] is None
    assert segments[4]["text"] == "Just an unlabelled commentary line."
    print("--> Unit Test: Speaker Parser PASSED!")

def test_api_integration():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    # 1. Create a test transcript with speaker labels matching prompt requirements
    sample_file = base_dir / "test_meeting_phase2.txt"
    sample_content = """Harinath: We need to complete the API.
Prabu: I will finish the API by Friday.
Manikanta: We still need to decide which database to use.
Someone: Maybe we should use PostgreSQL.
Okay, let's use PostgreSQL."""
    sample_file.write_text(sample_content, encoding="utf-8")

    # 2. Upload transcript file
    boundary = "----WebKitFormBoundaryPhase2Test"
    file_bytes = sample_file.read_bytes()

    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Phase 2 Architecture Discussion",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{sample_file.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        file_bytes,
        f"--{boundary}--".encode(),
        b""
    ]
    body = b"\r\n".join(parts)

    req = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    print("\n--- Integration Test: TXT Upload & Auto-Processing ---")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 201, f"Expected 201, got {resp.status}"
        data = json.loads(resp.read().decode())
        meeting = data["meeting"]
        meeting_id = meeting["id"]
        print(f"Uploaded Meeting ID: {meeting_id}")
        print(f"Status: {meeting['status']}")
        assert meeting["status"] == "TRANSCRIBED", f"Expected TRANSCRIBED, got {meeting['status']}"

    # 3. Test GET /api/v1/meetings/{meeting_id}/transcript endpoint
    print(f"\n--- Integration Test: GET /api/v1/meetings/{meeting_id}/transcript ---")
    req_get = urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_id}/transcript")
    with urllib.request.urlopen(req_get) as resp_get:
        assert resp_get.status == 200
        transcript_data = json.loads(resp_get.read().decode())
        print("Transcript Response:")
        print(json.dumps(transcript_data, indent=2))

        assert transcript_data["meeting_id"] == meeting_id
        assert transcript_data["status"] == "TRANSCRIBED"
        assert transcript_data["total_segments"] == 5

        segs = transcript_data["segments"]
        assert segs[0]["speaker_label"] == "Harinath"
        assert segs[1]["speaker_label"] == "Prabu"
        assert segs[2]["speaker_label"] == "Manikanta"
        assert segs[3]["speaker_label"] == "Someone"
        assert segs[4]["speaker_label"] is None

    # 4. Verify SQLite Database directly
    print("\n--- Integration Test: SQLite DB Segment Persistence ---")
    db_path = base_dir / "data" / "meeting.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, speaker_label, text FROM transcript_segments WHERE meeting_id = ?;", (meeting_id,))
            rows = cursor.fetchall()
            if rows:
                print(f"DB Rows found for meeting {meeting_id}: {len(rows)}")
                assert len(rows) == 5, f"Expected 5 DB rows, got {len(rows)}"
            cursor.execute("SELECT file_path FROM media_files WHERE meeting_id = ?;", (meeting_id,))
            mf_row = cursor.fetchone()
            if mf_row:
                db_file_path = mf_row[0]
                saved_file_path = Path(db_file_path)
                if not saved_file_path.is_absolute():
                    saved_file_path = base_dir / "backend" / saved_file_path
                if saved_file_path.exists():
                    assert saved_file_path.read_text(encoding="utf-8") == sample_content
        except sqlite3.OperationalError:
            pass
        conn.close()

    if "db_file_path" in locals():
        saved_file_path = Path(db_file_path)
        if not saved_file_path.is_absolute():
            saved_file_path = base_dir / "backend" / saved_file_path
        print(f"\nVerifying original file preserved at: {saved_file_path}")
        if saved_file_path.exists():
            assert saved_file_path.read_text(encoding="utf-8") == sample_content
            print("--> Original file preserved intact on disk!")

    # 6. Test Error Handling: Missing Meeting (404)
    print("\n--- Integration Test: Missing Meeting 404 ---")
    try:
        urllib.request.urlopen(f"{base_url}/api/v1/meetings/non-existent-id/transcript")
        assert False, "Should have thrown 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404
        print(f"Received expected 404 for missing meeting: {e.read().decode()}")

    print("\n--> ALL PHASE 2 TESTS PASSED SUCCESSFULLY! <--")

if __name__ == "__main__":
    test_speaker_parser_unit()
    test_api_integration()
