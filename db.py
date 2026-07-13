import sqlite3
import datetime
import os

DB_FILE = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS txns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            note TEXT,
            type TEXT,
            chat_id TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add(date, category, amount, note, type, chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    created_at = datetime.datetime.now().isoformat()
    c.execute('''
        INSERT INTO txns (date, category, amount, note, type, chat_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (date, category, amount, note, type, chat_id, created_at))
    conn.commit()
    conn.close()

def undo_last(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id FROM txns WHERE chat_id = ? ORDER BY id DESC LIMIT 1
    ''', (chat_id,))
    row = c.fetchone()
    if row:
        c.execute('DELETE FROM txns WHERE id = ?', (row[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def all_rows():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM txns ORDER BY date DESC, id DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def month_total(month_str):
    # month_str format: 'YYYY-MM'
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT SUM(amount) FROM txns WHERE date LIKE ? AND type = 'expense'
    ''', (f"{month_str}%",))
    row = c.fetchone()
    conn.close()
    return row[0] or 0.0

init_db()
