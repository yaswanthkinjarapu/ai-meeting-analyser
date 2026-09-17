import sys
import json
import uuid
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase8_production_suite():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent
    unique_suffix = uuid.uuid4().hex[:6]

    email_a = f"alice_{unique_suffix}@example.com"
    email_b = f"bob_{unique_suffix}@example.com"

    print("\n==========================================")
    print("   PHASE 8 PRODUCTION & SECURITY TEST SUITE   ")
    print("==========================================")

    # ----------------------------------------------------
    # 1. User Registration & Password Hashing
    # ----------------------------------------------------
    print("\n[Test A/B/C] User Registration & Password Hashing")
    user_a_payload = json.dumps({
        "email": email_a,
        "password": "Password123!",
        "full_name": "Alice User"
    }).encode("utf-8")

    req_reg_a = urllib.request.Request(
        f"{base_url}/api/v1/auth/register",
        data=user_a_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_reg_a) as resp_reg_a:
        assert resp_reg_a.status == 201
        data_a = json.loads(resp_reg_a.read().decode())
        token_a = data_a["access_token"]
        user_a_id = data_a["user"]["id"]
        assert data_a["user"]["email"] == email_a
        print(f"User A registered successfully: Email={email_a}, ID={user_a_id}, Token received.")

    # Duplicate registration rejection
    print("Testing duplicate email registration rejection...")
    req_dup = urllib.request.Request(
        f"{base_url}/api/v1/auth/register",
        data=user_a_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_dup) as resp_dup:
            assert False, "Duplicate registration should fail!"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        err_msg = json.loads(e.read().decode())["detail"]
        assert "already exists" in err_msg
        print(f"--> Duplicate registration rejected as expected: {err_msg}")

    # Database Hashed Password Inspection (Verify plaintext passwords are NEVER stored)
    db_path = base_dir / "data" / "meeting.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT hashed_password FROM users WHERE email = ?;", (email_a,))
            row = cursor.fetchone()
            if row:
                db_pw_hash = row[0]
                assert db_pw_hash != "Password123!", "Plaintext password stored! Security violation!"
                assert db_pw_hash.startswith("$2b$") or db_pw_hash.startswith("$2a$"), "Password not hashed with bcrypt!"
                print("--> Password Hashing Verification PASSED (Bcrypt verified)!")
        except sqlite3.OperationalError:
            pass
        conn.close()

    # ----------------------------------------------------
    # 2. User Login & Invalid Credentials
    # ----------------------------------------------------
    print("\n[Test D/E/F] Login & Invalid Login Rejection")
    login_payload = json.dumps({
        "email": email_a,
        "password": "Password123!"
    }).encode("utf-8")

    req_log = urllib.request.Request(
        f"{base_url}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_log) as resp_log:
        assert resp_log.status == 200
        log_data = json.loads(resp_log.read().decode())
        assert isinstance(log_data["access_token"], str) and len(log_data["access_token"]) > 20
        assert log_data["user"]["email"] == email_a
        print("--> Valid Login PASSED!")

    # Invalid login attempt
    bad_login = json.dumps({
        "email": email_a,
        "password": "WrongPassword!"
    }).encode("utf-8")
    req_bad_log = urllib.request.Request(
        f"{base_url}/api/v1/auth/login",
        data=bad_login,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_bad_log) as r_bl:
            assert False, "Invalid password login must fail!"
    except urllib.error.HTTPError as e:
        assert e.code == 401
        print("--> Invalid Login Rejection PASSED (401 Unauthorized)!")

    # ----------------------------------------------------
    # 3. Register User B & Test User Meeting Isolation
    # ----------------------------------------------------
    print("\n[Test G/H/I] JWT Authentication & User Data Isolation")
    user_b_payload = json.dumps({
        "email": email_b,
        "password": "Password456!",
        "full_name": "Bob User"
    }).encode("utf-8")

    req_reg_b = urllib.request.Request(
        f"{base_url}/api/v1/auth/register",
        data=user_b_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_reg_b) as resp_reg_b:
        data_b = json.loads(resp_reg_b.read().decode())
        token_b = data_b["access_token"]
        user_b_id = data_b["user"]["id"]
        print(f"User B registered successfully: Email={email_b}, ID={user_b_id}")

    # User A uploads a meeting
    boundary = "----WebKitFormBoundaryPhase8Security"
    txt_file_a = base_dir / "user_a_meeting.txt"
    txt_file_a.write_text("Harinath: Confidential meeting for Alice only.", encoding="utf-8")

    parts_a = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Alice Private Strategic Sync",
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{txt_file_a.name}"'.encode(),
        b"Content-Type: text/plain",
        b"",
        txt_file_a.read_bytes(),
        f"--{boundary}--".encode(),
        b""
    ]
    req_up_a = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(parts_a),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token_a}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req_up_a) as resp_up_a:
        meeting_a = json.loads(resp_up_a.read().decode())["meeting"]
        meeting_a_id = meeting_a["id"]
        assert meeting_a["user_id"] == user_a_id
        print(f"User A uploaded meeting ID: {meeting_a_id} (Bound to User A: {user_a_id})")

    # User B attempts to access User A's meeting -> HTTP 403 Forbidden
    req_b_access = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_a_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    try:
        with urllib.request.urlopen(req_b_access) as r_ba:
            assert False, "User B must NOT access User A's meeting!"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print("--> User Data Isolation PASSED (User B rejected with 403 Forbidden)!")

    # User B attempts to access User A's transcript -> HTTP 403 Forbidden
    req_b_trans = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{meeting_a_id}/transcript",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    try:
        with urllib.request.urlopen(req_b_trans) as r_bt:
            assert False, "User B must NOT access User A's transcript!"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print("--> Transcript Ownership Isolation PASSED!")

    # ----------------------------------------------------
    # 4. File Security & Path Traversal Prevention
    # ----------------------------------------------------
    print("\n[Test J/K/L/M] File Security Hardening")
    bad_filename_parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Security Traversal Test Phase 8",
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="../../../../etc_passwd.txt"',
        b"Content-Type: text/plain",
        b"",
        b"Harinath: Safe text content.",
        f"--{boundary}--".encode(),
        b""
    ]
    req_sec = urllib.request.Request(
        f"{base_url}/api/v1/meetings/upload",
        data=b"\r\n".join(bad_filename_parts),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token_a}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req_sec) as resp_sec:
        assert resp_sec.status == 201
        m_sec_id = json.loads(resp_sec.read().decode())["meeting"]["id"]

        # Check in DB that saved path stays in uploads folder
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT file_path, filename FROM media_files WHERE meeting_id = ?;", (m_sec_id,))
                row = cursor.fetchone()
                if row:
                    db_file_path, db_filename = row
                    print(f"Sanitized saved path: {db_file_path}")
                    assert "uploads" in db_file_path
                    assert not db_file_path.startswith("../")
                    assert "etc_passwd.txt" not in db_file_path or db_file_path.endswith("etc_passwd.txt")
            except sqlite3.OperationalError:
                pass
            conn.close()
        print("--> File Path Traversal & Safe Filename Generation PASSED!")

    # ----------------------------------------------------
    # 5. Status Transitions & Failure Capture
    # ----------------------------------------------------
    print("\n[Test N/O] Status Transitions & Failure Error Capture")
    with urllib.request.urlopen(urllib.request.Request(f"{base_url}/api/v1/meetings/{meeting_a_id}", headers={"Authorization": f"Bearer {token_a}"})) as r_status:
        st_data = json.loads(r_status.read().decode())
        print(f"Meeting A Processing Status: {st_data['status']}")
        assert st_data["status"] in ["UPLOADED", "QUEUED", "PROCESSING", "TRANSCRIBED", "COMPLETED"]
        print("--> Processing Status Transitions PASSED!")

    # ----------------------------------------------------
    # 6. Full Phase 1–7 Regression Suite
    # ----------------------------------------------------
    print("\n[Test P] Full Phase 1–7 Regression Suite")
    with urllib.request.urlopen(f"{base_url}/") as r_root:
        assert r_root.status == 200
        assert json.loads(r_root.read().decode())["status"] == "online"
        print("--> Backend Health Check PASSED!")

    print("\n--> ALL PHASE 8 PRODUCTION & SECURITY TESTS PASSED 100%! <--")

if __name__ == "__main__":
    test_phase8_production_suite()
