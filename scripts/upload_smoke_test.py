#!/usr/bin/env python3
"""Smoke test: create admin user, obtain session via magic-token, upload an image and verify it's served.

Usage: python scripts/upload_smoke_test.py --host http://127.0.0.1:5000
"""
import argparse
import os
import sqlite3
import secrets
import hashlib
import time
from datetime import datetime, timedelta

import requests


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def ensure_admin(db_path, email='smoketest@example.com'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL DEFAULT "editor", created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    cur.execute('SELECT id FROM users WHERE email=?', (email,))
    row = cur.fetchone()
    if row:
        uid = row[0]
        cur.execute('UPDATE users SET role=? WHERE id=?', ('admin', uid))
        conn.commit()
    else:
        cur.execute('INSERT INTO users (email, role, created_at) VALUES (?,?,?)', (email, 'admin', datetime.utcnow().isoformat()))
        conn.commit()
        uid = cur.lastrowid
    conn.close()
    return uid


def insert_token(db_path, uid, token):
    th = hash_token(token)
    expires = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS login_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, token_hash TEXT NOT NULL, expires_at DATETIME NOT NULL, used INTEGER NOT NULL DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, ip TEXT, user_agent TEXT)')
    conn.commit()
    cur.execute('INSERT INTO login_tokens (user_id, token_hash, expires_at, used, created_at) VALUES (?,?,?,?,?)', (uid, th, expires, 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def make_sample_image(path):
    # Create a tiny 1x1 PNG
    png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82'
    with open(path, 'wb') as f:
        f.write(png)


def run(host):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data.db')
    db_path = os.path.abspath(db_path)
    print('Using DB:', db_path)
    uid = ensure_admin(db_path)
    print('Admin user id:', uid)
    token = secrets.token_urlsafe(32)
    insert_token(db_path, uid, token)
    sess = requests.Session()
    consume_url = f"{host.rstrip('/')}/auth/consume?token={token}&uid={uid}"
    print('Consuming token via', consume_url)
    r = sess.get(consume_url, allow_redirects=True, timeout=10)
    if r.status_code >= 400:
        print('Failed to consume token, status', r.status_code)
        return 2
    # Get admin manage page to extract CSRF
    r = sess.get(f"{host.rstrip('/')}/admin/manage", timeout=10)
    if r.status_code != 200:
        print('Failed to reach /admin/manage', r.status_code)
        return 3
    import re
    m = re.search(r"const\s+CSRF\s*=\s*'([0-9a-f]+)'", r.text)
    if not m:
        print('CSRF token not found in /admin/manage')
        return 4
    csrf = m.group(1)
    print('CSRF:', csrf)
    # Create sample image
    tmpdir = os.path.join(os.path.dirname(__file__), 'tmp')
    os.makedirs(tmpdir, exist_ok=True)
    imgpath = os.path.join(tmpdir, 'sample.png')
    make_sample_image(imgpath)
    files = {'file': ('sample.png', open(imgpath, 'rb'), 'image/png')}
    data = {'title': 'smoke test', 'description': 'uploaded by smoke test'}
    headers = {'X-CSRF-Token': csrf}
    print('Uploading photo...')
    r = sess.post(f"{host.rstrip('/')}/api/photos", files=files, data=data, headers=headers, timeout=30)
    if r.status_code not in (200,201):
        print('Upload failed', r.status_code, r.text)
        return 5
    j = r.json()
    filename = j.get('photo', {}).get('filename')
    print('Uploaded filename:', filename)
    if not filename:
        print('No filename returned')
        return 6
    # Check file accessible
    file_url = f"{host.rstrip('/')}/static/uploads/photos/{filename}"
    print('Checking file URL:', file_url)
    r = requests.get(file_url, timeout=10)
    if r.status_code != 200:
        print('Failed to fetch uploaded file, status', r.status_code)
        return 7
    print('Uploaded file accessible via HTTP')
    # Check API list
    r = requests.get(f"{host.rstrip('/')}/api/photos", timeout=10)
    if r.status_code != 200:
        print('/api/photos failed', r.status_code)
        return 8
    j = r.json()
    found = any(p.get('filename') == filename for p in j.get('photos', []))
    if not found:
        print('Uploaded photo not present in /api/photos response')
        return 9
    print('Smoke test passed')
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='http://127.0.0.1:5000')
    args = p.parse_args()
    rc = run(args.host)
    exit(rc)
