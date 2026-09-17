import sys
import json
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

def test_phase9_search():
    base_url = "http://127.0.0.1:8000"

    print("\n--- Test: Meeting Search ---")
    query = "PostgreSQL"
    with urllib.request.urlopen(f"{base_url}/api/v1/meetings/search?q={query}") as resp:
        assert resp.status == 200
        results = json.loads(resp.read().decode())
        assert isinstance(results, list)
        print(f"Search query '{query}' returned {len(results)} matching meetings.")

    print("--> Meeting Search PASSED 100%!")

if __name__ == "__main__":
    test_phase9_search()
