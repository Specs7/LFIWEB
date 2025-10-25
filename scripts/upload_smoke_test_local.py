#!/usr/bin/env python3
"""Run smoke test using Flask test_client (no network).

This will:
- ensure an admin user exists in the DB
- start a Flask test client, set session to admin
- upload a tiny PNG to /api/photos
- verify the DB entry and that the file was saved on disk
"""
import os
import sqlite3
import secrets
from datetime import datetime
from io import BytesIO

# Add repo root to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend import app as flask_app


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


def make_sample_png_bytes():
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82'


def run():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data.db'))
    print('DB:', db_path)
    uid = ensure_admin(db_path)
    print('Admin id:', uid)

    client = flask_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['csrf_token'] = secrets.token_hex(16)
        csrf = sess['csrf_token']

    data = {
        'title': 'local smoke',
        'description': 'uploaded via test_client'
    }
    img = make_sample_png_bytes()
    data['file'] = (BytesIO(img), 'sample.png')

    # Flask test_client expects file tuples in 'data' and content_type multipart/form-data
    resp = client.post('/api/photos', data=data, content_type='multipart/form-data', headers={'X-CSRF-Token': csrf})
    print('POST /api/photos ->', resp.status_code)
    if resp.status_code not in (200,201):
        print('Failed', resp.get_data(as_text=True))
        return 1
    j = resp.get_json()
    filename = j.get('photo', {}).get('filename')
    if not filename:
        print('No filename returned')
        return 2
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'static', 'uploads', 'photos', filename))
    print('Expected saved file:', path)
    if not os.path.exists(path):
        print('File not found on disk')
        return 3
    # Check that /static route serves it
    r2 = client.get(f'/static/uploads/photos/{filename}')
    print('GET static ->', r2.status_code)
    if r2.status_code != 200:
        return 4
    print('Local smoke test passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
