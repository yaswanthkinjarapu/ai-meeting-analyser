import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_export():
    base_url = "http://127.0.0.1:8000"
    base_dir = Path(__file__).resolve().parent

    print("\n--- Test: Report Export (Markdown & JSON) ---")
    txt_path = base_dir / "test_export.txt"
    txt_path.write_text("Harinath: We need to complete the API. Prabu: I will finish the API by Friday.", encoding="utf-8")

    boundary = "----WebKitFormBoundaryPhase9Export"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="title"',
        b"",
        b"Export Test Meeting",
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

    # Export Markdown
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_id}/export?format=markdown") as r_md:
        assert r_md.status == 200
        md_text = r_md.read().decode("utf-8")
        assert "# Meeting Intelligence Report" in md_text
        print("--> Markdown Export PASSED!")

    # Export JSON
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/{m_id}/export?format=json") as r_js:
        assert r_js.status == 200
        js_data = json.loads(r_js.read().decode("utf-8"))
        assert "meeting" in js_data
        assert "decisions" in js_data
        print("--> JSON Export PASSED!")

if __name__ == "__main__":
    test_phase9_export()
