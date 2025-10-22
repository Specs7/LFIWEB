#!/usr/bin/env python3
"""Quick smoke test runner for backend functionality.

This script initializes a temporary DB, exercises article CRUD and photo upload
(using the Flask test client), and prints pass/fail results. It avoids external
dependencies beyond what's already in the repo (Flask).
"""
import os
import tempfile
from io import BytesIO
from datetime import datetime

# Ensure package import path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in os.sys.path:
    os.sys.path.insert(0, ROOT)

import backend.app as appmod


def run():
    # point DB_PATH to a temp file
    td = tempfile.TemporaryDirectory(prefix='lfi_smoke_')
    dbpath = os.path.join(td.name, 'data.db')
    os.environ['DB_PATH'] = dbpath

    print('DB_PATH ->', dbpath)

    # import the backend.app module after DB_PATH is set
    import importlib
    appmod = importlib.import_module('backend.app')
    importlib.reload(appmod)
    appmod.init_db()
    print('init_db() completed')

    client = appmod.app.test_client()

    # Create an admin user directly in DB
    conn = appmod.get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (email, role, created_at) VALUES (?,?,?)', ('smoke@example.test', 'admin', datetime.utcnow().isoformat()))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    print('Created admin user id=', uid)

    # set session for admin
    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['csrf_token'] = 'smokecsrf'

    headers = {'X-CSRF-Token': 'smokecsrf'}

    # Articles: create
    r = client.post('/api/articles', json={'title': 'Smoke test', 'author': 'smoke', 'content': 'ok'}, headers=headers)
    print('POST /api/articles ->', r.status_code, r.get_json())
    assert r.status_code == 201
    aid = r.get_json()['article']['id']

    # Articles: update
    r = client.put(f'/api/articles/{aid}', json={'title': 'Smoke test v2', 'author': 'smoke', 'content': 'ok2'}, headers=headers)
    print('PUT /api/articles ->', r.status_code)
    assert r.status_code == 200

    # Articles: list
    r = client.get('/api/articles')
    print('GET /api/articles ->', r.status_code, r.get_json().get('total'))
    assert r.status_code == 200

    # Photo upload
    img = BytesIO(b'fakejpegdata')
    data = {
        'title': 'SmokePic',
        'description': 'desc',
        'file': (img, 's.jpg')
    }
    r = client.post('/api/photos', data=data, content_type='multipart/form-data', headers=headers)
    print('POST /api/photos ->', r.status_code, r.get_json())
    assert r.status_code == 201
    photo = r.get_json()['photo']
    fname = photo['filename']

    # Check file exists
    saved = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'photos', fname)
    print('Expect file at', saved)
    if os.path.exists(saved):
        print('File found on disk')
    else:
        print('File NOT found at expected path; listing uploads dir:')
        upldir = os.path.dirname(saved)
        try:
            print(os.listdir(upldir))
        except Exception as e:
            print('Could not list', upldir, e)
        raise SystemExit('Photo file missing')

    # Delete photo
    r = client.delete(f"/api/photos/{photo['id']}", headers=headers)
    print('DELETE /api/photos ->', r.status_code)
    assert r.status_code == 200

    print('\nSMOKE TESTS PASSED')


if __name__ == '__main__':
    run()
