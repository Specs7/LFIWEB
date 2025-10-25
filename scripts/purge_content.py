#!/usr/bin/env python3
"""Purge articles/photos/videos and uploaded files safely.

Usage:
  scripts/purge_content.py [--db PATH] [--backup] [--dry-run] [--yes]

- By default the script uses DB_PATH env var or ./data.db
- With --backup it will copy the DB and tar the uploads directory before deleting.
- With --dry-run it will only show what would be done.
- With --yes it will skip the interactive confirmation (use with care).

This script is destructive. Make sure you have a backup and that you run it
from the project root (repo root).
"""
import argparse
import os
import shutil
import sqlite3
import tarfile
from datetime import datetime


def now_ts():
    return datetime.utcnow().strftime('%Y%m%d_%H%M%S')


def resolve_db(path_arg: str):
    if path_arg:
        return path_arg
    env = os.getenv('DB_PATH')
    if env:
        return env
    # default to data.db in repo root
    return os.path.abspath(os.path.join(os.getcwd(), 'data.db'))


def backup_db(db_path: str):
    ts = now_ts()
    dest = f"{db_path}.bak.{ts}"
    print(f"Backing up DB: {db_path} -> {dest}")
    shutil.copy2(db_path, dest)
    return dest


def backup_uploads(uploads_dir: str):
    if not os.path.exists(uploads_dir):
        print(f"Uploads directory not found: {uploads_dir} (skipping)")
        return None
    ts = now_ts()
    dest = os.path.abspath(f"uploads-backup-{ts}.tgz")
    print(f"Archiving uploads: {uploads_dir} -> {dest}")
    with tarfile.open(dest, 'w:gz') as tf:
        # add the uploads dir contents without absolute path
        tf.add(uploads_dir, arcname=os.path.basename(uploads_dir))
    return dest


def counts(db_path: str):
    if not os.path.exists(db_path):
        return {'articles': 0, 'photos': 0, 'videos': 0}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    res = {}
    for t in ('articles', 'photos', 'videos'):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            res[t] = cur.fetchone()[0]
        except Exception:
            res[t] = 0
    conn.close()
    return res


def purge_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print("Deleting rows from tables: articles, photos, videos")
    cur.execute('BEGIN')
    cur.execute('DELETE FROM articles')
    cur.execute('DELETE FROM photos')
    cur.execute('DELETE FROM videos')
    conn.commit()
    try:
        cur.execute('VACUUM')
    except Exception:
        pass
    conn.close()


def move_uploads(uploads_dir: str):
    ts = now_ts()
    moved = []
    for sub in ('photos', 'videos'):
        src = os.path.join(uploads_dir, sub)
        if not os.path.exists(src):
            print(f"No directory: {src} (skipping)")
            continue
        dest = f"{src}_removed_{ts}"
        print(f"Moving {src} -> {dest}")
        shutil.move(src, dest)
        moved.append((src, dest))
        # recreate an empty folder for the app
        os.makedirs(src, exist_ok=True)
    return moved


def parse_args():
    p = argparse.ArgumentParser(description='Purge site content (articles/photos/videos and uploaded files)')
    p.add_argument('--db', help='Path to sqlite DB')
    p.add_argument('--backup', action='store_true', help='Create backups before purging')
    p.add_argument('--dry-run', action='store_true', help='Only show what would be done')
    p.add_argument('--yes', action='store_true', help='Answer yes to prompts')
    return p.parse_args()


def main():
    args = parse_args()
    db_path = resolve_db(args.db)
    uploads_dir = os.path.abspath(os.path.join(os.getcwd(), 'backend', 'static', 'uploads'))

    print('DB path:', db_path)
    print('Uploads dir:', uploads_dir)

    if not os.path.exists(db_path):
        print(f'Error: DB not found at {db_path}')
        return 2

    before = counts(db_path)
    print('Current counts:')
    for k, v in before.items():
        print(f'  {k}: {v}')

    if args.dry_run:
        print('\nDry-run mode, nothing changed.')
        return 0

    if args.backup:
        try:
            dbbak = backup_db(db_path)
            upbak = backup_uploads(uploads_dir)
            print('Backups created:', dbbak, upbak)
        except Exception as e:
            print('Backup failed:', e)
            return 3

    if not args.yes:
        confirm = input('Proceed to permanently delete content? Type YES to continue: ').strip()
        if confirm != 'YES':
            print('Aborted by user.')
            return 1

    try:
        purge_db(db_path)
    except Exception as e:
        print('Failed to purge DB:', e)
        return 4

    try:
        moved = move_uploads(uploads_dir)
    except Exception as e:
        print('Failed to move uploads:', e)
        return 5

    after = counts(db_path)
    print('After purge counts:')
    for k, v in after.items():
        print(f'  {k}: {v}')

    print('\nPurge completed. Uploads moved:' if moved else '\nPurge completed. No uploads moved.')
    for src, dest in moved:
        print(f'  {src} -> {dest}')

    print('\nNext: verify endpoints /api/articles /api/photos /api/videos and check that static uploads are empty.')
    return 0


if __name__ == '__main__':
    exit(main())
