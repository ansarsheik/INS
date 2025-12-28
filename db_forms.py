# db_forms.py
import sqlite3, os
from datetime import datetime
from uuid import uuid4

DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    # create inventory table (if missing columns migration will add them)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id TEXT PRIMARY KEY,
        sku TEXT UNIQUE,
        name TEXT,
        description TEXT,
        denomination TEXT,
        type TEXT,
        qty INTEGER,
        location TEXT,
        received_from TEXT,
        issued_to TEXT,
        balance INTEGER,
        remarks TEXT,
        created_utc TEXT,
        modified_utc TEXT
    );""")
    # create transactions table to log in/out
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        sku TEXT,
        delta INTEGER,
        tx_type TEXT, -- 'IN' or 'OUT'
        reason TEXT,
        source TEXT,  -- 'scanner' or 'manual'
        created_utc TEXT
    );""")
    conn.commit()

    # simple automatic column migrations for older DBs
    cols = [r[1] for r in conn.execute("PRAGMA table_info(inventory);").fetchall()]
    if "sku" not in cols:
        conn.execute("ALTER TABLE inventory ADD COLUMN sku TEXT;")
    if "modified_utc" not in cols:
        conn.execute("ALTER TABLE inventory ADD COLUMN modified_utc TEXT;")
    # ensure transactions table exists (already created above)
    conn.commit()
    conn.close()

def _run(sql, params=(), fetch=False):
    ensure_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = None
    if fetch:
        rows = cur.fetchall()
    conn.commit()
    conn.close()
    return rows

# Inventory CRUD & helpers
def add_inventory(sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("""INSERT INTO inventory (id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
         (str(uuid4()), sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks, now, now))

def list_inventory():
    return _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc FROM inventory ORDER BY name", fetch=True)

def get_inventory_by_sku(sku):
    rows = _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks FROM inventory WHERE sku = ?", (sku,), fetch=True)
    return rows[0] if rows else None

def get_inventory_by_id(id_):
    rows = _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks FROM inventory WHERE id = ?", (id_,), fetch=True)
    return rows[0] if rows else None

def update_inventory(id_, sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("""UPDATE inventory SET sku=?, name=?, description=?, denomination=?, type=?, qty=?, location=?, received_from=?, issued_to=?, balance=?, remarks=?, modified_utc=? WHERE id=?""",
         (sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks, now, id_))

def delete_inventory(id_):
    _run("DELETE FROM inventory WHERE id = ?", (id_,))

# Transactions log
def log_transaction(sku, delta, tx_type, reason="", source="manual"):
    now = datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO transactions (id, sku, delta, tx_type, reason, source, created_utc) VALUES (?,?,?,?,?,?,?)",
         (str(uuid4()), sku, delta, tx_type, reason, source, now))

def list_transactions(limit=1000):
    return _run("SELECT id, sku, delta, tx_type, reason, source, created_utc FROM transactions ORDER BY created_utc DESC LIMIT ?", (limit,), fetch=True)

# Qty adjustments (for scanner / usage)
def adjust_qty_by_sku(sku, delta, reason="", source="manual"):
    # apply change and log it atomically (two statements)
    now = datetime.utcnow().isoformat() + "Z"
    # Ensure SKU exists; if not, create placeholder? for safety we error out in calling code
    _run("UPDATE inventory SET qty = COALESCE(qty,0) + ?, modified_utc = ? WHERE sku = ?", (delta, now, sku))
    tx_type = "IN" if delta > 0 else "OUT"
    log_transaction(sku, delta, tx_type, reason=reason, source=source)

# Search
def search_inventory(term):
    t = f"%{term}%"
    return _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc FROM inventory WHERE sku LIKE ? OR name LIKE ? OR description LIKE ? ORDER BY name",
                (t, t, t), fetch=True)
