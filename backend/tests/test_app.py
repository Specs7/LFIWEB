import os
import sys
import io
import sqlite3
import importlib
from datetime import datetime

import pytest


def load_app(tmp_path):
    # Ensure a fresh import of the application module with its DB_PATH pointing to a temp DB
    db = tmp_path / "test.db"
    os.environ['DB_PATH'] = str(db)
    # remove cached module if present
    if 'backend.app' in sys.modules:
        del sys.modules['backend.app']
    import backend.app as appmod
    importlib.reload(appmod)
    appmod.init_db()
    return appmod


def test_init_db_creates_tables(tmp_path):
    appmod = load_app(tmp_path)
    conn = sqlite3.connect(os.environ['DB_PATH'])
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert {'users', 'login_tokens', 'articles', 'photos', 'videos'}.issubset(tables)
    conn.close()


def create_admin(client, appmod):
    conn = appmod.get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email, role, created_at) VALUES (?,?,?)", ("admin@example.test", 'admin', datetime.utcnow().isoformat()))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['csrf_token'] = 'testcsrf'
    return uid, 'testcsrf'


def test_articles_crud_smoke(tmp_path):
    appmod = load_app(tmp_path)
    client = appmod.app.test_client()
    uid, csrf = create_admin(client, appmod)

    # Create
    resp = client.post('/api/articles', json={'title': 'T1', 'author': 'A', 'content': 'C'}, headers={'X-CSRF-Token': csrf})
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'article' in data and data['article']['title'] == 'T1'
    aid = data['article']['id']

    # Update
    resp = client.put(f'/api/articles/{aid}', json={'title': 'T1b', 'author': 'A', 'content': 'C2'}, headers={'X-CSRF-Token': csrf})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['article']['title'] == 'T1b'

    # List
    resp = client.get('/api/articles')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'articles' in data and any(a['id'] == aid for a in data['articles'])

    # Delete
    resp = client.delete(f'/api/articles/{aid}', headers={'X-CSRF-Token': csrf})
    assert resp.status_code == 200


def test_photo_upload_and_delete(tmp_path):
    appmod = load_app(tmp_path)
    client = appmod.app.test_client()
    uid, csrf = create_admin(client, appmod)

    # Upload a fake image file (extension .jpg is allowed)
    data = {
        'title': 'Pic1',
        'description': 'desc1',
        'file': (io.BytesIO(b'fakejpegbytes'), 'test.jpg')
    }
    resp = client.post('/api/photos', data=data, headers={'X-CSRF-Token': csrf}, content_type='multipart/form-data')
    assert resp.status_code == 201
    j = resp.get_json()
    assert 'photo' in j
    pid = j['photo']['id']
    fname = j['photo']['filename']

    # Ensure file exists on disk
    p = os.path.join(os.environ['DB_PATH']).replace('test.db', '')
    # file is saved under backend/static/uploads/photos; check via app constants
    saved_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'photos')
    # Normalize path and check file presence
    saved_path = os.path.abspath(saved_path)
    files = os.listdir(saved_path)
    assert any(fname in f for f in files)

    # Delete
    resp = client.delete(f'/api/photos/{pid}', headers={'X-CSRF-Token': csrf})
    assert resp.status_code == 200

    # Confirm DB row removed
    conn = appmod.get_db()
    cur = conn.cursor()
    cur.execute('SELECT id FROM photos WHERE id=?', (pid,))
    assert cur.fetchone() is None
    conn.close()
