#!/usr/bin/env python3
"""Migration: add site_meta table and insert default values if missing."""
import os
import sqlite3
from datetime import datetime

DB = os.getenv('DB_PATH') or os.path.abspath(os.path.join(os.getcwd(), 'data.db'))

def main():
    print('Using DB:', DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS site_meta (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    # defaults (insert only if not present)
    defaults = {
        'site_title': 'La France Insoumise - Notre Ville',
        'site_subtitle': "L'Avenir en Commun",
        'footer_text': "&copy; 2025 Liste Municipale LFI - Notre Ville. L'Avenir en Commun.",
        'pillars_html': None,
        'contact_html': None,
        'socials_html': None
    }
    for k, v in defaults.items():
        cur.execute('SELECT 1 FROM site_meta WHERE key=?', (k,))
        if not cur.fetchone():
            cur.execute('INSERT INTO site_meta (key, value, updated_at) VALUES (?,?,?)', (k, v or '', datetime.utcnow().isoformat()))
            print('Inserted default for', k)
    conn.commit()
    conn.close()
    print('Migration site_meta complete')

if __name__ == '__main__':
    main()
