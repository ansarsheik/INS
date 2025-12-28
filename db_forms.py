# db_forms.py
import sqlite3
import os
from datetime import datetime
from uuid import uuid4

DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    # Inventory Data Sheet
    conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id TEXT PRIMARY KEY,
        item_no TEXT,
        part_no TEXT,
        description TEXT,
        denomination TEXT,
        type TEXT,
        qty INTEGER,
        location TEXT,
        received_from TEXT,
        issued_to TEXT,
        balance INTEGER,
        remarks TEXT,
        created_utc TEXT
    );
    """)
    # Certified Receipt Voucher
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
    );
    """)
    # Spares Issue Voucher
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
    );
    """)
    # Demand on the Supply Office for Naval Stores
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
    );
    """)
    conn.commit()
    conn.close()

# Generic helper
def _insert(table, data: dict):
    ensure_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    keys = ",".join(data.keys())
    placeholders = ",".join(["?"]*len(data))
    sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
    cur.execute(sql, list(data.values()))
    conn.commit()
    conn.close()

def _select_all(table, order_by="created_utc"):
    ensure_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} ORDER BY {order_by} DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

# Inventory functions
def save_inventory(item_no, part_no, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks):
    data = {
        "id": str(uuid4()),
        "item_no": item_no,
        "part_no": part_no,
        "description": description,
        "denomination": denomination,
        "type": type_,
        "qty": qty,
        "location": location,
        "received_from": received_from,
        "issued_to": issued_to,
        "balance": balance,
        "remarks": remarks,
        "created_utc": datetime.utcnow().isoformat() + "Z"
    }
    _insert("inventory", data)

def list_inventory():
    return _select_all("inventory")

# Certified receipt functions
def save_certified_receipt(set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks):
    data = {
        "id": str(uuid4()),
        "set_no": set_no,
        "part_no": part_no,
        "item_desc": item_desc,
        "denom_qty": denom_qty,
        "qty_received": qty_received,
        "received_from": received_from,
        "received_by": received_by,
        "remarks": remarks,
        "created_utc": datetime.utcnow().isoformat() + "Z"
    }
    _insert("certified_receipt", data)

def list_certified_receipt():
    return _select_all("certified_receipt")

# Spares issue functions
def save_spares_issue(sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks):
    data = {
        "id": str(uuid4()),
        "sl_no": sl_no,
        "part_no": part_no,
        "description": description,
        "lf_no": lf_no,
        "item": item,
        "qty_issued": qty_issued,
        "balance": balance,
        "issued_to": issued_to,
        "remarks": remarks,
        "created_utc": datetime.utcnow().isoformat() + "Z"
    }
    _insert("spares_issue", data)

def list_spares_issue():
    return _select_all("spares_issue")

# Demand on supply functions
def save_demand_supply(patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks):
    data = {
        "id": str(uuid4()),
        "patt_no": patt_no,
        "description": description,
        "mand_dept": mand_dept,
        "lf_no": lf_no,
        "qty_req": qty_req,
        "qty_held": qty_held,
        "balance": balance,
        "location": location,
        "remarks": remarks,
        "created_utc": datetime.utcnow().isoformat() + "Z"
    }
    _insert("demand_supply", data)

def list_demand_supply():
    return _select_all("demand_supply")
