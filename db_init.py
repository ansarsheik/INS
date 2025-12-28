# db_init.py
import sqlite3
import os
from uuid import uuid4
from datetime import datetime

DB_PATH = r"C:\ProgramData\MyWarehouse\app.db"

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS items(
        id TEXT PRIMARY KEY,
        sku TEXT,
        name TEXT,
        qty INTEGER,
        created_utc TEXT,
        modified_utc TEXT
    );
    """)
    conn.commit()
    conn.close()

def add_item(sku, name, qty):
    ensure_db()
    if not sku:
        sku = str(uuid4())[:12]  # short unique SKU if not provided
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("INSERT INTO items (id, sku, name, qty, created_utc, modified_utc) VALUES (?,?,?,?,?,?)",
                (str(uuid4()), sku, name, int(qty), now, now))
    conn.commit()
    conn.close()
    return sku

def get_all_items():
    ensure_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("SELECT id, sku, name, qty, created_utc, modified_utc FROM items ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_item_by_sku(sku):
    ensure_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("SELECT id, sku, name, qty FROM items WHERE sku = ?", (sku,))
    row = cur.fetchone()
    conn.close()
    return row

def update_qty(sku, qty):
    ensure_db()
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("UPDATE items SET qty = ?, modified_utc = ? WHERE sku = ?", (int(qty), now, sku))
    conn.commit()
    conn.close()
