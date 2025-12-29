# db_forms.py
import sqlite3, os
from datetime import datetime
from uuid import uuid4

DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    # inventory
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
    # transactions
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        sku TEXT,
        delta INTEGER,
        tx_type TEXT,
        reason TEXT,
        source TEXT,
        created_utc TEXT
    );""")
    # certified_receipt
    conn.execute("""
    CREATE TABLE IF NOT EXISTS certified_receipt (
        id TEXT PRIMARY KEY,
        set_no TEXT,
        part_no TEXT,
        item_desc TEXT,
        denom_qty TEXT,
        qty_received INTEGER,
        received_from TEXT,
        received_by TEXT,
        remarks TEXT,
        created_utc TEXT
    );""")
    # spares_issue
    conn.execute("""
    CREATE TABLE IF NOT EXISTS spares_issue (
        id TEXT PRIMARY KEY,
        sl_no TEXT,
        part_no TEXT,
        description TEXT,
        lf_no TEXT,
        item TEXT,
        qty_issued INTEGER,
        balance INTEGER,
        issued_to TEXT,
        remarks TEXT,
        created_utc TEXT
    );""")
    # demand_supply
    conn.execute("""
    CREATE TABLE IF NOT EXISTS demand_supply (
        id TEXT PRIMARY KEY,
        patt_no TEXT,
        description TEXT,
        mand_dept TEXT,
        lf_no TEXT,
        qty_req INTEGER,
        qty_held INTEGER,
        balance INTEGER,
        location TEXT,
        remarks TEXT,
        created_utc TEXT
    );""")
    conn.commit()

    # safe migrations for older DBs
    cols = [r[1] for r in conn.execute("PRAGMA table_info(inventory);").fetchall()]
    if "sku" not in cols:
        conn.execute("ALTER TABLE inventory ADD COLUMN sku TEXT;")
    if "modified_utc" not in cols:
        conn.execute("ALTER TABLE inventory ADD COLUMN modified_utc TEXT;")
    conn.commit()
    conn.close()

# low-level helper
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

# Inventory CRUD & helpers (unchanged)
def add_inventory(sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("""INSERT INTO inventory (id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
         (str(uuid4()), sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks, now, now))

def list_inventory():
    return _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc FROM inventory ORDER BY name", fetch=True)

def get_inventory_by_id(id_):
    rows = _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc FROM inventory WHERE id = ?", (id_,), fetch=True)
    return rows[0] if rows else None

def get_inventory_by_sku(sku):
    rows = _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc FROM inventory WHERE sku = ?", (sku,), fetch=True)
    return rows[0] if rows else None

def update_inventory(id_, sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("""UPDATE inventory SET sku=?, name=?, description=?, denomination=?, type=?, qty=?, location=?, received_from=?, issued_to=?, balance=?, remarks=?, modified_utc=? WHERE id=?""",
         (sku, name, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks, now, id_))

def delete_inventory(id_):
    _run("DELETE FROM inventory WHERE id = ?", (id_,))

# transactions
def log_transaction(sku, delta, tx_type, reason="", source="manual"):
    now = datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO transactions (id, sku, delta, tx_type, reason, source, created_utc) VALUES (?,?,?,?,?,?,?)",
         (str(uuid4()), sku, delta, tx_type, reason, source, now))

def adjust_qty_by_sku(sku, delta, reason="", source="manual"):
    now = datetime.utcnow().isoformat() + "Z"
    _run("UPDATE inventory SET qty = COALESCE(qty,0) + ?, modified_utc = ? WHERE sku = ?", (delta, now, sku))
    tx_type = "IN" if delta > 0 else "OUT"
    log_transaction(sku, delta, tx_type, reason, source)

def list_transactions(limit=1000):
    return _run("SELECT id, sku, delta, tx_type, reason, source, created_utc FROM transactions ORDER BY created_utc DESC LIMIT ?", (limit,), fetch=True)

def search_inventory(term):
    t = f"%{term}%"
    return _run("SELECT id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc FROM inventory WHERE sku LIKE ? OR name LIKE ? OR description LIKE ? ORDER BY name",
                (t, t, t), fetch=True)

# Certified Receipt CRUD
def save_certified_receipt(set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO certified_receipt (id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks, now))

def list_certified_receipt():
    return _run("SELECT id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc FROM certified_receipt ORDER BY created_utc DESC", fetch=True)

def delete_certified_receipt(id_):
    _run("DELETE FROM certified_receipt WHERE id = ?", (id_,))

# Spares issue CRUD
def save_spares_issue(sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO spares_issue (id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks, now))

def list_spares_issue():
    return _run("SELECT id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc FROM spares_issue ORDER BY created_utc DESC", fetch=True)

def delete_spares_issue(id_):
    _run("DELETE FROM spares_issue WHERE id = ?", (id_,))

# Demand supply CRUD
def save_demand_supply(patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO demand_supply (id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks, now))

def list_demand_supply():
    return _run("SELECT id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc FROM demand_supply ORDER BY created_utc DESC", fetch=True)

def delete_demand_supply(id_):
    _run("DELETE FROM demand_supply WHERE id = ?", (id_,))
