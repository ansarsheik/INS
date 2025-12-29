# main_enhanced.py
import sys, os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QInputDialog, QFileDialog, QSpinBox, QDialog, QFormLayout, QTextEdit,
    QTabWidget, QGroupBox, QScrollArea, QGridLayout, QDialogButtonBox, QListWidget
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
from PySide6.QtCore import Qt

import db_forms, pdf_and_print, backup

db_forms.ensure_db()

# --- small helper dialogs ---
class ImagePreviewDialog(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Barcode Preview")
        self.resize(600, 500)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); grid = QGridLayout(container)
        row = 0; col = 0
        for idx, p in enumerate(image_paths):
            lbl = QLabel(); pm = QPixmap(p)
            lbl.setPixmap(pm.scaledToWidth(280, Qt.SmoothTransformation))
            grid.addWidget(lbl, row, col)
            col += 1
            if col >= 2:
                col = 0; row += 1
        scroll.setWidget(container)
        layout.addWidget(scroll)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

# --- Reusable small form widget builder ---
def make_form_widget(fields):
    """
    fields: list of tuples (label, widget_instance)
    returns QFormLayout
    """
    form = QFormLayout()
    for lab, widget in fields:
        form.addRow(lab, widget)
    return form

# --- Tabs for other forms ---
class CertifiedTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        # inputs
        self.set_no = QLineEdit(); self.part_no = QLineEdit(); self.item_desc = QLineEdit()
        self.denom_qty = QLineEdit(); self.qty_received = QSpinBox(); self.qty_received.setRange(0,100000)
        self.received_from = QLineEdit(); self.received_by = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        form = make_form_widget([
            ("Set No:", self.set_no), ("Part No:", self.part_no), ("Item Description:", self.item_desc),
            ("Denomination/Qty:", self.denom_qty), ("Qty Received:", self.qty_received), ("Received From:", self.received_from),
            ("Received By:", self.received_by), ("Remarks:", self.remarks)
        ])
        layout.addLayout(form)
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addWidget(self.print_btn)
        layout.addLayout(btn_row)
        # table
        self.table = QTableWidget(); self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["id","Set No","Part No","Qty Received","Created"])
        self.table.hideColumn(0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        # signals
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        db_forms.save_certified_receipt(self.set_no.text().strip(), self.part_no.text().strip(), self.item_desc.text().strip(),
                                       self.denom_qty.text().strip(), self.qty_received.value(), self.received_from.text().strip(),
                                       self.received_by.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Certified receipt saved.")
        self.load(); self.on_clear()

    def on_clear(self):
        self.set_no.clear(); self.part_no.clear(); self.item_desc.clear(); self.denom_qty.clear(); self.qty_received.setValue(0)
        self.received_from.clear(); self.received_by.clear(); self.remarks.clear()

    def load(self):
        rows = db_forms.list_certified_receipt()
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
        # retrieve record (quick select)
        rows = db_forms._run("SELECT id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc FROM certified_receipt WHERE id = ?", (id_,), fetch=True)
        if not rows:
            QMessageBox.warning(self, "Not found", "Record not found.")
            return
        pdf = pdf_and_print.create_certified_receipt_pdf(rows[0])
        QMessageBox.information(self, "PDF", f"PDF created: {pdf}. Use File->Print or choose printer from print dialog.")
        pdf_and_print.print_pdf_shell(pdf)

class SparesIssueTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.sl_no = QLineEdit(); self.part_no = QLineEdit(); self.description = QLineEdit(); self.lf_no = QLineEdit()
        self.item = QLineEdit(); self.qty_issued = QSpinBox(); self.qty_issued.setRange(0,100000)
        self.balance = QSpinBox(); self.balance.setRange(0,100000); self.issued_to = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        form = make_form_widget([
            ("SL No:", self.sl_no), ("Part No:", self.part_no), ("Description:", self.description),
            ("LF No:", self.lf_no), ("Item:", self.item), ("Qty Issued:", self.qty_issued),
            ("Balance:", self.balance), ("Issued To:", self.issued_to), ("Remarks:", self.remarks)
        ])
        layout.addLayout(form)
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addWidget(self.print_btn)
        layout.addLayout(btn_row)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","SL No","Part No","Qty Issued","Created"]); self.table.hideColumn(0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        db_forms.save_spares_issue(self.sl_no.text().strip(), self.part_no.text().strip(), self.description.text().strip(),
                                  self.lf_no.text().strip(), self.item.text().strip(), self.qty_issued.value(), self.balance.value(),
                                  self.issued_to.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Spares issue saved.")
        self.load(); self.on_clear()

    def on_clear(self):
        self.sl_no.clear(); self.part_no.clear(); self.description.clear(); self.lf_no.clear(); self.item.clear()
        self.qty_issued.setValue(0); self.balance.setValue(0); self.issued_to.clear(); self.remarks.clear()

    def load(self):
        rows = db_forms.list_spares_issue()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[6] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[10] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0:
            QMessageBox.warning(self, "Select", "Select a record to print.")
            return
        id_ = self.table.item(cur,0).text()
        rows = db_forms._run("SELECT id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc FROM spares_issue WHERE id = ?", (id_,), fetch=True)
        if not rows:
            QMessageBox.warning(self, "Not found", "Record not found.")
            return
        pdf = pdf_and_print.create_spares_issue_pdf(rows[0])
        QMessageBox.information(self, "PDF", f"PDF created: {pdf}.")
        pdf_and_print.print_pdf_shell(pdf)

class DemandSupplyTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.patt_no = QLineEdit(); self.description = QLineEdit(); self.mand_dept = QLineEdit(); self.lf_no = QLineEdit()
        self.qty_req = QSpinBox(); self.qty_req.setRange(0,100000); self.qty_held = QSpinBox(); self.qty_held.setRange(0,100000)
        self.balance = QSpinBox(); self.balance.setRange(0,100000); self.location = QLineEdit(); self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        form = make_form_widget([
            ("Pattern No:", self.patt_no), ("Description:", self.description), ("Mand/Dept:", self.mand_dept),
            ("LF No:", self.lf_no), ("Qty Required:", self.qty_req), ("Qty Held:", self.qty_held),
            ("Balance:", self.balance), ("Location:", self.location), ("Remarks:", self.remarks)
        ])
        layout.addLayout(form)
        btn_row = QHBoxLayout(); self.save_btn = QPushButton("Save"); self.clear_btn = QPushButton("Clear"); self.print_btn = QPushButton("Print Selected")
        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.clear_btn); btn_row.addWidget(self.print_btn)
        layout.addLayout(btn_row)
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["id","Pattern No","Description","Qty Req","Created"]); self.table.hideColumn(0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.save_btn.clicked.connect(self.on_save); self.clear_btn.clicked.connect(self.on_clear); self.print_btn.clicked.connect(self.on_print)
        self.load()

    def on_save(self):
        db_forms.save_demand_supply(self.patt_no.text().strip(), self.description.text().strip(), self.mand_dept.text().strip(),
                                   self.lf_no.text().strip(), self.qty_req.value(), self.qty_held.value(), self.balance.value(),
                                   self.location.text().strip(), self.remarks.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Demand saved.")
        self.load(); self.on_clear()

    def on_clear(self):
        self.patt_no.clear(); self.description.clear(); self.mand_dept.clear(); self.lf_no.clear(); self.qty_req.setValue(0)
        self.qty_held.setValue(0); self.balance.setValue(0); self.location.clear(); self.remarks.clear()

    def load(self):
        rows = db_forms.list_demand_supply()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or ""))
            self.table.setItem(i,2,QTableWidgetItem(r[2] or "")); self.table.setItem(i,3,QTableWidgetItem(str(r[5] or "")))
            self.table.setItem(i,4,QTableWidgetItem(r[10] or ""))
        self.table.resizeRowsToContents()

    def on_print(self):
        cur = self.table.currentRow()
        if cur < 0:
            QMessageBox.warning(self, "Select", "Select a record to print.")
            return
        id_ = self.table.item(cur,0).text()
        rows = db_forms._run("SELECT id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc FROM demand_supply WHERE id = ?", (id_,), fetch=True)
        if not rows:
            QMessageBox.warning(self, "Not found", "Record not found.")
            return
        pdf = pdf_and_print.create_demand_supply_pdf(rows[0])
        QMessageBox.information(self, "PDF", f"PDF created: {pdf}."); pdf_and_print.print_pdf_shell(pdf)

# --- Main window updated to include new tabs and label preview ---
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INS - Warehouse Inventory")
        self.resize(1200,820)
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
        self.search = QLineEdit(); self.search.setPlaceholderText("Search SKU / name / description")
        self.add_btn = QPushButton("Add Item"); self.edit_btn = QPushButton("Edit Selected"); self.del_btn = QPushButton("Delete Selected")
        ctrl.addWidget(self.search); ctrl.addWidget(self.add_btn); ctrl.addWidget(self.edit_btn); ctrl.addWidget(self.del_btn)
        inv_layout.addLayout(ctrl)
        scan_group = QGroupBox("Scanner / Stock Use"); scan_layout = QHBoxLayout(); self.scan_input = QLineEdit(); self.scan_input.setPlaceholderText("Scan SKU here")
        self.scan_qty = QSpinBox(); self.scan_qty.setRange(1,100000); self.scan_qty.setValue(1); self.use_btn = QPushButton("Use (decrement)")
        scan_layout.addWidget(QLabel("Scanner:")); scan_layout.addWidget(self.scan_input); scan_layout.addWidget(QLabel("Qty:")); scan_layout.addWidget(self.scan_qty); scan_layout.addWidget(self.use_btn)
        scan_group.setLayout(scan_layout); inv_layout.addWidget(scan_group)
        self.table = QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["id","SKU","Name","Qty","Location","Remarks","Modified"]); self.table.hideColumn(0); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inv_layout.addWidget(self.table)
        bottom = QHBoxLayout()
        self.generate_labels_btn = QPushButton("Generate Labels for Selected"); self.print_sheet_btn = QPushButton("Print Form for Selected")
        self.report_pdf_btn = QPushButton("Inventory Report (PDF)"); self.export_csv_btn = QPushButton("Export CSV"); self.tx_report_btn = QPushButton("Transactions Report"); self.backup_btn = QPushButton("Run Backup Now")
        bottom.addWidget(self.generate_labels_btn); bottom.addWidget(self.print_sheet_btn); bottom.addWidget(self.report_pdf_btn); bottom.addWidget(self.export_csv_btn); bottom.addWidget(self.tx_report_btn); bottom.addWidget(self.backup_btn)
        inv_layout.addLayout(bottom)

        tabs.addTab(inv_tab, "Inventory Data Sheet")
        # add other forms as tabs
        tabs.addTab(CertifiedTab(), "Certified Receipt Voucher")
        tabs.addTab(SparesIssueTab(), "Spares Issue Voucher")
        tabs.addTab(DemandSupplyTab(), "Demand on Supply Office")
        layout.addWidget(tabs)
        self.setLayout(layout)

        # signals (inventory)
        self.add_btn.clicked.connect(self.on_add); self.edit_btn.clicked.connect(self.on_edit); self.del_btn.clicked.connect(self.on_delete)
        self.search.textChanged.connect(self.on_search); self.use_btn.clicked.connect(self.on_use); self.scan_input.returnPressed.connect(self.on_scan_enter)
        self.generate_labels_btn.clicked.connect(self.on_generate_labels); self.print_sheet_btn.clicked.connect(self.on_print_form)
        self.report_pdf_btn.clicked.connect(self.on_generate_report); self.export_csv_btn.clicked.connect(self.on_export_csv)
        self.tx_report_btn.clicked.connect(self.on_transactions_report); self.backup_btn.clicked.connect(self.on_backup)

    def refresh_table(self, rows=None):
        if rows is None: rows = db_forms.list_inventory()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i,0,QTableWidgetItem(r[0])); self.table.setItem(i,1,QTableWidgetItem(r[1] or "")); self.table.setItem(i,2,QTableWidgetItem(r[2] or ""))
            self.table.setItem(i,3,QTableWidgetItem(str(r[6] or 0))); self.table.setItem(i,4,QTableWidgetItem(r[7] or "")); self.table.setItem(i,5,QTableWidgetItem(r[11] or ""))
            self.table.setItem(i,6,QTableWidgetItem(r[13] or ""))
        self.table.resizeRowsToContents()

    # (inventory CRUD + other functions unchanged from previous main_enhanced)
    def on_add(self):
        dlg = QDialog(self); dlg.setWindowTitle("Add Item"); form = QFormLayout(dlg)
        sku = QLineEdit(); name = QLineEdit(); desc = QLineEdit(); denom = QLineEdit(); type_ = QLineEdit()
        qty = QSpinBox(); qty.setRange(0,100000); location = QLineEdit(); received = QLineEdit(); issued_to = QLineEdit(); balance = QSpinBox(); balance.setRange(0,100000); remarks = QTextEdit(); remarks.setFixedHeight(60)
        form.addRow("SKU:", sku); form.addRow("Name:", name); form.addRow("Description:", desc)
        form.addRow("Denomination:", denom); form.addRow("Type:", type_); form.addRow("Qty:", qty)
        form.addRow("Location:", location); form.addRow("Received From:", received); form.addRow("Issued To:", issued_to)
        form.addRow("Balance:", balance); form.addRow("Remarks:", remarks)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); form.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            if not sku.text().strip() or not name.text().strip():
                QMessageBox.warning(self, "Validation", "SKU and Name are required."); return
            db_forms.add_inventory(sku.text().strip(), name.text().strip(), desc.text().strip(), denom.text().strip(), type_.text().strip(),
                                   qty.value(), location.text().strip(), received.text().strip(), issued_to.text().strip(), balance.value(), remarks.toPlainText().strip())
            QMessageBox.information(self, "Saved", "Item added."); self.refresh_table()

    def _selected_id(self):
        cur = self.table.currentRow()
        if cur < 0: return None
        item = self.table.item(cur, 0)
        return item.text() if item else None

    def on_edit(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a row to edit."); return
        rec = db_forms.get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Not found", "Record not found."); return
        dlg = QDialog(self); dlg.setWindowTitle("Edit Item"); form = QFormLayout(dlg)
        sku = QLineEdit(rec[1]); name = QLineEdit(rec[2]); desc = QLineEdit(rec[3] or ""); denom = QLineEdit(rec[4] or ""); type_ = QLineEdit(rec[5] or "")
        qty = QSpinBox(); qty.setRange(0,100000); qty.setValue(rec[6] or 0); location = QLineEdit(rec[7] or ""); received = QLineEdit(rec[8] or ""); issued_to = QLineEdit(rec[9] or "")
        balance = QSpinBox(); balance.setRange(0,100000); balance.setValue(rec[10] or 0); remarks = QTextEdit(rec[11] or ""); remarks.setFixedHeight(60)
        form.addRow("SKU:", sku); form.addRow("Name:", name); form.addRow("Description:", desc)
        form.addRow("Denomination:", denom); form.addRow("Type:", type_); form.addRow("Qty:", qty)
        form.addRow("Location:", location); form.addRow("Received From:", received); form.addRow("Issued To:", issued_to)
        form.addRow("Balance:", balance); form.addRow("Remarks:", remarks)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); form.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:
            db_forms.update_inventory(id_, sku.text().strip(), name.text().strip(), desc.text().strip(), denom.text().strip(), type_.text().strip(),
                                     qty.value(), location.text().strip(), received.text().strip(), issued_to.text().strip(), balance.value(), remarks.toPlainText().strip())
            QMessageBox.information(self, "Updated", "Record updated."); self.refresh_table()

    def on_delete(self):
        id_ = self._selected_id(); 
        if not id_: QMessageBox.warning(self, "Select", "Select a row to delete."); return
        if QMessageBox.question(self, "Confirm", "Delete selected record?") != QMessageBox.StandardButton.Yes: return
        db_forms.delete_inventory(id_); QMessageBox.information(self, "Deleted", "Record deleted."); self.refresh_table()

    def on_search(self, text):
        if not text: self.refresh_table(); return
        rows = db_forms.search_inventory(text); self.refresh_table(rows)

    def on_use(self):
        sku = self.scan_input.text().strip(); qty = self.scan_qty.value()
        if not sku: QMessageBox.warning(self, "Scanner", "Scan or enter SKU first."); return
        rec = db_forms.get_inventory_by_sku(sku)
        if not rec: QMessageBox.warning(self, "Not found", f"SKU {sku} not in inventory."); self.scan_input.clear(); return
        db_forms.adjust_qty_by_sku(sku, -qty, reason="usage (manual)", source="scanner"); QMessageBox.information(self, "Updated", f"Decremented {qty} from {sku}."); self.scan_input.clear(); self.refresh_table()

    def on_scan_enter(self):
        sku = self.scan_input.text().strip()
        if not sku: return
        qty = self.scan_qty.value()
        rec = db_forms.get_inventory_by_sku(sku)
        if not rec: QMessageBox.warning(self, "Not found", f"SKU {sku} not in inventory."); self.scan_input.clear(); return
        resp = QMessageBox.question(self, "Confirm Usage", f"Use {qty} of SKU {sku} ({rec[2]})?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes: self.scan_input.clear(); return
        db_forms.adjust_qty_by_sku(sku, -qty, reason="usage (scanner)", source="scanner"); QMessageBox.information(self, "Updated", f"{qty} units deducted from {sku}."); self.scan_input.clear(); self.refresh_table()

    def on_generate_labels(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select an item first."); return
        rec = db_forms.get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Error", "Record not found."); return
        sku = rec[1]; name = rec[2]; qty_default = rec[6] or 1
        count, ok = QInputDialog.getInt(self, "Labels count", "Number of labels to generate (per product):", value=qty_default, min=1, max=10000)
        if not ok: return
        # generate barcode images (preview)
        image_paths = pdf_and_print.generate_barcode_images(sku, name, count)
        dlg = ImagePreviewDialog(image_paths, parent=self)
        dlg.exec()
        # also create PDF for printing if user wants
        pdf = pdf_and_print.create_labels_pdf(sku, name, count)
        QMessageBox.information(self, "Labels", f"Labels PDF created: {pdf}. Use Print to print the labels.")

    def on_print_form(self):
        id_ = self._selected_id()
        if not id_: QMessageBox.warning(self, "Select", "Select a record to print form."); return
        rec = db_forms.get_inventory_by_id(id_)
        if not rec: QMessageBox.warning(self, "Error", "Record not found."); return
        pdf = pdf_and_print.create_inventory_sheet_pdf(rec)
        # show printer selection
        printers = pdf_and_print.enum_printers()
        if printers:
            printer, ok = QInputDialog.getItem(self, "Select Printer", "Printer:", printers, 0, False)
            if ok and printer:
                sumatra = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"
                try:
                    if os.path.exists(sumatra): pdf_and_print.print_pdf_sumatra(pdf, printer_name=printer, sumatra_path=sumatra)
                    else: pdf_and_print.print_pdf_shell(pdf)
                except Exception as e: QMessageBox.critical(self, "Print error", str(e))
            else:
                pdf_and_print.print_pdf_shell(pdf)
        else:
            pdf_and_print.print_pdf_shell(pdf); QMessageBox.information(self, "Print", "Used default system print command.")

    def on_generate_report(self):
        rows = db_forms.list_inventory(); pdf = pdf_and_print.create_inventory_report_pdf(rows)
        QMessageBox.information(self, "Report", f"Inventory report created: {pdf}\nAttempting to print..."); pdf_and_print.print_pdf_shell(pdf)

    def on_export_csv(self):
        rows = db_forms.list_inventory(); path, _ = QFileDialog.getSaveFileName(self, "Save CSV", os.path.expanduser("~\\Desktop\\inventory_export.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["id","sku","name","description","denomination","type","qty","location","received_from","issued_to","balance","remarks","created_utc","modified_utc"])
            for r in rows: writer.writerow(list(r))
        QMessageBox.information(self, "Export", f"Exported CSV to {path}")

    def on_transactions_report(self):
        rows = db_forms.list_transactions(limit=1000); path, _ = QFileDialog.getSaveFileName(self, "Save Transactions CSV", os.path.expanduser("~\\Desktop\\transactions.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["id","sku","delta","tx_type","reason","source","created_utc"])
            for r in rows: writer.writerow(list(r))
        QMessageBox.information(self, "Saved", f"Transactions exported to {path}")

    def on_backup(self):
        try: backup.backup_db(); QMessageBox.information(self, "Backup", "Backup created in C:\\ProgramData\\MyWarehouse\\backups")
        except Exception as e: QMessageBox.critical(self, "Backup error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv); w = MainWindow(); w.show(); sys.exit(app.exec())
