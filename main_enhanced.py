# main_enhanced.py
"""
Single-file Windows-ready desktop app (PySide6) that:
- Provides Inventory Data Sheet + Certified Receipt Voucher + Spares Issue Voucher + Demand on Supply Office tabs.
- Stores data in SQLite at C:\ProgramData\MyWarehouse\forms.db
- Includes automatic DB migration helper and CLI mode 'migrate' to run migrations only.
- Generates barcode images (preview) and label PDFs (one label per page).
- Generates printable filled-form PDFs for each form.
- Logs transactions for IN/OUT (scanner / manual adjustments).
- Has backup routine (Run Backup Now button).
- Printing uses win32api/win32print if available; SumatraPDF fallback supported.

Usage:
  python main_enhanced.py           # run GUI
  python main_enhanced.py migrate   # run migrations only (safe)
"""

import sys, os, sqlite3, tempfile, datetime, shutil, subprocess
from uuid import uuid4

# UI
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QInputDialog, QFileDialog, QSpinBox, QDialog, QFormLayout, QTextEdit,
    QTabWidget, QGroupBox, QScrollArea, QGridLayout, QDialogButtonBox, QTableWidgetItem
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
from PySide6.QtCore import Qt

# PDF & barcode libs
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# python-barcode (ImageWriter) + PIL used for preview images
from barcode import Code128
from barcode.writer import ImageWriter

# Paths & constants
DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"
BACKUP_DIR = r"C:\ProgramData\MyWarehouse\backups"
TMP = tempfile.gettempdir()
SUMATRA_PATH = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"

# ---------------------------
# DATABASE LAYER & MIGRATION
# ---------------------------
def ensure_db_and_migrate():
    """Create DB and apply incremental migrations to reach latest schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    # Core inventory table: full field set requested in conversation
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
    );
    """)
    # Transactions log
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        part_no TEXT,
        delta INTEGER,
        tx_type TEXT,
        reason TEXT,
        source TEXT,
        created_utc TEXT
    );
    """)
    # Other forms
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
    );
    """)
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
    );
    """)
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
    );
    """)
    conn.commit()

    # Migration safety: ensure each expected column exists; if not, add it as TEXT (or INTEGER where needed).
    # This is non-destructive and safe for most development transitions.
    expected_cols = {
        "inventory": {
            "s_no":"TEXT","sl_no_contract":"TEXT","set_patt_no":"TEXT","part_no":"TEXT","description":"TEXT",
            "denomination":"TEXT","type":"TEXT","qty_per_gt":"INTEGER","mdnd_def":"TEXT","lf_no":"TEXT","location_bin":"TEXT",
            "received_from_whom":"TEXT","qty_received":"INTEGER","issued_to_whom":"TEXT","qty_issued":"INTEGER",
            "total_qty":"INTEGER","balance":"INTEGER","remarks":"TEXT","created_utc":"TEXT","modified_utc":"TEXT"
        },
        # transactions already created above
    }
    for table, cols in expected_cols.items():
        cur.execute(f"PRAGMA table_info({table});")
        present = {r[1] for r in cur.fetchall()}
        for col_name, col_type in cols.items():
            if col_name not in present:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};")
                except Exception:
                    # ignore; best-effort migration
                    pass
    conn.commit()
    conn.close()

# small helper to run SQL
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
    now = datetime.datetime.utcnow().isoformat() + "Z"
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
    now = datetime.datetime.utcnow().isoformat() + "Z"
    _run("""UPDATE inventory SET s_no=?, sl_no_contract=?, set_patt_no=?, part_no=?, description=?, denomination=?, type=?, qty_per_gt=?, mdnd_def=?, lf_no=?, location_bin=?, received_from_whom=?, qty_received=?, issued_to_whom=?, qty_issued=?, total_qty=?, balance=?, remarks=?, modified_utc=? WHERE id=?""",
         (s_no, sl_no_contract, set_patt_no, part_no, description, denomination, type_, qty_per_gt,
          mdnd_def, lf_no, location_bin, received_from_whom, qty_received, issued_to_whom, qty_issued,
          total_qty, balance, remarks, now, id_))

def delete_inventory(id_):
    _run("DELETE FROM inventory WHERE id = ?", (id_,))

# transactions
def log_transaction(part_no, delta, tx_type, reason="", source="manual"):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO transactions (id, part_no, delta, tx_type, reason, source, created_utc) VALUES (?,?,?,?,?,?,?)",
         (str(uuid4()), part_no, delta, tx_type, reason, source, now))

def adjust_qty_by_partno(part_no, delta, reason="", source="manual"):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    # update total_qty and balance if present
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
    now = datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO certified_receipt (id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks, now))

def list_certified_receipt():
    return _run("SELECT id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc FROM certified_receipt ORDER BY created_utc DESC", fetch=True)

def delete_certified_receipt(id_):
    _run("DELETE FROM certified_receipt WHERE id = ?", (id_,))

# Spares issue CRUD
def save_spares_issue(sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO spares_issue (id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks, now))

def list_spares_issue():
    return _run("SELECT id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc FROM spares_issue ORDER BY created_utc DESC", fetch=True)

def delete_spares_issue(id_):
    _run("DELETE FROM spares_issue WHERE id = ?", (id_,))

# Demand supply CRUD
def save_demand_supply(patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    _run("INSERT INTO demand_supply (id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
         (str(uuid4()), patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks, now))

def list_demand_supply():
    return _run("SELECT id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc FROM demand_supply ORDER BY created_utc DESC", fetch=True)

def delete_demand_supply(id_):
    _run("DELETE FROM demand_supply WHERE id = ?", (id_,))

# ---------------------------
# BACKUP
# ---------------------------
def backup_db(keep_days=30):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    tmp_copy = os.path.join(BACKUP_DIR, f"db_copy_{now}.db")
    shutil.copy2(DB_PATH, tmp_copy)
    zip_name = os.path.join(BACKUP_DIR, f"backup_{now}.zip")
    shutil.make_archive(zip_name.replace('.zip',''), 'zip', BACKUP_DIR, os.path.basename(tmp_copy))
    os.remove(tmp_copy)
    # rotate
    for f in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp):
            age = (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(fp))).days
            if age > keep_days:
                os.remove(fp)

# ---------------------------
# PDF / Barcode generation / printing helpers
# ---------------------------
def create_inventory_sheet_pdf(record, out_path=None):
    """
    record fields order:
    id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc
    """
    if out_path is None:
        out_path = os.path.join(TMP, f"inventory_sheet_{record[4]}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4
    margin = 15*mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, h - margin, "INS - INVENTORY DATA SHEET")
    c.setFont("Helvetica", 10)
    y_top = h - margin - 20
    # Left column
    left_labels = [
        ("SNo.", record[1]),
        ("SL No of Contract", record[2]),
        ("Set Patt No", record[3]),
        ("Part No", record[4]),
        ("Description", record[5]),
        ("Denomination", record[6]),
        ("Type", record[7]),
        ("Qty Per GT", str(record[8] or "")),
        ("MDND/DEF", record[9]),
        ("LF No (MGT No.)", record[10]),
        ("Location/Bin", record[11]),
    ]
    x = margin; y = y_top
    for lab, val in left_labels:
        c.drawString(x, y, f"{lab}:")
        c.drawString(x + 140, y, str(val or ""))
        y -= 12
    # Right column
    x2 = margin + 320; y2 = y_top
    right_labels = [
        ("Received From Whom", record[12]),
        ("Qty Received", str(record[13] or "")),
        ("Issued to Whom", record[14]),
        ("Qty Issued", str(record[15] or "")),
        ("Total Qty", str(record[16] or "")),
        ("Balance", str(record[17] or "")),
        ("Remarks", record[18] or "")
    ]
    for lab, val in right_labels:
        c.drawString(x2, y2, f"{lab}:")
        c.drawString(x2 + 150, y2, str(val or ""))
        y2 -= 12
    # barcode (part_no)
    barcode_val = str(record[4] or "")
    bc = code128.Code128(barcode_val, barHeight=18*mm, barWidth=0.45)
    bc.drawOn(c, margin, y2 - 36)
    c.showPage()
    c.save()
    return out_path

def create_labels_pdf(part_no, name, qty, out_path=None, label_w_mm=70, label_h_mm=30):
    if out_path is None:
        out_path = os.path.join(TMP, f"labels_{part_no}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.pdf")
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
        out_path = os.path.join(TMP, f"inventory_report_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    y = h - margin
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, y, title); y -= 18
    c.setFont("Helvetica", 10); c.drawString(margin, y, f"Generated: {datetime.datetime.utcnow().isoformat()}Z"); y -= 14
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
        out_dir = os.path.join(TMP, f"barcode_preview_{part_no}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}")
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
# UI
# ---------------------------
class ImagePreviewDialog(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Barcode Preview")
        self.resize(700, 520)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); grid = QGridLayout(container)
        row = 0; col = 0
        for idx, p in enumerate(image_paths):
            lbl = QLabel(); pm = QPixmap(p)
            lbl.setPixmap(pm.scaledToWidth(320, Qt.SmoothTransformation))
            grid.addWidget(lbl, row, col)
            col += 1
            if col >= 2:
                col = 0; row += 1
        scroll.setWidget(container)
        layout.addWidget(scroll)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

# Tabs for other forms
def make_form_widget(fields):
    form = QFormLayout()
    for lab, widget in fields:
        form.addRow(lab, widget)
    return form

class CertifiedTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        self.set_no = QLineEdit(); self.part_no = QLineEdit(); self.item_desc = QLineEdit()
        self.denom_qty = QLineEdit(); self.qty_received = QSpinBox(); self.qty_received.setRange(0,100000)
        self.received_from = QLineEdit(); self.received_by = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        layout.addLayout(make_form_widget([
            ("Set No:", self.set_no), ("Part No:", self.part_no), ("Item Description:", self.item_desc),
            ("Denomination/Qty:", self.denom_qty), ("Qty Received:", self.qty_received), ("Received From:", self.received_from),
            ("Received By:", self.received_by), ("Remarks:", self.remarks)
        ]))
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addWidget(self.print_btn)
        layout.addLayout(btn_row)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","Set No","Part No","Qty Received","Created"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        save_certified_receipt(self.set_no.text().strip(), self.part_no.text().strip(), self.item_desc.text().strip(),
                               self.denom_qty.text().strip(), self.qty_received.value(), self.received_from.text().strip(),
                               self.received_by.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Certified receipt saved.")
        self.load(); self.on_clear()

    def on_clear(self):
        self.set_no.clear(); self.part_no.clear(); self.item_desc.clear(); self.denom_qty.clear(); self.qty_received.setValue(0)
        self.received_from.clear(); self.received_by.clear(); self.remarks.clear()

    def load(self):
        rows = list_certified_receipt()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[5] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[9] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0:
            QMessageBox.warning(self, "Select", "Select a record to print.")
            return
        id_ = self.table.item(cur,0).text()
        rows = _run("SELECT id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc FROM certified_receipt WHERE id = ?", (id_,), fetch=True)
        if not rows:
            QMessageBox.warning(self, "Not found", "Record not found.")
            return
        pdf = create_certified_receipt_pdf(rows[0])
        QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); print_pdf_shell(pdf)

class SparesIssueTab(QWidget):
    def __init__(self):
        super().__init__(); self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        self.sl_no = QLineEdit(); self.part_no = QLineEdit(); self.description = QLineEdit(); self.lf_no = QLineEdit()
        self.item = QLineEdit(); self.qty_issued = QSpinBox(); self.qty_issued.setRange(0,100000)
        self.balance = QSpinBox(); self.balance.setRange(0,100000); self.issued_to = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        layout.addLayout(make_form_widget([
            ("SL No:", self.sl_no), ("Part No:", self.part_no), ("Description:", self.description),
            ("LF No:", self.lf_no), ("Item:", self.item), ("Qty Issued:", self.qty_issued),
            ("Balance:", self.balance), ("Issued To:", self.issued_to), ("Remarks:", self.remarks)
        ]))
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addWidget(self.print_btn)
        layout.addLayout(btn_row)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","SL No","Part No","Qty Issued","Created"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        save_spares_issue(self.sl_no.text().strip(), self.part_no.text().strip(), self.description.text().strip(), self.lf_no.text().strip(), self.item.text().strip(), self.qty_issued.value(), self.balance.value(), self.issued_to.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Spares issue saved.")
        self.load(); self.on_clear()

    def on_clear(self):
        self.sl_no.clear(); self.part_no.clear(); self.description.clear(); self.lf_no.clear(); self.item.clear()
        self.qty_issued.setValue(0); self.balance.setValue(0); self.issued_to.clear(); self.remarks.clear()

    def load(self):
        rows = list_spares_issue()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[6] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[10] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0: QMessageBox.warning(self, "Select", "Select a record to print."); return
        id_ = self.table.item(cur,0).text()
        rows = _run("SELECT id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc FROM spares_issue WHERE id = ?", (id_,), fetch=True)
        if not rows: QMessageBox.warning(self, "Not found", "Record not found."); return
        pdf = create_spares_issue_pdf(rows[0]); QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); print_pdf_shell(pdf)

class DemandSupplyTab(QWidget):
    def __init__(self):
        super().__init__(); self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        self.patt_no = QLineEdit(); self.description = QLineEdit(); self.mand_dept = QLineEdit(); self.lf_no = QLineEdit()
        self.qty_req = QSpinBox(); self.qty_req.setRange(0,100000); self.qty_held = QSpinBox(); self.qty_held.setRange(0,100000)
        self.balance = QSpinBox(); self.balance.setRange(0,100000); self.location = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        layout.addLayout(make_form_widget([
            ("Pattern No:", self.patt_no), ("Description:", self.description), ("Mand/Dept:", self.mand_dept),
            ("LF No:", self.lf_no), ("Qty Required:", self.qty_req), ("Qty Held:", self.qty_held),
            ("Balance:", self.balance), ("Location:", self.location), ("Remarks:", self.remarks)
        ]))
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addWidget(self.print_btn)
        layout.addLayout(btn_row)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","Pattern No","Description","Qty Req","Created"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        save_demand_supply(self.patt_no.text().strip(), self.description.text().strip(), self.mand_dept.text().strip(), self.lf_no.text().strip(), self.qty_req.value(), self.qty_held.value(), self.balance.value(), self.location.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Demand saved.")
        self.load(); self.on_clear()

    def on_clear(self):
        self.patt_no.clear(); self.description.clear(); self.mand_dept.clear(); self.lf_no.clear(); self.qty_req.setValue(0); self.qty_held.setValue(0); self.balance.setValue(0); self.location.clear(); self.remarks.clear()

    def load(self):
        rows = list_demand_supply()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[5] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[10] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0: QMessageBox.warning(self, "Select", "Select a record to print."); return
        id_ = self.table.item(cur,0).text()
        rows = _run("SELECT id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc FROM demand_supply WHERE id = ?", (id_,), fetch=True)
        if not rows: QMessageBox.warning(self, "Not found", "Record not found."); return
        pdf = create_demand_supply_pdf(rows[0]); QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); print_pdf_shell(pdf)

# Main Window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INS - Warehouse Inventory")
        self.resize(1250, 840)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        pal = self.palette(); pal.setColor(QPalette.Window, QColor("#f4f7fb")); self.setPalette(pal)
        layout = QVBoxLayout(self)
        header = QLabel("INS"); header.setFont(QFont("Arial", 26, QFont.Bold)); header.setStyleSheet("color: #2d6cdf;"); layout.addWidget(header, alignment=Qt.AlignLeft)
        tabs = QTabWidget()
        # Inventory tab
        inv_tab = QWidget(); inv_layout = QVBoxLayout(inv_tab)
        ctrl = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Search Part No / Description / SNo.")
        self.add_btn = QPushButton("Add Item"); self.edit_btn = QPushButton("Edit Selected"); self.del_btn = QPushButton("Delete Selected")
        ctrl.addWidget(self.search); ctrl.addWidget(self.add_btn); ctrl.addWidget(self.edit_btn); ctrl.addWidget(self.del_btn)
        inv_layout.addLayout(ctrl)
        scan_group = QGroupBox("Scanner / Stock Use"); scan_layout = QHBoxLayout(); self.scan_input = QLineEdit(); self.scan_input.setPlaceholderText("Scan Part No here")
        self.scan_qty = QSpinBox(); self.scan_qty.setRange(1,100000); self.scan_qty.setValue(1); self.use_btn = QPushButton("Use (decrement)")
        scan_layout.addWidget(QLabel("Scanner:")); scan_layout.addWidget(self.scan_input); scan_layout.addWidget(QLabel("Qty:")); scan_layout.addWidget(self.scan_qty); scan_layout.addWidget(self.use_btn)
        scan_group.setLayout(scan_layout); inv_layout.addWidget(scan_group)
        self.table = QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["id","Part No","Description","Total Qty","Location/Bin","Remarks","Modified"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inv_layout.addWidget(self.table)
        bottom = QHBoxLayout()
        self.generate_labels_btn = QPushButton("Generate Labels for Selected"); self.print_sheet_btn = QPushButton("Print Form for Selected")
        self.report_pdf_btn = QPushButton("Inventory Report (PDF)"); self.export_csv_btn = QPushButton("Export CSV"); self.tx_report_btn = QPushButton("Transactions Report"); self.backup_btn = QPushButton("Run Backup Now")
        bottom.addWidget(self.generate_labels_btn); bottom.addWidget(self.print_sheet_btn); bottom.addWidget(self.report_pdf_btn); bottom.addWidget(self.export_csv_btn); bottom.addWidget(self.tx_report_btn); bottom.addWidget(self.backup_btn)
        inv_layout.addLayout(bottom)
        tabs.addTab(inv_tab, "Inventory Data Sheet")
        # other forms tabs
        tabs.addTab(CertifiedTab(), "Certified Receipt Voucher")
        tabs.addTab(SparesIssueTab(), "Spares Issue Voucher")
        tabs.addTab(DemandSupplyTab(), "Demand on Supply Office")
        layout.addWidget(tabs); self.setLayout(layout)

        # connect signals
        self.add_btn.clicked.connect(self.on_add); self.edit_btn.clicked.connect(self.on_edit); self.del_btn.clicked.connect(self.on_delete)
        self.search.textChanged.connect(self.on_search); self.use_btn.clicked.connect(self.on_use); self.scan_input.returnPressed.connect(self.on_scan_enter)
        self.generate_labels_btn.clicked.connect(self.on_generate_labels); self.print_sheet_btn.clicked.connect(self.on_print_form)
        self.report_pdf_btn.clicked.connect(self.on_generate_report); self.export_csv_btn.clicked.connect(self.on_export_csv)
        self.tx_report_btn.clicked.connect(self.on_transactions_report); self.backup_btn.clicked.connect(self.on_backup)

    def refresh_table(self, rows=None):
        if rows is None: rows = list_inventory()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            # r order: id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[4] or "")); self.table.setItem(i,2,QTableWidgetItem(r[5] or ""))
            self.table.setItem(i,3,QTableWidgetItem(str(r[16] or 0))); self.table.setItem(i,4,QTableWidgetItem(r[11] or "")); self.table.setItem(i,5,QTableWidgetItem(r[18] or ""))
            self.table.setItem(i,6,QTableWidgetItem(r[20] or ""))
        self.table.resizeRowsToContents()

    def on_add(self):
        dlg = QDialog(self); dlg.setWindowTitle("Add Item"); form = QFormLayout(dlg)
        s_no = QLineEdit(); sl_no_contract = QLineEdit(); set_patt_no = QLineEdit(); part_no = QLineEdit()
        description = QLineEdit(); denomination = QLineEdit(); type_ = QLineEdit()
        qty_per_gt = QSpinBox(); qty_per_gt.setRange(0,100000)
        mdnd_def = QLineEdit(); lf_no = QLineEdit(); location_bin = QLineEdit()
        received_from_whom = QLineEdit(); qty_received = QSpinBox(); qty_received.setRange(0,100000)
        issued_to_whom = QLineEdit(); qty_issued = QSpinBox(); qty_issued.setRange(0,100000)
        total_qty = QSpinBox(); total_qty.setRange(0,100000)
        balance = QSpinBox(); balance.setRange(0,100000)
        remarks = QTextEdit(); remarks.setFixedHeight(60)
        form.addRow("SNo.:", s_no); form.addRow("SL No of Contract:", sl_no_contract); form.addRow("Set Patt No:", set_patt_no)
        form.addRow("Part No:", part_no); form.addRow("Description:", description); form.addRow("Denomination:", denomination)
        form.addRow("Type:", type_); form.addRow("Qty Per GT:", qty_per_gt); form.addRow("MDND/DEF:", mdnd_def); form.addRow("LF No (MGT No.):", lf_no)
        form.addRow("Location/Bin:", location_bin); form.addRow("Received From Whom:", received_from_whom); form.addRow("Qty Received:", qty_received)
        form.addRow("Issued to Whom:", issued_to_whom); form.addRow("Qty Issued:", qty_issued); form.addRow("Total Qty:", total_qty)
        form.addRow("Balance:", balance); form.addRow("Remarks:", remarks)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); form.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            if not part_no.text().strip():
                QMessageBox.warning(self, "Validation", "Part No is required."); return
            tot = total_qty.value()
            if tot == 0:
                tot = qty_received.value() - qty_issued.value()
            add_inventory_record(s_no.text().strip(), sl_no_contract.text().strip(), set_patt_no.text().strip(), part_no.text().strip(),
                                 description.text().strip(), denomination.text().strip(), type_.text().strip(), qty_per_gt.value(),
                                 mdnd_def.text().strip(), lf_no.text().strip(), location_bin.text().strip(), received_from_whom.text().strip(),
                                 qty_received.value(), issued_to_whom.text().strip(), qty_issued.value(), tot, balance.value(), remarks.toPlainText().strip())
            QMessageBox.information(self, "Saved", "Item added."); self.refresh_table()

    def _selected_id(self):
        cur = self.table.currentRow()
        if cur < 0: return None
        item = self.table.item(cur, 0)
        return item.text() if item else None

    def on_edit(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a row to edit."); return
        rec = get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Not found", "Record not found."); return
        dlg = QDialog(self); dlg.setWindowTitle("Edit Item"); form = QFormLayout(dlg)
        s_no = QLineEdit(rec[1] or ""); sl_no_contract = QLineEdit(rec[2] or ""); set_patt_no = QLineEdit(rec[3] or "")
        part_no = QLineEdit(rec[4] or ""); description = QLineEdit(rec[5] or ""); denomination = QLineEdit(rec[6] or "")
        type_ = QLineEdit(rec[7] or ""); qty_per_gt = QSpinBox(); qty_per_gt.setRange(0,100000); qty_per_gt.setValue(int(rec[8] or 0))
        mdnd_def = QLineEdit(rec[9] or ""); lf_no = QLineEdit(rec[10] or ""); location_bin = QLineEdit(rec[11] or "")
        received_from_whom = QLineEdit(rec[12] or ""); qty_received = QSpinBox(); qty_received.setRange(0,100000); qty_received.setValue(int(rec[13] or 0))
        issued_to_whom = QLineEdit(rec[14] or ""); qty_issued = QSpinBox(); qty_issued.setRange(0,100000); qty_issued.setValue(int(rec[15] or 0))
        total_qty = QSpinBox(); total_qty.setRange(0,100000); total_qty.setValue(int(rec[16] or 0))
        balance = QSpinBox(); balance.setRange(0,100000); balance.setValue(int(rec[17] or 0))
        remarks = QTextEdit(rec[18] or ""); remarks.setFixedHeight(60)
        form.addRow("SNo.:", s_no); form.addRow("SL No of Contract:", sl_no_contract); form.addRow("Set Patt No:", set_patt_no)
        form.addRow("Part No:", part_no); form.addRow("Description:", description); form.addRow("Denomination:", denomination)
        form.addRow("Type:", type_); form.addRow("Qty Per GT:", qty_per_gt); form.addRow("MDND/DEF:", mdnd_def); form.addRow("LF No (MGT No.):", lf_no)
        form.addRow("Location/Bin:", location_bin); form.addRow("Received From Whom:", received_from_whom); form.addRow("Qty Received:", qty_received)
        form.addRow("Issued to Whom:", issued_to_whom); form.addRow("Qty Issued:", qty_issued); form.addRow("Total Qty:", total_qty)
        form.addRow("Balance:", balance); form.addRow("Remarks:", remarks)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); form.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            update_inventory(id_, s_no.text().strip(), sl_no_contract.text().strip(), set_patt_no.text().strip(), part_no.text().strip(),
                             description.text().strip(), denomination.text().strip(), type_.text().strip(), qty_per_gt.value(),
                             mdnd_def.text().strip(), lf_no.text().strip(), location_bin.text().strip(), received_from_whom.text().strip(),
                             qty_received.value(), issued_to_whom.text().strip(), qty_issued.value(), total_qty.value(), balance.value(), remarks.toPlainText().strip())
            QMessageBox.information(self, "Updated", "Record updated."); self.refresh_table()

    def on_delete(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a row to delete."); return
        if QMessageBox.question(self, "Confirm", "Delete selected record?") != QMessageBox.StandardButton.Yes: return
        delete_inventory(id_); QMessageBox.information(self, "Deleted", "Record deleted."); self.refresh_table()

    def on_search(self, text):
        if not text: self.refresh_table(); return
        rows = search_inventory(text); self.refresh_table(rows)

    def on_use(self):
        part_no = self.scan_input.text().strip(); qty = self.scan_qty.value()
        if not part_no: QMessageBox.warning(self, "Scanner", "Scan or enter Part No first."); return
        rec = get_inventory_by_partno(part_no)
        if not rec: QMessageBox.warning(self, "Not found", f"Part No {part_no} not in inventory."); self.scan_input.clear(); return
        adjust_qty_by_partno(part_no, -qty, reason="usage (manual)", source="scanner")
        QMessageBox.information(self, "Updated", f"Decremented {qty} from {part_no}."); self.scan_input.clear(); self.refresh_table()

    def on_scan_enter(self):
        part_no = self.scan_input.text().strip()
        if not part_no: return
        qty = self.scan_qty.value()
        rec = get_inventory_by_partno(part_no)
        if not rec: QMessageBox.warning(self, "Not found", f"Part No {part_no} not in inventory."); self.scan_input.clear(); return
        resp = QMessageBox.question(self, "Confirm Usage", f"Use {qty} of Part No {part_no} ({rec[5]})?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes: self.scan_input.clear(); return
        adjust_qty_by_partno(part_no, -qty, reason="usage (scanner)", source="scanner"); QMessageBox.information(self, "Updated", f"{qty} units deducted from {part_no}."); self.scan_input.clear(); self.refresh_table()

    def on_generate_labels(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select an item first."); return
        rec = get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Error", "Record not found."); return
        part_no = rec[4]; name = rec[5]; qty_default = rec[16] or 1
        count, ok = QInputDialog.getInt(self, "Labels count", "Number of labels to generate (per product):", value=qty_default, min=1, max=10000)
        if not ok: return
        image_paths = generate_barcode_images(part_no, name, count)
        dlg = ImagePreviewDialog(image_paths, parent=self); dlg.exec()
        pdf = create_labels_pdf(part_no, name, count)
        QMessageBox.information(self, "Labels", f"Labels PDF created: {pdf}. You can print it now with a label printer.")

    def on_print_form(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a record to print form."); return
        rec = get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Error", "Record not found."); return
        pdf = create_inventory_sheet_pdf(rec)
        # printer selection
        printers = enum_printers()
        if printers:
            printer, ok = QInputDialog.getItem(self, "Select Printer", "Printer:", printers, 0, False)
            if ok and printer:
                if os.path.exists(SUMATRA_PATH):
                    try: print_pdf_sumatra(pdf, printer_name=printer, sumatra_path=SUMATRA_PATH); return
                    except Exception as e: QMessageBox.warning(self, "Print error", str(e))
                # fallback to shell (may open print dialog)
                print_pdf_shell(pdf)
            else:
                print_pdf_shell(pdf)
        else:
            print_pdf_shell(pdf)
            QMessageBox.information(self, "Print", "Used default system print command (no printer list).")

    def on_generate_report(self):
        rows = list_inventory(); pdf = create_inventory_report_pdf(rows); QMessageBox.information(self, "Report", f"Inventory report created: {pdf}"); print_pdf_shell(pdf)

    def on_export_csv(self):
        rows = list_inventory(); path, _ = QFileDialog.getSaveFileName(self, "Save CSV", os.path.expanduser("~\\Desktop\\inventory_export.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["id","s_no","sl_no_contract","set_patt_no","part_no","description","denomination","type","qty_per_gt","mdnd_def","lf_no","location_bin","received_from_whom","qty_received","issued_to_whom","qty_issued","total_qty","balance","remarks","created_utc","modified_utc"])
            for r in rows: writer.writerow(list(r))
        QMessageBox.information(self, "Export", f"Exported CSV to {path}")

    def on_transactions_report(self):
        rows = list_transactions(limit=1000); path, _ = QFileDialog.getSaveFileName(self, "Save Transactions CSV", os.path.expanduser("~\\Desktop\\transactions.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["id","part_no","delta","tx_type","reason","source","created_utc"])
            for r in rows: writer.writerow(list(r))
        QMessageBox.information(self, "Saved", f"Transactions exported to {path}")

    def on_backup(self):
        try: backup_db(); QMessageBox.information(self, "Backup", f"Backup created in {BACKUP_DIR}")
        except Exception as e: QMessageBox.critical(self, "Backup error", str(e))

# ---------------------------
# CLI / Run
# ---------------------------
def run_migrations_only():
    print("Running migrations (ensure DB exists and columns are updated)...")
    ensure_db_and_migrate()
    print("Migrations complete.")
    print(f"DB path: {DB_PATH}")

def main():
    ensure_db_and_migrate()
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "migrate":
        run_migrations_only(); sys.exit(0)
    main()
