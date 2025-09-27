import os, sqlite3, hashlib, secrets, smtplib, re
from datetime import datetime, timedelta
from email.message import EmailMessage
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, render_template_string
from urllib.parse import urlparse

DB_PATH = os.getenv('DB_PATH', 'data.db')
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
SITE_URL = os.getenv('SITE_URL', 'http://localhost:5000')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'no-reply@example.com')
TOKEN_EXP_MINUTES = int(os.getenv('TOKEN_EXP_MINUTES', '15'))

app = Flask(__name__)
app.secret_key = SECRET_KEY
# session cookie settings (safe defaults for dev; override in prod via env)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_safe_url(url: str) -> bool:
    if not url:
        return False
    try:
        parts = urlparse(url)
        return parts.scheme in ('http', 'https') and bool(parts.netloc)
    except Exception:
        return False


def _check_csrf():
    # For state-changing requests, require X-CSRF-Token header and match session value
    if request.method in ('POST', 'PUT', 'DELETE'):
        header = request.headers.get('X-CSRF-Token')
        if not header or header != session.get('csrf_token'):
            return False
    return True


@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    # basic CSP: allow same-origin and common CDNs for fonts/images/scripts
    response.headers.setdefault('Content-Security-Policy', "default-src 'self' https:; img-src 'self' data: https:; font-src 'self' https:; script-src 'self' https: 'unsafe-inline'; style-src 'self' https: 'unsafe-inline';")
    return response

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
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
    ''')
    conn.commit()
    conn.close()

def gen_token():
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def send_mail(to_email: str, subject: str, text: str):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        app.logger.warning('SMTP not configured, skipping send_mail. Would send to %s', to_email)
        app.logger.info('Mail contents: %s', text)
        return True
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg.set_content(text)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        app.logger.error('Failed to send email: %s', e)
        return False

def recent_token_count(conn, user_id=None, ip=None, minutes=60):
    cur = conn.cursor()
    since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
    if user_id:
        cur.execute('SELECT COUNT(*) FROM login_tokens WHERE user_id=? AND created_at>=?', (user_id, since))
    elif ip:
        cur.execute('SELECT COUNT(*) FROM login_tokens WHERE ip=? AND created_at>=?', (ip, since))
    else:
        return 0
    return cur.fetchone()[0]

@app.route('/auth/request-token', methods=['POST'])
def request_token():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({'status': 'ok'}), 200
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, role FROM users WHERE email=?', (email,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'status': 'ok'}), 200
    user_id = row['id']
    ip = request.remote_addr
    if recent_token_count(conn, user_id=user_id, minutes=60) >= 5 or recent_token_count(conn, ip=ip, minutes=60) >= 20:
        conn.close()
        return jsonify({'error': 'Too many requests'}), 429
    token = gen_token()
    token_hash = hash_token(token)
    expires_at = (datetime.utcnow() + timedelta(minutes=TOKEN_EXP_MINUTES)).isoformat()
    cur.execute('INSERT INTO login_tokens (user_id, token_hash, expires_at, ip, user_agent) VALUES (?,?,?,?,?)',
                (user_id, token_hash, expires_at, ip, request.headers.get('User-Agent')))
    conn.commit()
    conn.close()
    link = f"{SITE_URL.rstrip('/')}/admin/verify?email={email}&token={token}"
    subject = 'Votre lien de connexion'
    text = f"Bonjour,\n\nCliquez sur le lien ci‑dessous pour vous connecter (valide {TOKEN_EXP_MINUTES} minutes):\n\n{link}\n\nSi vous n'avez pas demandé ce lien, ignorez cet email.\n"
    send_mail(email, subject, text)
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/verify', methods=['GET'])
def verify_token():
    email = (request.args.get('email') or '').strip().lower()
    token = request.args.get('token') or ''
    if not email or not token:
        return 'Paramètres manquants', 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE email=?', (email,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return 'Token invalide', 400
    user_id = user['id']
    token_hash = hash_token(token)
    cur.execute('''SELECT id, used, expires_at FROM login_tokens
                   WHERE user_id=? AND token_hash=? ORDER BY created_at DESC LIMIT 1''', (user_id, token_hash))
    row = cur.fetchone()
    if not row:
        conn.close()
        return 'Token invalide', 400
    if row['used']:
        conn.close()
        return 'Token déjà utilisé', 400
    if datetime.fromisoformat(row['expires_at']) < datetime.utcnow():
        conn.close()
        return 'Token expiré', 400
    cur.execute('UPDATE login_tokens SET used=1 WHERE id=?', (row['id'],))
    conn.commit()
    conn.close()
    session['user_id'] = user_id
    session['logged_in_at'] = datetime.utcnow().isoformat()
    # generate a csrf token for subsequent state-changing requests
    session['csrf_token'] = secrets.token_urlsafe(16)
    return redirect(url_for('admin_index'))

@app.route('/admin')
def admin_index():
    if not session.get('user_id'):
        return redirect(url_for('show_request_form'))
    return render_template_string('<h2>Admin connecté</h2><p>Utilisateur id: {{uid}}</p><p><a href="/admin/logout">Déconnexion</a></p>', uid=session.get('user_id'))


@app.route('/api/articles', methods=['GET'])
def api_get_articles():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, title, author, content, image, created_at FROM articles ORDER BY created_at DESC')
    rows = cur.fetchall()
    articles = [dict(r) for r in rows]
    conn.close()
    return jsonify({'articles': articles}), 200


@app.route('/api/articles', methods=['POST'])
def api_create_article():
    # Simple protection: require session login
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    if not _check_csrf():
        return jsonify({'error': 'Invalid CSRF token'}), 403
    # Check role is admin
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE id=?', (session.get('user_id'),))
    user = cur.fetchone()
    if not user or user['role'] != 'admin':
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    # server-side validation & sanitization
    title = (data.get('title') or '').strip()
    author = (data.get('author') or '').strip()
    content = (data.get('content') or '').strip()
    image = (data.get('image') or '').strip()
    if not title:
        return jsonify({'error': 'title required'}), 400
    if len(title) > 200 or len(author) > 100 or len(content) > 10000:
        return jsonify({'error': 'Input too long'}), 400
    if image and not is_safe_url(image):
        return jsonify({'error': 'Invalid image URL'}), 400
    conn = get_db()
    cur = conn.cursor()
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

@app.route('/')
def index():
    # Serve the static frontend template
    try:
        return render_template('lfi_municipal_site.html')
    except Exception as e:
        app.logger.error('Failed to render template: %s', e)
        return render_template_string('<p>Frontend template not found. Please ensure backend/templates/lfi_municipal_site.html exists.</p>'), 500

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('show_request_form'))

@app.route('/admin/request', methods=['GET'])
def show_request_form():
    return render_template_string('''
    <h2>Demande de lien de connexion</h2>
    <form method="post" action="/auth/request-token" onsubmit="event.preventDefault(); send();">
      <input type="email" id="email" name="email" placeholder="Votre email" required>
      <button type="submit">Recevoir le lien</button>
    </form>
    <div id="msg"></div>
    <script>
      async function send(){
        const email = document.getElementById('email').value;
        await fetch('/auth/request-token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
        document.getElementById('msg').textContent = 'Si un compte existe, vous recevrez un email.';
      }
    </script>
    ''')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
