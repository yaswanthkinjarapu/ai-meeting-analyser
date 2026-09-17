import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_meeting_details():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: Meeting Details & Transcript ---")
    # Upload sample text meeting first
    txt_path = base_dir / "test_details.txt"
    txt_path.write_text("Harinath: Detailed meeting for testing details view.", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Details"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Details Test Meeting",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{txt_path.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        txt_path.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        m = json.loads(resp.read().decode())["meeting"]
        m_id = m["id"]

    # Retrieve details
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_id}") as resp_d:
        assert resp_d.status == 200
        det = json.loads(resp_d.read().decode())
        assert det["id"] == m_id

    # Retrieve transcript
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_id}/transcript") as resp_t:
        assert resp_t.status == 200
        t_data = json.loads(resp_t.read().decode())
        assert t_data["total_segments"] == 1

    print("--> Meeting Details & Transcript PASSED 100%!")

if __name__ == "__main__":
    test_phase9_meeting_details()
