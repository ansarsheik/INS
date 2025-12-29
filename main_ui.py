# main_ui.py
"""
UI layer for INS inventory app.
This file holds all UI code and styling. It imports functionality from core.py.
Run: python main_ui.py
"""

import sys, os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QInputDialog, QFileDialog, QSpinBox, QDialog, QFormLayout, QTextEdit,
    QTabWidget, QGroupBox, QScrollArea, QGridLayout, QDialogButtonBox, QFrame
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
from PySide6.QtCore import Qt

# import functionality from core
import core

# app stylesheet (modern)
APP_STYLE = """
QWidget {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #f5f7fb, stop:1 #eef3fb);
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial;
    font-size: 11px; color: #222;
}
QLabel#AppHeader {
    font-size: 26px; font-weight: 700; color: #ffffff; padding: 14px 18px;
    border-radius: 10px; background: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #3b82f6, stop:1 #2563eb);
    margin-bottom: 12px; min-height: 48px;
}
QFrame.card { background: #ffffff; border-radius: 12px; padding: 12px; border: 1px solid rgba(30,40,60,0.04); }
QPushButton { background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 #ffffff, stop:1 #f3f4f6); border: 1px solid rgba(0,0,0,0.08); padding: 8px 12px; border-radius: 10px; min-height: 30px; }
QPushButton#primary { background: qlineargradient(x1:0 y1:0, x2:0 y2:1, stop:0 #2563eb, stop:1 #1e40af); color: white; border: none; font-weight: 600; }
QLineEdit, QTextEdit, QSpinBox { background: #ffffff; border: 1px solid rgba(30,40,60,0.08); border-radius: 8px; padding: 6px 8px; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus { border: 1px solid #60a5fa; box-shadow: 0 0 0 4px rgba(96,165,250,0.08); }
QTabWidget::pane { border: none; background: transparent; }
QHeaderView::section { background: transparent; padding: 8px; border: none; color: #0f172a; font-weight: 600; }
QTableWidget::item { padding: 8px; }
QTableWidget::item:selected { background: rgba(37,99,235,0.12); }
"""

# small helper to create QFormLayout from pairs
def make_form_widget(fields):
    form = QFormLayout()
    for lab, widget in fields:
        form.addRow(lab, widget)
    return form

# image preview dialog for barcode images
class ImagePreviewDialog(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Barcode Preview")
        self.resize(760, 540)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); grid = QGridLayout(container)
        row = col = 0
        for idx, p in enumerate(image_paths):
            lbl = QLabel(); pm = QPixmap(p)
            lbl.setPixmap(pm.scaledToWidth(360, Qt.SmoothTransformation))
            grid.addWidget(lbl, row, col, alignment=Qt.AlignCenter)
            col += 1
            if col >= 2: col = 0; row += 1
        scroll.setWidget(container); layout.addWidget(scroll)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject); layout.addWidget(btns)

# Tabs implementations — they use core.* functions for data & PDF generation
class CertifiedTab(QWidget):
    def __init__(self):
        super().__init__(); self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        card = QFrame(); card.setProperty("class","card"); card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        self.set_no = QLineEdit(); self.part_no = QLineEdit(); self.item_desc = QLineEdit()
        self.denom_qty = QLineEdit(); self.qty_received = QSpinBox(); self.qty_received.setRange(0,100000)
        self.received_from = QLineEdit(); self.received_by = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        card_layout.addLayout(make_form_widget([
            ("Set No:", self.set_no), ("Part No:", self.part_no), ("Item Description:", self.item_desc),
            ("Denomination/Qty:", self.denom_qty), ("Qty Received:", self.qty_received), ("Received From:", self.received_from),
            ("Received By:", self.received_by), ("Remarks:", self.remarks)
        ]))
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.save_btn.setObjectName("primary")
        self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addStretch(); btn_row.addWidget(self.print_btn)
        card_layout.addLayout(btn_row)
        layout.addWidget(card)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","Set No","Part No","Qty Received","Created"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        core.save_certified_receipt(self.set_no.text().strip(), self.part_no.text().strip(), self.item_desc.text().strip(),
                                    self.denom_qty.text().strip(), self.qty_received.value(), self.received_from.text().strip(),
                                    self.received_by.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Certified receipt saved."); self.load(); self.on_clear()

    def on_clear(self):
        self.set_no.clear(); self.part_no.clear(); self.item_desc.clear(); self.denom_qty.clear(); self.qty_received.setValue(0)
        self.received_from.clear(); self.received_by.clear(); self.remarks.clear()

    def load(self):
        rows = core.list_certified_receipt(); self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[5] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[9] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0: QMessageBox.warning(self, "Select", "Select a record to print."); return
        id_ = self.table.item(cur,0).text()
        rows = core._run("SELECT id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc FROM certified_receipt WHERE id = ?", (id_,), fetch=True)
        if not rows: QMessageBox.warning(self, "Not found", "Record not found."); return
        pdf = core.create_certified_receipt_pdf(rows[0]); QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); core.print_pdf_shell(pdf)

class SparesIssueTab(QWidget):
    def __init__(self):
        super().__init__(); self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        card = QFrame(); card.setProperty("class","card"); card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        self.sl_no = QLineEdit(); self.part_no = QLineEdit(); self.description = QLineEdit(); self.lf_no = QLineEdit()
        self.item = QLineEdit(); self.qty_issued = QSpinBox(); self.qty_issued.setRange(0,100000)
        self.balance = QSpinBox(); self.balance.setRange(0,100000); self.issued_to = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        card_layout.addLayout(make_form_widget([
            ("SL No:", self.sl_no), ("Part No:", self.part_no), ("Description:", self.description),
            ("LF No:", self.lf_no), ("Item:", self.item), ("Qty Issued:", self.qty_issued),
            ("Balance:", self.balance), ("Issued To:", self.issued_to), ("Remarks:", self.remarks)
        ]))
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.save_btn.setObjectName("primary"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addStretch(); btn_row.addWidget(self.print_btn)
        card_layout.addLayout(btn_row); layout.addWidget(card)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","SL No","Part No","Qty Issued","Created"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        core.save_spares_issue(self.sl_no.text().strip(), self.part_no.text().strip(), self.description.text().strip(), self.lf_no.text().strip(), self.item.text().strip(), self.qty_issued.value(), self.balance.value(), self.issued_to.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Spares issue saved."); self.load(); self.on_clear()

    def on_clear(self):
        self.sl_no.clear(); self.part_no.clear(); self.description.clear(); self.lf_no.clear(); self.item.clear()
        self.qty_issued.setValue(0); self.balance.setValue(0); self.issued_to.clear(); self.remarks.clear()

    def load(self):
        rows = core.list_spares_issue(); self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[6] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[10] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0: QMessageBox.warning(self, "Select", "Select a record to print."); return
        id_ = self.table.item(cur,0).text()
        rows = core._run("SELECT id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc FROM spares_issue WHERE id = ?", (id_,), fetch=True)
        if not rows: QMessageBox.warning(self, "Not found", "Record not found."); return
        pdf = core.create_spares_issue_pdf(rows[0]); QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); core.print_pdf_shell(pdf)

class DemandSupplyTab(QWidget):
    def __init__(self):
        super().__init__(); self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        card = QFrame(); card.setProperty("class","card"); card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        self.patt_no = QLineEdit(); self.description = QLineEdit(); self.mand_dept = QLineEdit(); self.lf_no = QLineEdit()
        self.qty_req = QSpinBox(); self.qty_req.setRange(0,100000); self.qty_held = QSpinBox(); self.qty_held.setRange(0,100000)
        self.balance = QSpinBox(); self.balance.setRange(0,100000); self.location = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        card_layout.addLayout(make_form_widget([
            ("Pattern No:", self.patt_no), ("Description:", self.description), ("Mand/Dept:", self.mand_dept),
            ("LF No:", self.lf_no), ("Qty Required:", self.qty_req), ("Qty Held:", self.qty_held),
            ("Balance:", self.balance), ("Location:", self.location), ("Remarks:", self.remarks)
        ]))
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.save_btn.setObjectName("primary"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addStretch(); btn_row.addWidget(self.print_btn)
        card_layout.addLayout(btn_row); layout.addWidget(card)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","Pattern No","Description","Qty Req","Created"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        core.save_demand_supply(self.patt_no.text().strip(), self.description.text().strip(), self.mand_dept.text().strip(), self.lf_no.text().strip(), self.qty_req.value(), self.qty_held.value(), self.balance.value(), self.location.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Demand saved."); self.load(); self.on_clear()

    def on_clear(self):
        self.patt_no.clear(); self.description.clear(); self.mand_dept.clear(); self.lf_no.clear(); self.qty_req.setValue(0); self.qty_held.setValue(0); self.balance.setValue(0); self.location.clear(); self.remarks.clear()

    def load(self):
        rows = core.list_demand_supply(); self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or "")); self.table.setItem(i,2,QTableWidgetItem(r[2] or ""))
            self.table.setItem(i,3,QTableWidgetItem(str(r[5] or ""))); self.table.setItem(i,4,QTableWidgetItem(r[10] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0: QMessageBox.warning(self, "Select", "Select a record to print."); return
        id_ = self.table.item(cur,0).text()
        rows = core._run("SELECT id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc FROM demand_supply WHERE id = ?", (id_,), fetch=True)
        if not rows: QMessageBox.warning(self, "Not found", "Record not found."); return
        pdf = core.create_demand_supply_pdf(rows[0]); QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); core.print_pdf_shell(pdf)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INS - Warehouse Inventory")
        self.resize(1280, 860)
        self._build_ui()
        core.ensure_db_and_migrate()
        self.refresh_table()

    def _build_ui(self):
        pal = self.palette(); pal.setColor(QPalette.Window, QColor("#f5f7fb")); self.setPalette(pal)
        main = QVBoxLayout(self)

        header = QLabel("INS"); header.setObjectName("AppHeader"); header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_frame = QFrame(); h_layout = QHBoxLayout(header_frame); h_layout.addWidget(header); h_layout.addStretch()
        main.addWidget(header_frame)

        tabs = QTabWidget(); tabs.setObjectName("MainTabs")
        # Inventory tab
        inv_tab = QWidget(); inv_layout = QVBoxLayout(inv_tab)
        top_card = QFrame(); top_card.setProperty("class","card"); top_card.setFrameShape(QFrame.StyledPanel); top_card_layout = QHBoxLayout(top_card)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search Part No / Description / SNo."); self.search.setMinimumWidth(360)
        self.add_btn = QPushButton("Add Item"); self.add_btn.setObjectName("primary"); self.edit_btn = QPushButton("Edit Selected"); self.del_btn = QPushButton("Delete Selected")
        top_card_layout.addWidget(self.search); top_card_layout.addStretch(); top_card_layout.addWidget(self.add_btn); top_card_layout.addWidget(self.edit_btn); top_card_layout.addWidget(self.del_btn)
        inv_layout.addWidget(top_card)

        scan_card = QFrame(); scan_card.setProperty("class","card"); scan_card.setFrameShape(QFrame.StyledPanel)
        scan_layout = QHBoxLayout(scan_card); self.scan_input = QLineEdit(); self.scan_input.setPlaceholderText("Scan Part No here"); self.scan_input.setMinimumWidth(340)
        self.scan_qty = QSpinBox(); self.scan_qty.setRange(1,100000); self.scan_qty.setValue(1); self.use_btn = QPushButton("Use (decrement)"); self.use_btn.setObjectName("primary")
        scan_layout.addWidget(QLabel("Scanner:")); scan_layout.addWidget(self.scan_input); scan_layout.addWidget(QLabel("Qty:")); scan_layout.addWidget(self.scan_qty); scan_layout.addStretch(); scan_layout.addWidget(self.use_btn)
        inv_layout.addWidget(scan_card)

        self.table = QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["id","Part No","Description","Total Qty","Location/Bin","Remarks","Modified"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inv_layout.addWidget(self.table)

        bottom_card = QFrame(); bottom_card.setProperty("class","card"); bottom_card.setFrameShape(QFrame.StyledPanel); bottom_layout = QHBoxLayout(bottom_card)
        self.generate_labels_btn = QPushButton("Generate Labels for Selected"); self.generate_labels_btn.setObjectName("primary")
        self.print_sheet_btn = QPushButton("Print Form for Selected"); self.report_pdf_btn = QPushButton("Inventory Report (PDF)")
        self.export_csv_btn = QPushButton("Export CSV"); self.tx_report_btn = QPushButton("Transactions Report"); self.backup_btn = QPushButton("Run Backup Now")
        bottom_layout.addWidget(self.generate_labels_btn); bottom_layout.addWidget(self.print_sheet_btn); bottom_layout.addWidget(self.report_pdf_btn); bottom_layout.addWidget(self.export_csv_btn); bottom_layout.addWidget(self.tx_report_btn); bottom_layout.addStretch(); bottom_layout.addWidget(self.backup_btn)
        inv_layout.addWidget(bottom_card)

        tabs.addTab(inv_tab, "Inventory Data Sheet")
        tabs.addTab(CertifiedTab(), "Certified Receipt Voucher")
        tabs.addTab(SparesIssueTab(), "Spares Issue Voucher")
        tabs.addTab(DemandSupplyTab(), "Demand on Supply Office")
        main.addWidget(tabs); self.setLayout(main)

        # signals
        self.add_btn.clicked.connect(self.on_add); self.edit_btn.clicked.connect(self.on_edit); self.del_btn.clicked.connect(self.on_delete)
        self.search.textChanged.connect(self.on_search); self.use_btn.clicked.connect(self.on_use); self.scan_input.returnPressed.connect(self.on_scan_enter)
        self.generate_labels_btn.clicked.connect(self.on_generate_labels); self.print_sheet_btn.clicked.connect(self.on_print_form)
        self.report_pdf_btn.clicked.connect(self.on_generate_report); self.export_csv_btn.clicked.connect(self.on_export_csv)
        self.tx_report_btn.clicked.connect(self.on_transactions_report); self.backup_btn.clicked.connect(self.on_backup)

    def refresh_table(self, rows=None):
        if rows is None: rows = core.list_inventory()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            # r order: id,s_no,sl_no_contract,set_patt_no,part_no,description,denomination,type,qty_per_gt,mdnd_def,lf_no,location_bin,received_from_whom,qty_received,issued_to_whom,qty_issued,total_qty,balance,remarks,created_utc,modified_utc
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[4] or "")); self.table.setItem(i,2,QTableWidgetItem(r[5] or ""))
            self.table.setItem(i,3,QTableWidgetItem(str(r[16] or 0))); self.table.setItem(i,4,QTableWidgetItem(r[11] or "")); self.table.setItem(i,5,QTableWidgetItem(r[18] or ""))
            self.table.setItem(i,6,QTableWidgetItem(r[20] or ""))
        self.table.resizeRowsToContents()

    def on_add(self):
        dlg = QDialog(self); dlg.setWindowTitle("Add Item"); dlg.setMinimumWidth(720)
        form = QFormLayout(dlg)
        s_no = QLineEdit(); sl_no_contract = QLineEdit(); set_patt_no = QLineEdit(); part_no = QLineEdit()
        description = QLineEdit(); denomination = QLineEdit(); type_ = QLineEdit()
        qty_per_gt = QSpinBox(); qty_per_gt.setRange(0,100000)
        mdnd_def = QLineEdit(); lf_no = QLineEdit(); location_bin = QLineEdit()
        received_from_whom = QLineEdit(); qty_received = QSpinBox(); qty_received.setRange(0,100000)
        issued_to_whom = QLineEdit(); qty_issued = QSpinBox(); qty_issued.setRange(0,100000)
        total_qty = QSpinBox(); total_qty.setRange(0,100000)
        balance = QSpinBox(); balance.setRange(0,100000)
        remarks = QTextEdit(); remarks.setFixedHeight(80)
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
            core.add_inventory_record(s_no.text().strip(), sl_no_contract.text().strip(), set_patt_no.text().strip(), part_no.text().strip(),
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
        rec = core.get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Not found", "Record not found."); return
        dlg = QDialog(self); dlg.setWindowTitle("Edit Item"); dlg.setMinimumWidth(720)
        form = QFormLayout(dlg)
        s_no = QLineEdit(rec[1] or ""); sl_no_contract = QLineEdit(rec[2] or ""); set_patt_no = QLineEdit(rec[3] or "")
        part_no = QLineEdit(rec[4] or ""); description = QLineEdit(rec[5] or ""); denomination = QLineEdit(rec[6] or "")
        type_ = QLineEdit(rec[7] or ""); qty_per_gt = QSpinBox(); qty_per_gt.setRange(0,100000); qty_per_gt.setValue(int(rec[8] or 0))
        mdnd_def = QLineEdit(rec[9] or ""); lf_no = QLineEdit(rec[10] or ""); location_bin = QLineEdit(rec[11] or "")
        received_from_whom = QLineEdit(rec[12] or ""); qty_received = QSpinBox(); qty_received.setRange(0,100000); qty_received.setValue(int(rec[13] or 0))
        issued_to_whom = QLineEdit(rec[14] or ""); qty_issued = QSpinBox(); qty_issued.setRange(0,100000); qty_issued.setValue(int(rec[15] or 0))
        total_qty = QSpinBox(); total_qty.setRange(0,100000); total_qty.setValue(int(rec[16] or 0))
        balance = QSpinBox(); balance.setRange(0,100000); balance.setValue(int(rec[17] or 0))
        remarks = QTextEdit(rec[18] or ""); remarks.setFixedHeight(80)
        form.addRow("SNo.:", s_no); form.addRow("SL No of Contract:", sl_no_contract); form.addRow("Set Patt No:", set_patt_no)
        form.addRow("Part No:", part_no); form.addRow("Description:", description); form.addRow("Denomination:", denomination)
        form.addRow("Type:", type_); form.addRow("Qty Per GT:", qty_per_gt); form.addRow("MDND/DEF:", mdnd_def); form.addRow("LF No (MGT No.):", lf_no)
        form.addRow("Location/Bin:", location_bin); form.addRow("Received From Whom:", received_from_whom); form.addRow("Qty Received:", qty_received)
        form.addRow("Issued to Whom:", issued_to_whom); form.addRow("Qty Issued:", qty_issued); form.addRow("Total Qty:", total_qty)
        form.addRow("Balance:", balance); form.addRow("Remarks:", remarks)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); form.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            core.update_inventory(id_, s_no.text().strip(), sl_no_contract.text().strip(), set_patt_no.text().strip(), part_no.text().strip(),
                             description.text().strip(), denomination.text().strip(), type_.text().strip(), qty_per_gt.value(),
                             mdnd_def.text().strip(), lf_no.text().strip(), location_bin.text().strip(), received_from_whom.text().strip(),
                             qty_received.value(), issued_to_whom.text().strip(), qty_issued.value(), total_qty.value(), balance.value(), remarks.toPlainText().strip())
            QMessageBox.information(self, "Updated", "Record updated."); self.refresh_table()

    def on_delete(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a row to delete."); return
        if QMessageBox.question(self, "Confirm", "Delete selected record?") != QMessageBox.StandardButton.Yes: return
        core.delete_inventory(id_); QMessageBox.information(self, "Deleted", "Record deleted."); self.refresh_table()

    def on_search(self, text):
        if not text: self.refresh_table(); return
        rows = core.search_inventory(text); self.refresh_table(rows)

    def on_use(self):
        part_no = self.scan_input.text().strip(); qty = self.scan_qty.value()
        if not part_no: QMessageBox.warning(self, "Scanner", "Scan or enter Part No first."); return
        rec = core.get_inventory_by_partno(part_no)
        if not rec: QMessageBox.warning(self, "Not found", f"Part No {part_no} not in inventory."); self.scan_input.clear(); return
        core.adjust_qty_by_partno(part_no, -qty, reason="usage (manual)", source="scanner")
        QMessageBox.information(self, "Updated", f"Decremented {qty} from {part_no}."); self.scan_input.clear(); self.refresh_table()

    def on_scan_enter(self):
        part_no = self.scan_input.text().strip()
        if not part_no: return
        qty = self.scan_qty.value()
        rec = core.get_inventory_by_partno(part_no)
        if not rec: QMessageBox.warning(self, "Not found", f"Part No {part_no} not in inventory."); self.scan_input.clear(); return
        resp = QMessageBox.question(self, "Confirm Usage", f"Use {qty} of Part No {part_no} ({rec[5]})?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes: self.scan_input.clear(); return
        core.adjust_qty_by_partno(part_no, -qty, reason="usage (scanner)", source="scanner"); QMessageBox.information(self, "Updated", f"{qty} units deducted from {part_no}."); self.scan_input.clear(); self.refresh_table()

    def on_generate_labels(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select an item first."); return
        rec = core.get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Error", "Record not found."); return
        part_no = rec[4]; name = rec[5]; qty_default = rec[16] or 1
        count, ok = QInputDialog.getInt(self, "Labels count", "Number of labels to generate (per product):", value=qty_default, min=1, max=10000)
        if not ok: return
        image_paths = core.generate_barcode_images(part_no, name, count)
        dlg = ImagePreviewDialog(image_paths, parent=self); dlg.exec()
        pdf = core.create_labels_pdf(part_no, name, count)
        QMessageBox.information(self, "Labels", f"Labels PDF created: {pdf}. You can print it now with a label printer.")

    def on_print_form(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a record to print form."); return
        rec = core.get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Error", "Record not found."); return
        pdf = core.create_inventory_sheet_pdf(rec)
        printers = core.enum_printers()
        if printers:
            printer, ok = QInputDialog.getItem(self, "Select Printer", "Printer:", printers, 0, False)
            if ok and printer:
                if os.path.exists(core.SUMATRA_PATH):
                    try: core.print_pdf_sumatra(pdf, printer_name=printer, sumatra_path=core.SUMATRA_PATH); return
                    except Exception as e: QMessageBox.warning(self, "Print error", str(e))
                core.print_pdf_shell(pdf)
            else:
                core.print_pdf_shell(pdf)
        else:
            core.print_pdf_shell(pdf)
            QMessageBox.information(self, "Print", "Used default system print command (no printer list).")

    def on_generate_report(self):
        rows = core.list_inventory(); pdf = core.create_inventory_report_pdf(rows); QMessageBox.information(self, "Report", f"Inventory report created: {pdf}"); core.print_pdf_shell(pdf)

    def on_export_csv(self):
        rows = core.list_inventory(); path, _ = QFileDialog.getSaveFileName(self, "Save CSV", os.path.expanduser("~\\Desktop\\inventory_export.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["id","s_no","sl_no_contract","set_patt_no","part_no","description","denomination","type","qty_per_gt","mdnd_def","lf_no","location_bin","received_from_whom","qty_received","issued_to_whom","qty_issued","total_qty","balance","remarks","created_utc","modified_utc"])
            for r in rows: writer.writerow(list(r))
        QMessageBox.information(self, "Export", f"Exported CSV to {path}")

    def on_transactions_report(self):
        rows = core.list_transactions(limit=1000); path, _ = QFileDialog.getSaveFileName(self, "Save Transactions CSV", os.path.expanduser("~\\Desktop\\transactions.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["id","part_no","delta","tx_type","reason","source","created_utc"])
            for r in rows: writer.writerow(list(r))
        QMessageBox.information(self, "Saved", f"Transactions exported to {path}")

    def on_backup(self):
        try: core.backup_db(); QMessageBox.information(self, "Backup", f"Backup created in {core.BACKUP_DIR}")
        except Exception as e: QMessageBox.critical(self, "Backup error", str(e))

# ---------------------------
# Run
# ---------------------------
def main():
    core.ensure_db_and_migrate()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
