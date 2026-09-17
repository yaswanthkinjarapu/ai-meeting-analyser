#!/usr/bin/env python3
"""
SQLite to PostgreSQL Production Migration Utility
--------------------------------------------------
Safely copies all application data from a source SQLite database (e.g. data/meeting.db)
to a target production PostgreSQL database.

Features:
- Preserves primary keys, UUIDs, foreign key references, and timestamps.
- Performs record count verification across all 21 schema tables.
- Non-destructive: leaves the original SQLite database untouched.

Usage:
    python scripts/migrate_sqlite_to_postgres.py --sqlite-path data/meeting.db --postgres-url postgresql+psycopg://user:password@localhost:5432/meeting_db
"""

import os
import sys
import argparse
from typing import Dict, Any, List

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.database import models
from app.database.session import Base

MODEL_ORDER = [
    models.User,
    models.Meeting,
    models.MediaFile,
    models.Speaker,
    models.TranscriptSegment,
    models.Decision,
    models.ActionItem,
    models.UnresolvedQuestion,
    models.MeetingSummary,
    models.Topic,
    models.TimelineEvent,
    models.RiskBlocker,
    models.Dependency,
    models.FollowUpSuggestion,
    models.LiveMeetingSession,
    models.LiveSessionEvent,
    models.CalendarEvent,
    models.EmailFollowup,
    models.FollowUpReminder,
    models.UserIntegration,
    models.UserSettings,
]

def migrate_data(sqlite_path: str, postgres_url: str):
    print("=" * 70)
    print("      SQLITE TO POSTGRESQL PRODUCTION DATA MIGRATION TOOL      ")
    print("=" * 70)

    if not os.path.exists(sqlite_path):
        print(f"❌ Error: Source SQLite database file '{sqlite_path}' does not exist.")
        sys.exit(1)

    sqlite_url = f"sqlite:///{os.path.abspath(sqlite_path)}"
    print(f"🔹 Source SQLite URL  : {sqlite_url}")
    print(f"🔹 Target Postgres URL: {postgres_url}")

    src_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    tgt_engine = create_engine(postgres_url, pool_pre_ping=True)

    # Ensure target tables exist
    print("\n[1/3] Creating schema tables on target PostgreSQL database...")
    Base.metadata.create_all(bind=tgt_engine)
    print("✅ Target tables verified.")

    SrcSession = sessionmaker(bind=src_engine)
    TgtSession = sessionmaker(bind=tgt_engine)

    src_db = SrcSession()
    tgt_db = TgtSession()

    stats: Dict[str, int] = {}

    try:
        print("\n[2/3] Transferring records across 21 schema tables...")
        for model in MODEL_ORDER:
            table_name = model.__tablename__
            records = src_db.query(model).all()
            stats[table_name] = len(records)

            if not records:
                print(f"  • {table_name:<25}: 0 records")
                continue

            for rec in records:
                # Inspect model columns to create detached dictionary
                inst_dict = {c.name: getattr(rec, c.name) for c in inspect(model).column_attrs}
                new_obj = model(**inst_dict)
                tgt_db.merge(new_obj)

            tgt_db.commit()
            print(f"  • {table_name:<25}: {len(records)} records migrated successfully.")

        print("\n[3/3] Verifying migration consistency...")
        print("=" * 70)
        print(f"{'Table Name':<30} | {'Source Count':<12} | {'Target Count':<12} | Status")
        print("-" * 70)

        all_matched = True
        for model in MODEL_ORDER:
            table_name = model.__tablename__
            src_cnt = src_db.query(model).count()
            tgt_cnt = tgt_db.query(model).count()
            status = "MATCH" if src_cnt == tgt_cnt else "MISMATCH"
            if src_cnt != tgt_cnt:
                all_matched = False
            print(f"{table_name:<30} | {src_cnt:<12} | {tgt_cnt:<12} | {status}")

        print("=" * 70)

        if all_matched:
            print("\n✨ SQLITE TO POSTGRESQL MIGRATION PASSED 100%! All records transferred accurately.")
        else:
            print("\n⚠️ WARNING: Some table counts mismatched during verification. Please inspect target database.")

    except Exception as e:
        tgt_db.rollback()
        print(f"\n❌ Migration Failed with error: {str(e)}")
        sys.exit(1)
    finally:
        src_db.close()
        tgt_db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Meeting AI SQLite database to PostgreSQL.")
    parser.add_argument("--sqlite-path", default="data/meeting.db", help="Path to source SQLite database file")
    parser.add_argument("--postgres-url", required=True, help="Target PostgreSQL SQLAlchemy connection string")
    args = parser.parse_args()

    migrate_data(args.sqlite-path, args.postgres_url)
