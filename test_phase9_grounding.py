import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_grounding():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: AI Grounding & Strict Rules ---")
    txt_path = base_dir / "test_grounding.txt"
    txt_content = """Someone: Maybe we should use PostgreSQL.
Harinath: Okay, let's use PostgreSQL.
Prabu: I will finish the API by Friday.
Manikanta: Someone should prepare the project report."""
    txt_path.write_text(txt_content, encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Grounding"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Grounding Test Meeting",
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
        actions = an["action_items"]

        # Rule 1: Suggestions excluded from decisions
        assert len(decisions) == 1
        assert decisions[0]["decision_text"] == "Okay, let's use PostgreSQL."

        # Rule 2: Unassigned responsible_person is None
        unassigned_act = next(a for a in actions if "project report" in a["task_description"])
        assert unassigned_act["responsible_person"] is None, "Fabricated responsible person!"

        # Rule 3: Explicit deadline
        explicit_act = next(a for a in actions if "finish the API" in a["task_description"])
        assert explicit_act["deadline"] == "by Friday"

        print("--> AI Grounding Rules & Verification PASSED 100%!")

if __name__ == "__main__":
    test_phase9_grounding()
