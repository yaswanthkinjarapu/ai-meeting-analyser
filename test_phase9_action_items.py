import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_action_items():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: Action Item Editing & Evidence Protection ---")
    txt_path = base_dir / "test_action_edit.txt"
    txt_path.write_text("Prabu: I will finish the documentation by Friday.", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Actions"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Action Item Edit Test",
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

    # Run AI analysis
    urllib.request.urlopen(urllib.request.Request(f"{base_url}/api/v1/meetings/{m_id}/analyze", method="POST"))

    # Get analysis to retrieve action item ID
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_id}/analysis") as resp_a:
        an = json.loads(resp_a.read().decode())
        actions = an["action_items"]
        assert len(actions) > 0
        ai = actions[0]
        ai_id = ai["id"]
        orig_quote = ai["context_quote"]

    # Edit action item status and notes
    patch_body = json.dumps({
        "status": "completed",
        "notes": "Documentation finished ahead of schedule."
    }).encode("utf-8")
    req_patch = urllib.request.Request(
        f"{base_url}/api/v1/meetings/{m_id}/action-items/{ai_id}",
        data=patch_body,
        headers={"Content-Type": "application/json"},
        method="PATCH"
    )
    with urllib.request.urlopen(req_patch) as resp_p:
        assert resp_p.status == 200
        updated_ai = json.loads(resp_p.read().decode())
        assert updated_ai["status"] == "completed"
        assert updated_ai["notes"] == "Documentation finished ahead of schedule."
        assert updated_ai["context_quote"] == orig_quote, "Original transcript evidence altered!"
        print("--> Action Item Edit & Evidence Protection PASSED!")

if __name__ == "__main__":
    test_phase9_action_items()
