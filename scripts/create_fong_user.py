#!/usr/bin/env python3
"""
One-off helper to create or update a dev user 'fong' in the SQLite DB used by the app.
Run from the repo root with: python scripts/create_fong_user.py
This script is intended for development only. It will NOT run in production.
"""
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'webstore.db')

username = 'fong'
email = 'fong@fong.com'
password = 'fong'

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    raise SystemExit(1)

pw_hash = generate_password_hash(password)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# ensure users table exists
try:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        print('users table not found in DB. Aborting.')
        conn.close()
        raise SystemExit(1)

    # check for existing user by username or email
    cur.execute('SELECT id, username, email FROM users WHERE username = ? OR email = ?', (username, email))
    existing = cur.fetchone()
    now = datetime.utcnow().isoformat()
    if existing:
        print('Existing user found. Updating password and email/username to match desired values.')
        cur.execute('UPDATE users SET username = ?, email = ?, password_hash = ?, updated_at = ? WHERE id = ?', (username, email, pw_hash, now, existing['id']))
        conn.commit()
        print(f"Updated user id={existing['id']}")
    else:
        # try to insert with minimal required columns; adapt if schema differs
        try:
            cur.execute(
                'INSERT INTO users (username, email, password_hash, is_admin, is_seller, created_at) VALUES (?, ?, ?, 0, 0, ?)',
                (username, email, pw_hash, now)
            )
            conn.commit()
            print(f"Inserted new user id={cur.lastrowid}")
        except sqlite3.IntegrityError:
            # fallback: try inserting without assuming columns
            cur.execute('INSERT OR REPLACE INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)', (username, email, pw_hash, now))
            conn.commit()
            print('Inserted/updated user (fallback path).')
except Exception as e:
    print('Error:', e)
finally:
    conn.close()

print('Done.')
