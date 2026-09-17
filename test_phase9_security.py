import sys
import json
import uuid
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_security():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent
    unique_suffix = uuid.uuid4().hex[:6]

    email_a = f"sec_a_{unique_suffix}@example.com"
    email_b = f"sec_b_{unique_suffix}@example.com"

    print("\n--- Test: Phase 9 Security & Ownership Isolation ---")
    # Register User A
    user_a_payload = json.dumps({"email": email_a, "password": "Password123!"}).encode("utf-8")
    req_reg_a = urllib.request.Request(f"{base_url}/api/v1/auth/register", data=user_a_payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req_reg_a) as r_a:
        token_a = json.loads(r_a.read().decode())["access_token"]

    # Register User B
    user_b_payload = json.dumps({"email": email_b, "password": "Password123!"}).encode("utf-8")
    req_reg_b = urllib.request.Request(f"{base_url}/api/v1/auth/register", data=user_b_payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req_reg_b) as r_b:
        token_b = json.loads(r_b.read().decode())["access_token"]

    # User A uploads meeting
    txt_path = base_dir / "sec_meeting.txt"
    txt_path.write_text("Harinath: User A private content.", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Sec"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"User A Private Meeting",
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
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Authorization": f"Bearer {token_a}"},
        method="POST"
    )
    with urllib.request.urlopen(req_up) as resp:
        m_id = json.loads(resp.read().decode())["meeting"]["id"]

    # User B attempts to export User A's meeting -> 403 Forbidden
    req_b_exp = urllib.request.Request(f"{base_url}/api/v1/meetings/{m_id}/export?format=markdown", headers={"Authorization": f"Bearer {token_b}"})
    try:
        with urllib.request.urlopen(req_b_exp) as r_be:
            assert False, "User B should not export User A's meeting!"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print("--> Export Ownership Protection PASSED!")

    # User B attempts to delete User A's meeting -> 403 Forbidden
    req_b_del = urllib.request.Request(f"{base_url}/api/v1/meetings/{m_id}", headers={"Authorization": f"Bearer {token_b}"}, method="DELETE")
    try:
        with urllib.request.urlopen(req_b_del) as r_bd:
            assert False, "User B should not delete User A's meeting!"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print("--> Delete Ownership Protection PASSED!")

    print("--> Phase 9 Security Suite PASSED 100%!")

if __name__ == "__main__":
    test_phase9_security()
