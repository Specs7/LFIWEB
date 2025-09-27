import os
import tempfile
import json
import pytest
import importlib.util

# Robust import: load backend.app from file so tests work regardless of PYTHONPATH/pytest behavior
spec = importlib.util.spec_from_file_location('backend.app', os.path.join(os.path.dirname(__file__), '..', 'app.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
flask_app = mod.app
init_db = mod.init_db
get_db = mod.get_db

@pytest.fixture
def client(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv('DB_PATH', str(db_file))
    # Import the app module from file with a unique name so it always picks up the env change
    import importlib.util
    app_path = os.path.join(os.path.dirname(__file__), '..', 'app.py')
    unique_name = f"backend_app_test_{tmp_path.name}"
    spec = importlib.util.spec_from_file_location(unique_name, app_path)
    mod_local = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod_local)
    # bind functions from the freshly loaded module
    flask_app_local = mod_local.app
    init_db_local = mod_local.init_db
    get_db_local = mod_local.get_db
    init_db_local()
    flask_app_local.config['TESTING'] = True
    client = flask_app_local.test_client()
    # attach helpers so tests can call get_db() if needed
    global flask_app, init_db, get_db
    flask_app = flask_app_local
    init_db = init_db_local
    get_db = get_db_local
    return client

def test_articles_crud(client):
    # create a user directly in DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (email, role) VALUES (?, ?)', ('t@test.local','admin'))
    conn.commit()
    cur.execute('SELECT id FROM users WHERE email=?', ('t@test.local',))
    uid = cur.fetchone()['id']
    conn.close()

    # simulate session by setting cookie via client
    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['csrf_token'] = 'test-csrf-token'

    # create
    r = client.post('/api/articles', json={'title':'t1','author':'a','content':'c','image':''}, headers={'X-CSRF-Token':'test-csrf-token'})
    assert r.status_code == 201
    data = r.get_json()
    aid = data['article']['id']

    # read
    r = client.get('/api/articles')
    assert r.status_code == 200
    data = r.get_json()
    assert len(data['articles']) >= 1

    # update
    r = client.put(f'/api/articles/{aid}', json={'title':'t1b','author':'a','content':'c2','image':''}, headers={'X-CSRF-Token':'test-csrf-token'})
    assert r.status_code == 200
    data = r.get_json()
    assert data['article']['title'] == 't1b'

    # delete
    r = client.delete(f'/api/articles/{aid}', headers={'X-CSRF-Token':'test-csrf-token'})
    assert r.status_code == 200

    r = client.get('/api/articles')
    data = r.get_json()
    assert all(a['id'] != aid for a in data['articles'])
