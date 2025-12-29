# core.py
"""
Core functionality for INS inventory app:
- DB + migrations
- CRUD for inventory and other forms
- Transactions logging
- PDF & barcode generation
- Backup and printing helpers

This file is UI-agnostic so it can be imported by `main_ui.py`.
It also supports a small CLI: `python core.py migrate`.
"""

import os, sqlite3, tempfile, datetime, shutil, subprocess, sys
from uuid import uuid4

# third-party libs used here (ensure installed in your venv)
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image  # used indirectly by python-barcode ImageWriter

# Paths & constants (change if you want)
DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"
BACKUP_DIR = r"C:\ProgramData\MyWarehouse\backups"
TMP = tempfile.gettempdir()
SUMATRA_PATH = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"

# ---------------------------
# DATABASE & MIGRATION
# ---------------------------
def ensure_db_and_migrate():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    # create core tables
    cur.execute("""
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        part_no TEXT,
        delta INTEGER,
        tx_type TEXT,
        reason TEXT,
        source TEXT,
        created_utc TEXT
    );""")
    # other forms
    cur.execute("""
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
    cur.execute("""
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
    cur.execute("""
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

    # Ensure expected columns exist in inventory (best-effort non-destructive migration)
    expected_cols = {
        "s_no":"TEXT","sl_no_contract":"TEXT","set_patt_no":"TEXT","part_no":"TEXT","description":"TEXT",
        "denomination":"TEXT","type":"TEXT","qty_per_gt":"INTEGER","mdnd_def":"TEXT","lf_no":"TEXT","location_bin":"TEXT",
        "received_from_whom":"TEXT","qty_received":"INTEGER","issued_to_whom":"TEXT","qty_issued":"INTEGER","total_qty":"INTEGER",
        "balance":"INTEGER","remarks":"TEXT","created_utc":"TEXT","modified_utc":"TEXT"
    }
    cur.execute("PRAGMA table_info(inventory);")
    present = {r[1] for r in cur.fetchall()}
    for col, col_type in expected_cols.items():
        if col not in present:
            try:
                cur.execute(f"ALTER TABLE inventory ADD COLUMN {col} {col_type};")
            except Exception:
                # ignore failures and continue
                pass
    conn.commit()
    conn.close()

# low-level helper
def _run(sql, params=(), fetch=False):
    ensure_db_and_migrate()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = None
    if fetch:
        rows = cur.fetchall()
    conn.commit()
    conn.close()
    return rows

# ---------------------------
# CRUD: Inventory + Transactions + Other Forms
# ---------------------------
def add_inventory_record(s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt,
                         mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued,
                         total_qty, balance, remarks):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("""INSERT INTO inventory (id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
         (str(uuid4()), s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt,
          mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued,
          total_qty, balance, remarks, now, now))

def list_inventory():
    return _run("SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc FROM inventory ORDER BY created_utc DESC", fetch=True)

def get_inventory_by_id(id_):
    rows = _run("SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc FROM inventory WHERE id = ?", (id_,), fetch=True)
    return rows[0] if rows else None

def get_inventory_by_partno(part_no):
    rows = _run("SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc FROM inventory WHERE part_no = ?", (part_no,), fetch=True)
    return rows[0] if rows else None

def update_inventory(id_, s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt,
                     mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued,
                     total_qty, balance, remarks):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("""UPDATE inventory SET s_no=?, sl_no_contract=?, set_patt_no=?, part_no=?, description=?, denomination=?, type=?, qty_per_gt=?, mdnd_def=?, lf_no=?, location_bin=?, received_from_whom=?, qty_received=?, issued_to_whom=?, qty_issued=?, total_qty=?, balance=?, remarks=?, modified_utc=? WHERE id=?""",
         (s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt,
          mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued,
          total_qty, balance, remarks, now, id_))

def delete_inventory(id_):
    _run("DELETE FROM inventory WHERE id = ?", (id_,))

# transactions
def log_transaction(part_no, delta, tx_type, reason="", source="manual"):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO transactions (id, part_no, delta, tx_type, reason, source, created_utc) VALUES (?,?,?,?,?,?,?)",
         (str(uuid4()), part_no, delta, tx_type, reason, source, now))

def adjust_qty_by_partno(part_no, delta, reason="", source="manual"):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("UPDATE inventory SET total_qty = COALESCE(total_qty,0) + ?, balance = COALESCE(balance,0) + ?, modified_utc = ? WHERE part_no = ?",
         (delta, delta, now, part_no))
    tx_type = "IN" if delta > 0 else "OUT"
    log_transaction(part_no, delta, tx_type, reason, source)

def list_transactions(limit=1000):
    return _run("SELECT id, part_no, delta, tx_type, reason, source, created_utc FROM transactions ORDER BY created_utc DESC LIMIT ?", (limit,), fetch=True)

def search_inventory(term):
    t = f"%{term}%"
    return _run("""SELECT id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc
                   FROM inventory WHERE part_no LIKE ? OR description LIKE ? OR s_no LIKE ? ORDER BY created_utc DESC""", (t,t,t), fetch=True)

# Certified receipt CRUD
def save_certified_receipt(set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO certified_receipt (id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks, now))

def list_certified_receipt():
    return _run("SELECT id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc FROM certified_receipt ORDER BY created_utc DESC", fetch=True)

# Spares issue CRUD
def save_spares_issue(sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO spares_issue (id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks, now))

def list_spares_issue():
    return _run("SELECT id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc FROM spares_issue ORDER BY created_utc DESC", fetch=True)

# Demand supply CRUD
def save_demand_supply(patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks):
    now = datetime.datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO demand_supply (id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks, now))

def list_demand_supply():
    return _run("SELECT id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc FROM demand_supply ORDER BY created_utc DESC", fetch=True)

# ---------------------------
# BACKUP
# ---------------------------
def backup_db(keep_days=30):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    now = datetime.datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    tmp_copy = os.path.join(BACKUP_DIR, f"db_copy_{now}.db")
    shutil.copy2(DB_PATH, tmp_copy)
    zip_name = os.path.join(BACKUP_DIR, f"backup_{now}.zip")
    shutil.make_archive(zip_name.replace('.zip',''), 'zip', BACKUP_DIR, os.path.basename(tmp_copy))
    os.remove(tmp_copy)
    # rotate
    for f in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp):
            age = (datetime.datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(fp))).days
            if age > keep_days:
                os.remove(fp)

# ---------------------------
# PDF / Barcode generation / printing helpers
# ---------------------------

def create_inventory_sheet_pdf(record, out_path=None):
    if out_path is None:
        out_path = os.path.join(TMP, f"inventory_sheet_{record[4]}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4
    margin = 15*mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, h - margin, "INS - INVENTORY DATA SHEET")
    c.setFont("Helvetica", 10)
    y_top = h - margin - 20
    left_labels = [
        ("SNo.", record[1]), ("SL No of Contract", record[2]), ("Set Patt No", record[3]),
        ("Part No", record[4]), ("Description", record[5]), ("Denomination", record[6]),
        ("Type", record[7]), ("Qty Per GT", str(record[8] or "")), ("MDND/DEF", record[9]),
        ("LF No (MGT No.)", record[10]), ("Location/Bin", record[11])
    ]
    x = margin; y = y_top
    for lab, val in left_labels:
        c.drawString(x, y, f"{lab}:"); c.drawString(x + 140, y, str(val or "")); y -= 12
    x2 = margin + 320; y2 = y_top
    right_labels = [
        ("Received From Whom", record[12]), ("Qty Received", str(record[13] or "")),
        ("Issued to Whom", record[14]), ("Qty Issued", str(record[15] or "")),
        ("Total Qty", str(record[16] or "")), ("Balance", str(record[17] or "")), ("Remarks", record[18] or "")
    ]
    for lab, val in right_labels:
        c.drawString(x2, y2, f"{lab}:"); c.drawString(x2 + 150, y2, str(val or "")); y2 -= 12
    barcode_val = str(record[4] or "")
    bc = code128.Code128(barcode_val, barHeight=18*mm, barWidth=0.45)
    bc.drawOn(c, margin, y2 - 36)
    c.showPage()
    c.save()
    return out_path

def create_labels_pdf(part_no, name, qty, out_path=None, label_w_mm=70, label_h_mm=30):
    if out_path is None:
        out_path = os.path.join(TMP, f"labels_{part_no}_{datetime.datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.pdf")
    c = canvas.Canvas(out_path, pagesize=(label_w_mm*mm, label_h_mm*mm))
    for i in range(max(1, int(qty))):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(5*mm, (label_h_mm-6)*mm, (name or part_no)[:60])
        barcode = code128.Code128(str(part_no), barHeight=12*mm, barWidth=0.34)
        barcode.drawOn(c, 5*mm, 6*mm)
        c.setFont("Helvetica", 9)
        c.drawString(5*mm, 3*mm, str(part_no))
        c.showPage()
    c.save()
    return out_path

def create_inventory_report_pdf(rows, out_path=None, title="Inventory Report"):
    if out_path is None:
        out_path = os.path.join(TMP, f"inventory_report_{datetime.datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    y = h - margin
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, y, title); y -= 18
    c.setFont("Helvetica", 10); c.drawString(margin, y, f"Generated: {datetime.datetime.datetime.utcnow().isoformat()}Z"); y -= 14
    col_x = [margin, margin+60*mm, margin+120*mm, margin+180*mm]
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col_x[0], y, "Part No"); c.drawString(col_x[1], y, "Description"); c.drawRightString(w - margin, y, "Total Qty")
    y -= 12; c.setFont("Helvetica", 9)
    for r in rows:
        if y < margin + 40:
            c.showPage(); y = h - margin
        part_no = r[4]; desc = (r[5] or "")[:40]; qty = str(r[16] or "")
        c.drawString(col_x[0], y, str(part_no)); c.drawString(col_x[1], y, desc); c.drawRightString(w - margin, y, qty)
        y -= 12
    c.showPage(); c.save()
    return out_path

def create_certified_receipt_pdf(record, out_path=None):
    if out_path is None:
        out_path = os.path.join(TMP, f"certified_receipt_{record[1] or 'rec'}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, h - margin, "Certified Receipt Voucher")
    y = h - margin - 30
    labels = ["Set No", "Part No", "Item Description", "Denomination/Qty", "Qty Received", "Received From", "Received By", "Remarks"]
    vals = [record[1] or "", record[2] or "", record[3] or "", record[4] or "", str(record[5] or ""), record[6] or "", record[7] or "", record[8] or ""]
    c.setFont("Helvetica", 11)
    for lab, val in zip(labels, vals):
        c.drawString(margin, y, f"{lab}:"); c.drawString(margin+140, y, str(val)); y -= 14
    c.showPage(); c.save(); return out_path

def create_spares_issue_pdf(record, out_path=None):
    if out_path is None:
        out_path = os.path.join(TMP, f"spares_issue_{record[1] or 'si'}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, h - margin, "Spares Issue Voucher")
    y = h - margin - 30
    labels = ["SL No","Part No","Description","LF No","Item","Qty Issued","Balance","Issued To","Remarks"]
    vals = [record[1] or "", record[2] or "", record[3] or "", record[4] or "", record[5] or "", str(record[6] or ""), str(record[7] or ""), record[8] or "", record[9] or ""]
    c.setFont("Helvetica",11)
    for lab, val in zip(labels, vals):
        c.drawString(margin, y, f"{lab}:"); c.drawString(margin+140, y, str(val)); y -= 14
    c.showPage(); c.save(); return out_path

def create_demand_supply_pdf(record, out_path=None):
    if out_path is None:
        out_path = os.path.join(TMP, f"demand_supply_{record[1] or 'ds'}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    c.setFont("Helvetica-Bold", 14); c.drawString(margin, h - margin, "Demand on the Supply Office for Naval Stores")
    y = h - margin - 30
    labels = ["Pattern No","Description","Mand/Dept","LF No","Qty Required","Qty Held","Balance","Location","Remarks"]
    vals = [record[1] or "", record[2] or "", record[3] or "", record[4] or "", str(record[5] or ""), str(record[6] or ""), str(record[7] or ""), record[8] or "", record[9] or ""]
    c.setFont("Helvetica",11)
    for lab, val in zip(labels, vals):
        c.drawString(margin, y, f"{lab}:"); c.drawString(margin+160, y, str(val)); y -= 14
    c.showPage(); c.save(); return out_path

# barcode images (preview)
def generate_barcode_images(part_no, name, count, out_dir=None):
    if out_dir is None:
        out_dir = os.path.join(TMP, f"barcode_preview_{part_no}_{datetime.datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    writer = ImageWriter()
    for i in range(max(1,int(count))):
        base = os.path.join(out_dir, f"{part_no}_{i+1}")
        barcode_obj = Code128(str(part_no), writer=writer)
        fname = barcode_obj.save(base)
        paths.append(fname)
    return paths

# printing helpers
def enum_printers():
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        return [p[2] for p in printers]
    except Exception:
        return []

def print_pdf_shell(path):
    try:
        import win32api
        win32api.ShellExecute(0, "print", path, None, ".", 0)
        return True
    except Exception as e:
        print("Shell print failed:", e)
        return False

def print_pdf_sumatra(path, printer_name=None, sumatra_path=SUMATRA_PATH):
    if not os.path.exists(sumatra_path):
        raise FileNotFoundError("SumatraPDF not found")
    cmd = [sumatra_path]
    if printer_name:
        cmd += ["-print-to", printer_name]
    else:
        cmd += ["-print-to-default"]
    cmd.append(path)
    subprocess.Popen(cmd, shell=False)
    return True

# ---------------------------
# CLI: allow running migrations only
# ---------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "migrate":
        print("Running migrations (ensure DB exists and columns are updated)...")
        ensure_db_and_migrate()
        print("Migrations complete.")
        print(f"DB path: {DB_PATH}")
    else:
        print("This module provides core functionality. Import it from your UI file (main_ui.py).")
