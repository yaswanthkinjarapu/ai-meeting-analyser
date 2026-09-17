import urllib.request
import json
from pathlib import Path

def run_upload_test():
    url = "http://127.0.0.1:8000/api/v1/meetings/upload"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    file_path = Path("sample_transcript.txt")
    file_content = file_path.read_bytes()
    
    parts = []
    # Title form field
    parts.append(f"--{boundary}".encode())
    parts.append(b'Content-Disposition: form-data; name="title"')
    parts.append(b"")
    parts.append(b"Sprint Planning Sync")
    
    # File field
    parts.append(f"--{boundary}".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode())
    parts.append(b"Content-Type: text/plain")
    parts.append(b"")
    parts.append(file_content)
    
    # End boundary
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    
    body = b"\r\n".join(parts)
    
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"HTTP Status: {resp.status}")
            data = json.loads(resp.read().decode())
            print("Response Payload:")
            print(json.dumps(data, indent=2))
            return data
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode())
        raise

if __name__ == "__main__":
    run_upload_test()
