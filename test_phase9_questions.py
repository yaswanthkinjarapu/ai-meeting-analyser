import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_questions():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: Unresolved Questions Status Updates ---")
    txt_path = base_dir / "test_question_edit.txt"
    txt_path.write_text("Manikanta: What database should we use?", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Questions"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Question Edit Test",
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
        questions = an["unresolved_questions"]
        assert len(questions) > 0
        q_id = questions[0]["id"]
        orig_quote = questions[0]["context_quote"]

    patch_body = json.dumps({"status": "resolved"}).encode("utf-8")
    req_patch = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{m_id}/questions/{q_id}",
        data=patch_body,
        headers={"Content-Type": "application/json"},
        method="PATCH"
    )
    with urllib.request.urlopen(req_patch) as resp_p:
        assert resp_p.status == 200
        up_q = json.loads(resp_p.read().decode())
        assert up_q["status"] == "resolved"
        assert up_q["context_quote"] == orig_quote
        print("--> Unresolved Question Status Update PASSED!")

if __name__ == "__main__":
    test_phase9_questions()
