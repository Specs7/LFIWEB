import sqlite3
DB_PATH = 'data.db'
email = input('Email admin: ').strip().lower()
if not email:
    print('Email requis'); exit(1)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL DEFAULT "editor", created_at DATETIME DEFAULT CURRENT_TIMESTAMP);')
try:
    cur.execute('INSERT INTO users (email, role) VALUES (?, ?)', (email, 'admin'))
    conn.commit()
    print('Admin ajouté:', email)
except Exception as e:
    print('Erreur:', e)
finally:
    conn.close()
