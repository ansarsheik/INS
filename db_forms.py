# db_forms.py
import sqlite3, os
from datetime import datetime
from uuid import uuid4

DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    # Inventory table with the requested fields
    conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id TEXT PRIMARY KEY,
        s_no TEXT,
        sl_no_contract TEXT,
        set_patt_no TEXT,
        part_no TEXT,
        description TEXT,
        denomination TEXT,
        type TEXT,
        qty_per_gt INTEGER,
        mdnd_def TEXT,
        lf_no TEXT,
        location_bin TEXT,
        received_from_whom TEXT,
        qty_received INTEGER,
        issued_to_whom TEXT,
        qty_issued INTEGER,
        total_qty INTEGER,
        balance INTEGER,
        remarks TEXT,
        created_utc TEXT,
        modified_utc TEXT
    );""")
    # transactions table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        part_no TEXT,
        delta INTEGER,
        tx_type TEXT,
        reason TEXT,
        source TEXT,
        created_utc TEXT
    );""")
    conn.commit()

    # Migration: add any missing columns if older DB exists
    existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(inventory);").fetchall()]
    required_cols = ["s_no","sl_no_contract","set_patt_no","part_no","description","denomination","type","qty_per_gt","mdnd_def","lf_no","location_bin","received_from_whom","qty_received","issued_to_whom","qty_issued","total_qty","balance","remarks","created_utc","modified_utc"]
    for col in required_cols:
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE inventory ADD COLUMN {col} TEXT;")
            except Exception:
                # ignore if can't add (very old DB edge cases)
                pass
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

# CRUD for inventory
def add_inventory(s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt, mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued, total_qty, balance, remarks):
    now = datetime.utcnow().isoformat() + "Z"
    _run("""INSERT INTO inventory (id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
         (str(uuid4()), s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt, mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued, total_qty, balance, remarks, now, now))

def list_inventory():
    return _run("SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc FROM inventory ORDER BY created_utc DESC", fetch=True)

def get_inventory_by_id(id_):
    rows = _run("SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc FROM inventory WHERE id = ?", (id_,), fetch=True)
    return rows[0] if rows else None

def get_inventory_by_partno(part_no):
    rows = _run("SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc FROM inventory WHERE part_no = ?", (part_no,), fetch=True)
    return rows[0] if rows else None

def update_inventory(id_, s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt, mdnd_def, lf_no, location_bin, received_from_wh
