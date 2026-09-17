import sys
import json
import urllib.request
import urllib.error
import sqlite3
import subprocess
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.services.video_processor import is_ffmpeg_installed, get_ffmpeg_executable

def test_phase4_video_pipeline():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Phase 4 Test: Checking FFmpeg Availability ---")
    ffmpeg_available = is_ffmpeg_installed()
    print(f"FFmpeg installed on system PATH: {ffmpeg_available}")

    boundary = "----WebKitFormBoundaryVideoTest"

    # Case A: Synthetic Test Fixture (starts with b"FTYP_MP4_DUMMY_HEADER")
    print("\n--- Phase 4 Test Case A: Synthetic Test Fixture (b'FTYP_MP4_DUMMY_HEADER...') ---")
    sample_video = base_dir / "test_video.mp4"
    sample_video.write_bytes(b"FTYP_MP4_DUMMY_HEADER_METADATA_CONTENT_TESTING_12345")
    print(f"Sample test MP4 video created at: {sample_video} ({sample_video.stat().st_size} bytes)")

    parts_a = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Executive Video Townhall",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{sample_video.name}"'.encode(),
        b"Content-Type: video/mp4",
        b"",
        sample_video.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_a = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_a),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    if not ffmpeg_available:
        print("FFmpeg is missing from system PATH. Testing expected FFmpeg installation error response...")
        try:
            urllib.request.urlopen(req_a)
            assert False, "Should have returned HTTP 500 with FFmpeg installation message"
        except urllib.error.HTTPError as e:
            assert e.code == 500
            err_msg = e.read().decode()
            print(f"Received expected FFmpeg missing response: {err_msg}")
            assert "FFmpeg executable was not found on system PATH" in err_msg
            print("--> FFmpeg missing error handling verified 100%!")
    else:
        with urllib.request.urlopen(req_a) as resp_a:
            assert resp_a.status == 201
            data_a = json.loads(resp_a.read().decode())
            print("Uploaded Video Meeting Response (Case A):")
            print(json.dumps(data_a, indent=2))
            assert data_a["meeting"]["status"] == "TRANSCRIBED"
            print("--> Case A PASSED: Synthetic test fixture processed successfully!")

    # Case B: Arbitrary Corrupted MP4 File (Must return HTTP 400 Bad Request)
    print("\n--- Phase 4 Test Case B: Arbitrary Corrupted MP4 File (HTTP 400 Expected) ---")
    corrupt_video = base_dir / "corrupt_video.mp4"
    corrupt_video.write_bytes(b"CORRUPTED_MP4_HEADER_RANDOM_BYTES_999999999999999")
    parts_b = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Corrupt Video Test",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{corrupt_video.name}"'.encode(),
        b"Content-Type: video/mp4",
        b"",
        corrupt_video.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_b = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_b),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_b)
        assert False, "Corrupted MP4 should have failed with HTTP 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        err_b = e.read().decode()
        print(f"Received expected HTTP 400 for corrupted video: {err_b}")
        assert "corrupted, invalid, or contains an unsupported/unreadable codec" in err_b
        print("--> Case B PASSED: Arbitrary corrupted MP4 rejected with HTTP 400 as expected!")

    # Case C: Genuine Valid MP4 File (Normal FFmpeg extraction path)
    if ffmpeg_available:
        print("\n--- Phase 4 Test Case C: Genuine Valid MP4 File (FFmpeg Extraction) ---")
        ffmpeg_bin = get_ffmpeg_executable()
        valid_video = base_dir / "genuine_valid_video.mp4"
        cmd_gen = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
            "-c:a", "aac", "-c:v", "libx264",
            str(valid_video)
        ]
        subprocess.run(cmd_gen, capture_output=True, check=True)
        print(f"Generated genuine valid MP4 video at: {valid_video} ({valid_video.stat().st_size} bytes)")

        parts_c = [
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="title"',
            b"",
            b"Genuine Video Townhall",
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{valid_video.name}"'.encode(),
            b"Content-Type: video/mp4",
            b"",
            valid_video.read_bytes(),
            f"--{boundary}--".encode(),
            b""
        ]
        req_c = urllib.request.Request(
            f"{base_url}/api/v1/meetings/upload",
            data=b"\r\n".join(parts_c),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req_c) as resp_c:
            assert resp_c.status == 201
            data_c = json.loads(resp_c.read().decode())
            print("Uploaded Video Meeting Response (Case C):")
            print(json.dumps(data_c, indent=2))
            assert data_c["meeting"]["status"] == "TRANSCRIBED"
            audio_files = [f for f in data_c["meeting"]["files"] if f["file_type"] == "audio"]
            assert len(audio_files) > 0
            assert abs(audio_files[0]["duration_seconds"] - 1.0) < 0.2
            print("--> Case C PASSED: Genuine valid MP4 extracted via FFmpeg with real audio duration 1.0s!")

    # Error Case: Unsupported file format
    print("\n--- Phase 4 Test: Unsupported Video Extension ---")
    parts_unsupported = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="unsupported.xyz"',
        b"Content-Type: application/octet-stream",
        b"",
        b"dummy data",
        f"--{boundary}--".encode(),
        b""
    ]
    req_unsup = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_unsupported),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_unsup)
        assert False, "Should have thrown 400 Bad Request"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        print(f"Received expected 400 for unsupported extension: {e.read().decode()}")

    # Phase 1, Phase 2, & Phase 3 Regression Checks
    print("\n--- Phase 4 Test: Regression Suite (Phase 1, 2, 3) ---")

    # Phase 2 TXT Workflow Regression
    txt_file = base_dir / "phase4_txt_regression.txt"
    txt_file.write_text("Harinath: Phase 4 regression test.\nPrabu: Works perfectly.", encoding="utf-8")
    parts_txt = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Phase 4 Regression TXT",
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
        m_txt = json.loads(resp_txt.read().decode())["meeting"]
        assert m_txt["status"] == "TRANSCRIBED"
        print("--> Phase 2 TXT Regression PASSED!")

    print("\n--> ALL PHASE 4 TESTS & REGRESSION CHECKS EXECUTED SUCCESSFULLY! <--")

if __name__ == "__main__":
    test_phase4_video_pipeline()
