import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_meeting_history():
    base_url = "http://127.0.0.1:8000"

    print("\n--- Test: Meeting History & Stats ---")
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/stats") as resp:
        assert resp.status == 200
        stats = json.loads(resp.read().decode())
        assert "total_meetings" in stats
        assert "open_action_items" in stats
        print(f"Meeting Stats retrieved: Total={stats['total_meetings']}, Open Actions={stats['open_action_items']}")

    with urllib.request.urlopen(f"{base_url}/api/v1/meetings") as resp_m:
        assert resp_m.status == 200
        meetings = json.loads(resp_m.read().decode())
        assert isinstance(meetings, list)
        print(f"Meeting History retrieved: Count={len(meetings)}")

    print("--> Meeting History & Stats PASSED 100%!")

if __name__ == "__main__":
    test_phase9_meeting_history()
