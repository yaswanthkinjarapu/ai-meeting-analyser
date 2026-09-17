import sqlite3
from pathlib import Path

def verify_all():
    base_dir = Path(__file__).resolve().parent
    
    # 1. Verify backend/uploads/ file exists
    upload_dir = base_dir / "backend" / "uploads"
    uploaded_files = list(upload_dir.glob("*"))
    print(f"Uploaded files in {upload_dir}: {[f.name for f in uploaded_files]}")
    assert len(uploaded_files) > 0, "No uploaded files found in backend/uploads/"
    
    # 2. Verify data/meeting.db exists
    db_path = base_dir / "data" / "meeting.db"
    print(f"SQLite DB path: {db_path} (Exists: {db_path.exists()})")
    assert db_path.exists(), "data/meeting.db does not exist!"
    
    # 3. Query SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, status, created_at FROM meetings;")
    meetings = cursor.fetchall()
    print("\nMeetings in SQLite DB:")
    for m in meetings:
        print(f"  ID: {m[0]} | Title: {m[1]} | Status: {m[2]} | CreatedAt: {m[3]}")
    assert len(meetings) > 0, "No meeting records found in SQLite DB!"
    
    cursor.execute("SELECT id, meeting_id, filename, file_type, file_extension, file_size_bytes, file_path FROM media_files;")
    files = cursor.fetchall()
    print("\nMediaFiles in SQLite DB:")
    for f in files:
        saved_path = Path(f[6])
        if not saved_path.is_absolute():
            saved_path = base_dir / "backend" / saved_path
            
        print(f"  File ID: {f[0]} | MeetingID: {f[1]} | Filename: {f[2]} | Type: {f[3]} | Ext: {f[4]} | Size: {f[5]} bytes")
        print(f"  Resolved Saved Path: {saved_path} (Exists: {saved_path.exists()})")
        assert saved_path.exists(), f"File at {saved_path} does not exist!"
        
    conn.close()
    print("\n--> ALL DATABASE & FILE SYSTEM CHECKS PASSED SUCCESSFULLY! <--")

if __name__ == "__main__":
    verify_all()
