import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_decisions():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: Decision Review Status Updates ---")
    txt_path = base_dir / "test_decision_edit.txt"
    txt_path.write_text("Harinath: Okay, let's use PostgreSQL.", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Decisions"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Decision Edit Test",
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
        m_id = json.loads(resp.read().decode())["meeting"]["id"]

    urllib.request.urlopen(urllib.request.Request(f"{base_url}/api/v1/meetings/{m_id}/analyze", method="POST"))

    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_id}/analysis") as resp_a:
        an = json.loads(resp_a.read().decode())
        decisions = an["decisions"]
        assert len(decisions) > 0
        d_id = decisions[0]["id"]
        orig_quote = decisions[0]["context_quote"]

    patch_body = json.dumps({"review_status": "needs_review"}).encode("utf-8")
    req_patch = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{m_id}/decisions/{d_id}",
        data=patch_body,
        headers={"Content-Type": "application/json"},
        method="PATCH"
    )
    with urllib.request.urlopen(req_patch) as resp_p:
        assert resp_p.status == 200
        up_d = json.loads(resp_p.read().decode())
        assert up_d["review_status"] == "needs_review"
        assert up_d["context_quote"] == orig_quote
        print("--> Decision Review Status Update PASSED!")

if __name__ == "__main__":
    test_phase9_decisions()
