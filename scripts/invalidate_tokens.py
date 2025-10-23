#!/usr/bin/env python3
"""
Utility to safely expire all outstanding magic-link login tokens in an SQLite DB.

Usage:
  # dry-run (shows how many tokens would be expired)
  python3 scripts/invalidate_tokens.py --db backend/data.db --dry-run

  # perform with confirmation
  python3 scripts/invalidate_tokens.py --db backend/data.db --yes

This script will create a timestamped backup of the DB before making changes.
"""

import argparse
import shutil
import sqlite3
import os
from datetime import datetime


def backup_db(db_path: str) -> str:
    if not os.path.exists(db_path):
        raise SystemExit(f"DB path not found: {db_path}")
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dst = f"{db_path}.{ts}.bak"
    shutil.copy2(db_path, dst)
    print(f"Created backup: {dst}")
    return dst


def count_outstanding(conn) -> int:
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM login_tokens WHERE used=0')
    return cur.fetchone()[0]


def expire_tokens(conn) -> int:
    cur = conn.cursor()
    cur.execute('UPDATE login_tokens SET used=1 WHERE used=0')
    conn.commit()
    # Re-count to be sure
    return count_outstanding(conn)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', required=False, default=os.getenv('DB_PATH', 'backend/data.db'), help='Path to SQLite DB')
    p.add_argument('--dry-run', action='store_true', help='Do not modify DB, just report count')
    p.add_argument('--yes', action='store_true', help='Perform changes without interactive confirmation')
    args = p.parse_args()

    db = args.db
    if not os.path.exists(db):
        print(f"DB not found: {db}")
        raise SystemExit(1)

    conn = sqlite3.connect(db)
    try:
        outstanding = count_outstanding(conn)
        print(f"Outstanding (used=0) login_tokens: {outstanding}")
        if args.dry_run:
            print("Dry-run: no changes made.")
            return
        if outstanding == 0:
            print("Nothing to do.")
            return
        if not args.yes:
            ans = input("Expire all outstanding tokens and create DB backup? [y/N]: ")
            if ans.lower() not in ('y', 'yes'):
                print("Aborting.")
                return
        # create backup
        backup_db(db)
        # perform expire
        expire_tokens(conn)
        # verify
        outstanding_after = count_outstanding(conn)
        print(f"Outstanding after update: {outstanding_after}")
        print("Completed. You may want to restart the web app to clear sessions.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
