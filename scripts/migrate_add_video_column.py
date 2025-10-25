#!/usr/bin/env python3
"""Migration helper: add 'video' TEXT column to articles table if missing.

Usage: python scripts/migrate_add_video_column.py --db /path/to/data.db
"""
import argparse
import sqlite3
import os


def has_column(conn, table, column):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


def run(db_path):
    if not os.path.exists(db_path):
        print('DB not found:', db_path)
        return 2
    conn = sqlite3.connect(db_path)
    try:
        if has_column(conn, 'articles', 'video'):
            print('Column video already exists in articles')
            return 0
        print('Adding column video to articles...')
        conn.execute("ALTER TABLE articles ADD COLUMN video TEXT")
        conn.commit()
        print('Done.')
        return 0
    except Exception as e:
        print('Migration failed:', e)
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--db', default=os.path.join(os.path.dirname(__file__), '..', 'data.db'))
    args = p.parse_args()
    raise SystemExit(run(args.db))
