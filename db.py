import sqlite3
from pathlib import Path

DB_PATH = Path("data.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        minutes INTEGER NOT NULL,
        date_greg TEXT NOT NULL,
        date_jalali TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """)
    conn.commit()
    conn.close()

def insert_tasks(task_names):
    conn = get_conn()
    cur = conn.cursor()
    for name in task_names:
        cur.execute("INSERT OR IGNORE INTO tasks(name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_tasks():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM tasks ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

def insert_entry(task_id, minutes, date_greg, date_jalali):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO entries(task_id, minutes, date_greg, date_jalali)
        VALUES (?, ?, ?, ?)
    """, (task_id, minutes, date_greg, date_jalali))
    conn.commit()
    conn.close()

def get_stats_between(date_from_greg, date_to_greg):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT t.name, SUM(e.minutes) 
    FROM entries e
    JOIN tasks t ON t.id = e.task_id
    WHERE e.date_greg BETWEEN ? AND ?
    GROUP BY t.name
    ORDER BY t.id ASC
    """, (date_from_greg, date_to_greg))
    rows = cur.fetchall()
    conn.close()
    return rows
