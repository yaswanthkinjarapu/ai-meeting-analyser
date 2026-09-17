import sys
import json
import wave
import struct
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def create_synthetic_wav(file_path: Path, duration_seconds: float = 2.0, sample_rate: int = 44100):
    """Generates a valid synthetic WAV audio file for testing."""
    num_samples = int(duration_seconds * sample_rate)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Generate 440 Hz sine wave frames
        import math
        frames = bytearray()
        for i in range(num_samples):
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            frames.extend(struct.pack("<h", value))
        wf.writeframes(frames)

def test_phase3_audio_pipeline():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    # 1. Create a synthetic test WAV audio file (2 seconds)
    audio_file = base_dir / "test_audio.wav"
    create_synthetic_wav(audio_file, duration_seconds=2.0)
    print(f"\n--- Phase 3 Test: Synthetic WAV created at {audio_file} ({audio_file.stat().st_size} bytes) ---")

    # 2. Test Audio Upload & Auto-Transcription
    print("\n--- Phase 3 Test: POST /api/v1/meetings/upload (WAV file) ---")
    boundary = "----WebKitFormBoundaryAudioTest"
    file_bytes = audio_file.read_bytes()

    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Weekly Audio Standup Sync",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{audio_file.name}"'.encode(),
        b"Content-Type: audio/wav",
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

    with urllib.request.urlopen(req) as resp:
        assert resp.status == 201, f"Expected 201, got {resp.status}"
        data = json.loads(resp.read().decode())
        meeting = data["meeting"]
        meeting_id = meeting["id"]
        print(f"Uploaded Meeting ID: {meeting_id}")
        print(f"Status: {meeting['status']}")
        assert meeting["status"] == "TRANSCRIBED", f"Expected TRANSCRIBED, got {meeting['status']}"

    # 3. Test GET /api/v1/meetings/{meeting_id}/transcript
    print(f"\n--- Phase 3 Test: GET /api/v1/meetings/{meeting_id}/transcript ---")
    req_get = urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_id}/transcript")
    with urllib.request.urlopen(req_get) as resp_get:
        assert resp_get.status == 200
        transcript_data = json.loads(resp_get.read().decode())
        print("Transcript Response:")
        print(json.dumps(transcript_data, indent=2))

        assert transcript_data["meeting_id"] == meeting_id
        assert transcript_data["status"] == "TRANSCRIBED"
        assert transcript_data["total_segments"] > 0
        for seg in transcript_data["segments"]:
            assert "speaker_label" in seg
            assert "text" in seg
            assert "start_time" in seg
            assert "end_time" in seg

    # 4. Verify SQLite Database Persistence & MediaFile Metadata
    print("\n--- Phase 3 Test: SQLite DB MediaFile Metadata Verification ---")
    db_path = base_dir / "data" / "meeting.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT filename, file_type, duration_seconds, language FROM media_files WHERE meeting_id = ?;", (meeting_id,))
            mf_row = cursor.fetchone()
            if mf_row:
                print(f"MediaFile in DB: Filename={mf_row[0]} | Type={mf_row[1]} | Duration={mf_row[2]}s | Language={mf_row[3]}")
                assert mf_row[1] == "audio"
                assert mf_row[2] is not None and mf_row[2] > 0
                assert mf_row[3] is not None
        except sqlite3.OperationalError:
            pass
        conn.close()

    # 5. Test Manual Transcribe Endpoint: POST /api/v1/meetings/{meeting_id}/transcribe
    print(f"\n--- Phase 3 Test: POST /api/v1/meetings/{meeting_id}/transcribe ---")
    req_tr = urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_id}/transcribe", method="POST")
    with urllib.request.urlopen(req_tr) as resp_tr:
        assert resp_tr.status == 200
        tr_data = json.loads(resp_tr.read().decode())
        assert tr_data["status"] == "TRANSCRIBED"
        assert tr_data["total_segments"] > 0
        print("Manual audio transcribe re-trigger successful!")

    # 6. Error Case: Empty Audio File (0 bytes)
    print("\n--- Phase 3 Test: Error Handling - Empty Audio (0 bytes) ---")
    empty_audio = base_dir / "empty_audio.wav"
    empty_audio.write_bytes(b"")

    parts_empty = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Empty Audio Meeting",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{empty_audio.name}"'.encode(),
        b"Content-Type: audio/wav",
        b"",
        b"",
        f"--{boundary}--".encode(),
        b""
    ]
    req_empty = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_empty),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_empty)
        assert False, "Should have thrown 400 Bad Request"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        print(f"Received expected 400 for empty audio: {e.read().decode()}")

    # 7. Regression Test: Verify Phase 2 TXT Workflow still works!
    print("\n--- Phase 3 Regression Test: Phase 2 TXT Workflow ---")
    txt_file = base_dir / "phase3_txt_regression.txt"
    txt_content = """Harinath: Phase 2 text workflow regression check.
Prabu: Everything works seamlessly."""
    txt_file.write_text(txt_content, encoding="utf-8")

    parts_txt = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Phase 2 Regression Check",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{txt_file.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        txt_file.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_txt = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_txt),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_txt) as resp_txt:
        assert resp_txt.status == 201
        data_txt = json.loads(resp_txt.read().decode())
        m_txt_id = data_txt["meeting"]["id"]
        assert data_txt["meeting"]["status"] == "TRANSCRIBED"

    req_txt_get = urllib.request.Request(f"{base_url}/api/v1/meetings/{m_txt_id}/transcript")
    with urllib.request.urlopen(req_txt_get) as resp_txt_get:
        txt_get_data = json.loads(resp_txt_get.read().decode())
        assert txt_get_data["total_segments"] == 2
        assert txt_get_data["segments"][0]["speaker_label"] == "Harinath"
        print("--> Phase 2 TXT Workflow Regression Check PASSED 100%!")

    print("\n--> ALL PHASE 3 TESTS & REGRESSION CHECKS PASSED SUCCESSFULLY! <--")

if __name__ == "__main__":
    test_phase3_audio_pipeline()
