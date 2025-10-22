"""Clean Flask app for LFIWEB.

Single-file Flask app implementing a stable base for articles, photos and videos.
This file is an atomic replacement for a previously corrupted file.
"""

import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    render_template,
    render_template_string,
    send_from_directory,
)
from werkzeug.utils import secure_filename

# Configuration
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, '..', 'data.db'))
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))

UPLOAD_BASE = os.path.join(BASE_DIR, 'static', 'uploads')
PHOTO_DIR = os.path.join(UPLOAD_BASE, 'photos')
VIDEO_DIR = os.path.join(UPLOAD_BASE, 'videos')
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

ALLOWED_IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_VIDEO_EXT = {'.mp4', '.webm', '.ogg', '.mov', '.mkv'}

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Upload/Quota configuration (bytes)
# These can be tuned via environment variables on PythonAnywhere
IMAGE_MAX_BYTES = int(os.getenv('IMAGE_MAX_BYTES', str(5 * 1024 * 1024)))  # 5 MB default
VIDEO_MAX_BYTES = int(os.getenv('VIDEO_MAX_BYTES', str(150 * 1024 * 1024)))  # 150 MB default
MAX_TOTAL_UPLOAD_BYTES = int(os.getenv('MAX_TOTAL_UPLOAD_BYTES', str(2 * 1024 * 1024 * 1024)))  # 2 GB default

# Prevent very large requests at the WSGI boundary (global cap)
app.config['MAX_CONTENT_LENGTH'] = MAX_TOTAL_UPLOAD_BYTES

# Simple in-memory rate limiter for demonstration.
# NOTE: This is process-local and not suitable for multi-process deployments;
# for production use Redis or another centralized store.
from collections import deque
import time
import smtplib
from email.message import EmailMessage

# rate-limiter settings
RL_WINDOW_SECONDS = int(os.getenv('RL_WINDOW_SECONDS', str(60 * 60)))  # 1 hour window by default
RL_MAX_REQUESTS = int(os.getenv('RL_MAX_REQUESTS', '5'))  # default 5 requests per window

# Map key -> deque[timestamp]
_rl_buckets = {}


def _rl_key_for_request():
    # Use IP address as rate-limit key; fall back to header if present
    return request.remote_addr or request.headers.get('X-Forwarded-For') or 'unknown'


def is_rate_limited(key: str) -> bool:
    now = time.time()
    dq = _rl_buckets.get(key)
    if dq is None:
        dq = deque()
        _rl_buckets[key] = dq
    # pop old
    while dq and dq[0] <= now - RL_WINDOW_SECONDS:
        dq.popleft()
    if len(dq) >= RL_MAX_REQUESTS:
        return True
    dq.append(now)
    return False


# Try to configure a Redis-backed rate limiter if REDIS_URL is provided.
REDIS_URL = os.getenv('REDIS_URL')
_redis = None
if REDIS_URL:
    try:
        import redis as _redislib
        _redis = _redislib.from_url(REDIS_URL)
    except Exception:
        app.logger.exception('Failed to initialize Redis client; falling back to in-memory rate limiter')


def is_rate_limited_redis(key: str) -> bool:
    """Use a Lua script to atomically prune, add, count and set expiry on a ZSET.

    Returns True if the request is rate-limited (count > RL_MAX_REQUESTS).
    The Lua script does:
      ZREMRANGEBYSCORE(key, 0, now - w)
      ZADD(key, now, member)
      local c = ZCARD(key)
      EXPIRE(key, w + 10)
      return c
    """
    if not _redis:
        return False
    now = int(time.time())
    w = RL_WINDOW_SECONDS
    rkey = f"rl:{key}"
    member = f"{now}-{secrets.token_hex(4)}"
    lua = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
    redis.call('ZADD', KEYS[1], ARGV[2], ARGV[3])
    local c = redis.call('ZCARD', KEYS[1])
    redis.call('EXPIRE', KEYS[1], ARGV[4])
    return c
    """
    try:
        # ARGV[1] = now - w, ARGV[2] = now, ARGV[3] = member, ARGV[4] = w + 10
        res = _redis.eval(lua, 1, rkey, now - w, now, member, w + 10)
        cnt = int(res)
        return cnt > RL_MAX_REQUESTS
    except Exception:
        app.logger.exception('Redis rate limiter failure; allowing request')
        return False


def check_rate_limit_for_request():
    key = _rl_key_for_request()
    # try redis first
    if _redis and is_rate_limited_redis(key):
        return True
    # fallback to in-memory
    return is_rate_limited(key)


# Site and SMTP configuration
SITE_URL = os.getenv('SITE_URL', 'http://localhost:5000')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT') or 0)
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', '1') not in ('0', 'false', 'False')
FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USER or f'no-reply@{urlparse(SITE_URL).hostname or "localhost"}')


def send_magic_link(email: str, user_id: int, token: str) -> bool:
    """Send the magic-link email. Returns True on success, False on failure.

    If SMTP_HOST is not configured, the function logs the link and returns True
    to allow non-email environments (dev/test) to function.
    """
    link = f"{SITE_URL.rstrip('/')}/auth/consume?token={token}&uid={user_id}"
    subject = 'Your login link'
    body = f"Click this link to sign in: {link}\n\nThis link expires in 2 hours." 
    # Read SMTP configuration at call time so tests can modify env vars after import
    smtp_host = os.getenv('SMTP_HOST')
    if not smtp_host:
        app.logger.info('SMTP not configured; magic link for %s: %s', email, link)
        return True
    smtp_port = int(os.getenv('SMTP_PORT') or 0)
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    smtp_use_tls = os.getenv('SMTP_USE_TLS', '1') not in ('0', 'false', 'False')
    from_email = os.getenv('FROM_EMAIL', smtp_user or f'no-reply@{urlparse(SITE_URL).hostname or "localhost"}')
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = email
        msg.set_content(body)
        port = smtp_port or 587
        server = smtplib.SMTP(smtp_host, port, timeout=10)
        if smtp_use_tls:
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        app.logger.info('Sent magic link to %s', email)
        return True
    except Exception:
        app.logger.exception('Failed to send magic link email')
        return False


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL UNIQUE,
      role TEXT NOT NULL DEFAULT 'editor',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS login_tokens (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      token_hash TEXT NOT NULL,
      expires_at DATETIME NOT NULL,
      used INTEGER NOT NULL DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      ip TEXT,
      user_agent TEXT,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS articles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT,
      content TEXT,
      image TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS photos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      filename TEXT NOT NULL,
      title TEXT,
      description TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS videos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      filename TEXT NOT NULL,
      title TEXT,
      description TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    conn.commit()
    conn.close()


def is_safe_url(url: str) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        return p.scheme in ('http', 'https') and bool(p.netloc)
    except Exception:
        return False


def _check_csrf() -> bool:
    if request.method in ('POST', 'PUT', 'DELETE'):
        header = request.headers.get('X-CSRF-Token')
        return header and header == session.get('csrf_token')
    return True


def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def save_upload(field_name: str, dest_dir: str):
    """Stream-save an uploaded file while enforcing per-file and total quotas.

    This function streams incoming file data to disk in chunks to avoid
    buffering large files in memory. It enforces per-file limits (based on
    extension) and a global uploads quota for the project.
    """
    if field_name not in request.files:
        return None, 'no file part'
    f = request.files[field_name]
    if not f or f.filename == '':
        return None, 'no selected file'
    filename = secure_filename(f.filename)
    if not filename:
        return None, 'invalid filename'
    ext = _ext(filename)
    if not ext:
        return None, 'missing extension'

    # Determine per-file limit by extension
    if ext in ALLOWED_IMAGE_EXT:
        per_file_limit = IMAGE_MAX_BYTES
    elif ext in ALLOWED_VIDEO_EXT:
        per_file_limit = VIDEO_MAX_BYTES
    else:
        return None, 'invalid file extension'

    name = secrets.token_hex(8) + ext
    target = os.path.join(dest_dir, name)

    # Stream-write the uploaded file and enforce per-file size
    try:
        total = 0
        # Ensure destination directory exists
        os.makedirs(dest_dir, exist_ok=True)
        with open(target, 'wb') as out:
            chunk = f.stream.read(8192)
            while chunk:
                out.write(chunk)
                total += len(chunk)
                if total > per_file_limit:
                    out.close()
                    try:
                        os.remove(target)
                    except Exception:
                        pass
                    return None, 'file too large'
                chunk = f.stream.read(8192)

        # Enforce a global uploads quota after successful save
        if get_total_upload_bytes() > MAX_TOTAL_UPLOAD_BYTES:
            try:
                os.remove(target)
            except Exception:
                pass
            return None, 'storage quota exceeded'

        return name, None
    except Exception as e:
        app.logger.exception('save_upload error: %s', e)
        try:
            if os.path.exists(target):
                os.remove(target)
        except Exception:
            pass
        return None, str(e)


def get_total_upload_bytes() -> int:
    """Return the total size in bytes of files under UPLOAD_BASE."""
    total = 0
    if not os.path.exists(UPLOAD_BASE):
        return 0
    for root, dirs, files in os.walk(UPLOAD_BASE):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except Exception:
                pass
    return total


@app.route('/')
def index():
    try:
        return render_template('lfi_municipal_site.html')
    except Exception:
        return render_template_string('<p>Frontend template missing.</p>'), 500


@app.route('/admin/request')
def show_request_form():
    return render_template('admin_request.html')


@app.route('/admin/manage')
def admin_manage():
    if not session.get('user_id'):
        return redirect(url_for('show_request_form'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    conn.close()
    if not user or user['role'] != 'admin':
        return "Access denied", 403
    csrf = session.get('csrf_token', '')
    # pass upload limits to client for pre-upload validation
    return render_template('admin_manage.html', uid=session.get('user_id'), csrf=csrf,
                           max_image=IMAGE_MAX_BYTES, max_video=VIDEO_MAX_BYTES)


@app.route('/admin/status')
def admin_status():
    """Return simple admin-facing JSON with Redis connection status and storage usage."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    conn.close()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    info = {'storage_bytes': get_total_upload_bytes()}
    if _redis:
        try:
            info['redis_ping'] = _redis.ping()
        except Exception as e:
            info['redis_error'] = str(e)
    else:
        info['redis'] = 'not configured'
    return jsonify(info), 200


@app.route('/api/me', methods=['GET'])
def api_me():
    if not session.get('user_id'):
        return jsonify({'user': None}), 200
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, email, role FROM users WHERE id=?', (session.get('user_id'),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'user': None}), 200
    return jsonify({'user': dict(row)}), 200


# Articles endpoints
@app.route('/api/articles', methods=['GET'])
def api_get_articles():
    q = (request.args.get('q') or '').strip()
    try:
        page = int(request.args.get('page') or '1')
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get('per_page') or '10')
        if per_page < 1 or per_page > 100:
            per_page = 10
    except ValueError:
        per_page = 10
    conn = get_db()
    cur = conn.cursor()
    params = []
    where = ''
    if q:
        where = "WHERE title LIKE ? OR content LIKE ?"
        like = f"%{q}%"
        params.extend([like, like])
    cur.execute(f"SELECT COUNT(*) FROM articles {where}", params)
    total = cur.fetchone()[0]
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    cur.execute(f"SELECT id, title, author, content, image, created_at FROM articles {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params)
    rows = cur.fetchall()
    articles = [dict(r) for r in rows]
    conn.close()
    return jsonify({'articles': articles, 'total': total, 'page': page, 'per_page': per_page}), 200


@app.route('/api/articles', methods=['POST'])
def api_create_article():
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    if not user or user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    author = (data.get('author') or '').strip()
    content = (data.get('content') or '').strip()
    image = (data.get('image') or '').strip()
    if not title:
        conn.close()
        return jsonify({'error': 'title required'}), 400
    if len(title) > 200 or len(author) > 100 or len(content) > 10000:
        conn.close()
        return jsonify({'error': 'Input too long'}), 400
    if image and not is_safe_url(image):
        conn.close()
        return jsonify({'error': 'Invalid image URL'}), 400
    cur.execute('INSERT INTO articles (title, author, content, image) VALUES (?,?,?,?)', (title, author, content, image))
    conn.commit()
    article_id = cur.lastrowid
    cur.execute('SELECT id, title, author, content, image, created_at FROM articles WHERE id=?', (article_id,))
    row = cur.fetchone()
    conn.close()
    return jsonify({'article': dict(row)}), 201


@app.route('/api/articles/<int:article_id>', methods=['PUT'])
def api_update_article(article_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    if not user or user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    author = (data.get('author') or '').strip()
    content = (data.get('content') or '').strip()
    image = (data.get('image') or '').strip()
    if not title:
        conn.close()
        return jsonify({'error': 'title required'}), 400
    if len(title) > 200 or len(author) > 100 or len(content) > 10000:
        conn.close()
        return jsonify({'error': 'Input too long'}), 400
    if image and not is_safe_url(image):
        conn.close()
        return jsonify({'error': 'Invalid image URL'}), 400
    cur.execute('UPDATE articles SET title=?, author=?, content=?, image=? WHERE id=?', (title, author, content, image, article_id))
    conn.commit()
    cur.execute('SELECT id, title, author, content, image, created_at FROM articles WHERE id=?', (article_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'article': dict(row)}), 200


@app.route('/api/articles/<int:article_id>', methods=['DELETE'])
def api_delete_article(article_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    if not user or user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    cur.execute('DELETE FROM articles WHERE id=?', (article_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'}), 200


# Photos endpoints
@app.route('/api/photos', methods=['GET'])
def photos_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, filename, title, description, created_at FROM photos ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return jsonify({'photos': [dict(r) for r in rows]}), 200


@app.route('/api/photos', methods=['POST'])
def photos_create():
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    if not user or user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    name, err = save_upload('file', PHOTO_DIR)
    if err:
        conn.close()
        return jsonify({'error': err}), 400
    if _ext(name) not in ALLOWED_IMAGE_EXT:
        try:
            os.remove(os.path.join(PHOTO_DIR, name))
        except Exception:
            pass
        conn.close()
        return jsonify({'error': 'Invalid image type'}), 400
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    cur.execute('INSERT INTO photos (filename, title, description, created_at) VALUES (?,?,?,?)', (name, title, description, datetime.utcnow().isoformat()))
    conn.commit()
    pid = cur.lastrowid
    cur.execute('SELECT id, filename, title, description, created_at FROM photos WHERE id=?', (pid,))
    row = cur.fetchone()
    conn.close()
    return jsonify({'photo': dict(row)}), 201


@app.route('/api/photos/<int:photo_id>', methods=['DELETE'])
def photos_delete(photo_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT filename FROM photos WHERE id=?', (photo_id,))
    r = cur.fetchone()
    if not r:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    fname = r['filename']
    cur.execute('DELETE FROM photos WHERE id=?', (photo_id,))
    conn.commit()
    conn.close()
    try:
        os.remove(os.path.join(PHOTO_DIR, fname))
    except Exception:
        pass
    return jsonify({'status': 'deleted'}), 200


@app.route('/static/uploads/photos/<path:filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)


# Videos endpoints
@app.route('/api/videos', methods=['GET'])
def videos_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, filename, title, description, created_at FROM videos ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return jsonify({'videos': [dict(r) for r in rows]}), 200


@app.route('/api/videos', methods=['POST'])
def videos_create():
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    if not user or user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    name, err = save_upload('file', VIDEO_DIR)
    if err:
        conn.close()
        return jsonify({'error': err}), 400
    if _ext(name) not in ALLOWED_VIDEO_EXT:
        try:
            os.remove(os.path.join(VIDEO_DIR, name))
        except Exception:
            pass
        conn.close()
        return jsonify({'error': 'Invalid video type'}), 400
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    cur.execute('INSERT INTO videos (filename, title, description, created_at) VALUES (?,?,?,?)', (name, title, description, datetime.utcnow().isoformat()))
    conn.commit()
    vid = cur.lastrowid
    cur.execute('SELECT id, filename, title, description, created_at FROM videos WHERE id=?', (vid,))
    row = cur.fetchone()
    conn.close()
    return jsonify({'video': dict(row)}), 201


@app.route('/api/videos/<int:video_id>', methods=['DELETE'])
def videos_delete(video_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT filename FROM videos WHERE id=?', (video_id,))
    r = cur.fetchone()
    if not r:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    fname = r['filename']
    cur.execute('DELETE FROM videos WHERE id=?', (video_id,))
    conn.commit()
    conn.close()
    try:
        os.remove(os.path.join(VIDEO_DIR, fname))
    except Exception:
        pass
    return jsonify({'status': 'deleted'}), 200


@app.route('/static/uploads/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('show_request_form'))




# Minimal auth endpoints (request token, consume token).
# These are intentionally minimal: in production wire up SMTP, SITE_URL env var, etc.


def gen_token():
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

@app.route('/auth/request-token', methods=['POST'])
def auth_request_token():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'status': 'ok'}), 200

    # Rate limit requests per IP/address
    if check_rate_limit_for_request():
        app.logger.warning('Rate limited request-token from %s', _rl_key_for_request())
        # Return OK to avoid leaking rate-limit state
        return jsonify({'status': 'ok'}), 200

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE email=?', (email,))
    user = cur.fetchone()
    if not user:
        # Create a default editor user to allow login links for demonstration.
        cur.execute('INSERT OR IGNORE INTO users (email, role, created_at) VALUES (?,?,?)', (email, 'editor', datetime.utcnow().isoformat()))
        conn.commit()
        cur.execute('SELECT id FROM users WHERE email=?', (email,))
        user = cur.fetchone()
    user_id = user['id']
    token = gen_token()
    th = hash_token(token)
    expires = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    cur.execute('INSERT INTO login_tokens (user_id, token_hash, expires_at, used, ip, user_agent) VALUES (?,?,?,?,?,?)', (user_id, th, expires, 0, request.remote_addr, request.headers.get('User-Agent')))
    conn.commit()
    conn.close()

    sent = send_magic_link(email, user_id, token)
    if not sent:
        app.logger.warning('Failed to send magic link to %s; token=%s', email, token)
    else:
        app.logger.info('Generated token for %s (id=%s) token=%s', email, user_id, token)
    # Always return OK to avoid enumerating emails
    return jsonify({'status': 'ok'}), 200


@app.route('/auth/consume', methods=['GET'])
def auth_consume():
    token = request.args.get('token')
    uid = request.args.get('uid')
    if not token or not uid:
        return redirect(url_for('show_request_form'))
    conn = get_db()
    cur = conn.cursor()
    th = hash_token(token)
    cur.execute('SELECT id, user_id, expires_at, used FROM login_tokens WHERE token_hash=?', (th,))
    row = cur.fetchone()
    if not row:
        return redirect(url_for('show_request_form'))
    if row['used']:
        return redirect(url_for('show_request_form'))
    # check expiry
    try:
        exp = datetime.fromisoformat(row['expires_at'])
        if datetime.utcnow() > exp:
            return redirect(url_for('show_request_form'))
    except Exception:
        pass
    # mark used
    cur.execute('UPDATE login_tokens SET used=1 WHERE id=?', (row['id'],))
    conn.commit()
    # create session
    session.clear()
    session['user_id'] = row['user_id']
    session['csrf_token'] = secrets.token_hex(16)
    conn.close()
    return redirect(url_for('admin_manage'))


# Initialize DB when run directly
if __name__ == '__main__':
        init_db()
        app.run(host='0.0.0.0', port=5000, debug=True)
