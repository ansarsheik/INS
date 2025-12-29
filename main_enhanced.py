# main_enhanced.py
"""
Modern-styled single-file desktop app (PySide6).
Everything functional as before — but with a modern CSS-like look & feel.
"""

import sys, os, sqlite3, tempfile, datetime, shutil, subprocess
from uuid import uuid4

# UI
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QInputDialog, QFileDialog, QSpinBox, QDialog, QFormLayout, QTextEdit,
    QTabWidget, QGroupBox, QScrollArea, QGridLayout, QDialogButtonBox, QFrame
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
from PySide6.QtCore import Qt

# PDF & barcode libs
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from barcode import Code128
from barcode.writer import ImageWriter

# Paths & constants
DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"
BACKUP_DIR = r"C:\ProgramData\MyWarehouse\backups"
TMP = tempfile.gettempdir()
SUMATRA_PATH = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"

# ---------------------------
# App stylesheet (modern CSS-like)
# ---------------------------
APP_STYLE = """
/* --- App background --- */
QWidget {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:1,
        stop:0 #f5f7fb, stop:1 #eef3fb);
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial;
    font-size: 11px;
    color: #222;
}

/* Header */
QLabel#AppHeader {
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    padding: 14px 18px;
    border-radius: 10px;
    background: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #3b82f6, stop:1 #2563eb);
    margin-bottom: 12px;
    min-height: 48px;
}

/* Card containers */
QFrame.card {
    background: #ffffff;
    border-radius: 12px;
    padding: 12px;
    border: 1px solid rgba(30,40,60,0.04);
    /* subtle shadow via border + background difference */
}

/* Buttons */
QPushButton {
    background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 #ffffff, stop:1 #f3f4f6);
    border: 1px solid rgba(0,0,0,0.08);
    padding: 8px 12px;
    border-radius: 10px;
    min-height: 30px;
}
QPushButton#primary {
    background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 #2563eb, stop:1 #1e40af);
    color: white;
    border: none;
    font-weight: 600;
}
QPushButton#primary:hover { background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 #1e60f0, stop:1 #164bb5); }
QPushButton#primary:pressed { background: #123e9b; }

QPushButton#danger {
    background: #ffe9e9;
    color: #a11;
    border: 1px solid #ffd6d6;
}
QPushButton:hover { transform: scale(1.0); }

/* Inputs */
QLineEdit, QTextEdit, QSpinBox {
    background: #ffffff;
    border: 1px solid rgba(30,40,60,0.08);
    border-radius: 8px;
    padding: 6px 8px;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
    border: 1px solid #60a5fa;
    box-shadow: 0 0 0 4px rgba(96,165,250,0.08);
}

/* TabWidget style */
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #334155;
    padding: 10px 14px;
    margin-right: 6px;
    border-radius: 8px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 #fff, stop:1 #f8fafc);
    border: 1px solid rgba(16,24,40,0.06);
    color: #0f172a;
    font-weight: 600;
}

/* Table */
QTableWidget {
    background: transparent;
    alternate-background-color: #fbfdff;
    gridline-color: rgba(2,6,23,0.03);
}
QHeaderView::section {
    background: transparent;
    padding: 8px;
    border: none;
    color: #0f172a;
    font-weight: 600;
}
QTableWidget::item {
    padding: 8px;
}
QTableWidget::item:selected {
    background: rgba(37,99,235,0.12);
}

/* Small helpers */
QGroupBox { font-weight: 600; color: #0f172a; margin-top: 6px; }
QScrollArea { background: transparent; }
QDialog { background: #f8fafc; }
"""

# ---------------------------
# DB + helpers (same as earlier)
# ---------------------------
def ensure_db_and_migrate():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
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
        descrip
