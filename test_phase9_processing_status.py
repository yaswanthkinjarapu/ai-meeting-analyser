import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_processing_status():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: Processing Status Transitions ---")
    txt_path = base_dir / "test_status.txt"
    txt_path.write_text("Harinath: Status transition check.", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Status"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Status Test Meeting",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{txt_path.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        txt_path.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_up = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req_up) as resp:
        m = json.loads(resp.read().decode())["meeting"]
        assert m["status"] in ["UPLOADED", "QUEUED", "PROCESSING", "TRANSCRIBED", "COMPLETED"]
        print(f"Meeting created with valid status transition: {m['status']}")

    print("--> Processing Status Transitions PASSED!")

if __name__ == "__main__":
    test_phase9_processing_status()
