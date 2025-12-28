# main_enhanced.py
import sys, os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QInputDialog, QFileDialog, QSpinBox, QDialog, QFormLayout, QTextEdit,
    QTabWidget, QGroupBox
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtCore import Qt

import db_forms, pdf_and_print, backup

db_forms.ensure_db()

class EditDialog(QDialog):
    def __init__(self, record=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Inventory" if record else "Add Inventory")
        self.rec = record
        self.layout = QFormLayout(self)
        self.sku = QLineEdit(); self.name = QLineEdit(); self.desc = QLineEdit()
        self.denom = QLineEdit(); self.type_ = QLineEdit()
        self.qty = QSpinBox(); self.qty.setRange(0,1000000)
        self.location = QLineEdit(); self.received = QLineEdit(); self.issued_to = QLineEdit()
        self.balance = QSpinBox(); self.balance.setRange(0,1000000)
        self.remarks = QTextEdit(); self.remarks.setFixedHeight(60)
        self.layout.addRow("SKU:", self.sku)
        self.layout.addRow("Name:", self.name)
        self.layout.addRow("Description:", self.desc)
        self.layout.addRow("Denomination:", self.denom)
        self.layout.addRow("Type:", self.type_)
        self.layout.addRow("Qty:", self.qty)
        self.layout.addRow("Location:", self.location)
        self.layout.addRow("Received From:", self.received)
        self.layout.addRow("Issued To:", self.issued_to)
        self.layout.addRow("Balance:", self.balance)
        self.layout.addRow("Remarks:", self.remarks)
        btns = QHBoxLayout()
        self.save_btn = QPushButton("Save"); self.cancel_btn = QPushButton("Cancel")
        btns.addWidget(self.save_btn); btns.addWidget(self.cancel_btn)
        self.layout.addRow(btns)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        if record:
            # record tuple: id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks...
            self.sku.setText(record[1]); self.name.setText(record[2]); self.desc.setText(record[3] or "")
            self.denom.setText(record[4] or ""); self.type_.setText(record[5] or "")
            self.qty.setValue(record[6] or 0); self.location.setText(record[7] or "")
            self.received.setText(record[8] or ""); self.issued_to.setText(record[9] or "")
            self.balance.setValue(record[10] or 0); self.remarks.setPlainText(record[11] or "")

    def values(self):
        return {
            "sku": self.sku.text().strip(),
            "name": self.name.text().strip(),
            "description": self.desc.text().strip(),
            "denomination": self.denom.text().strip(),
            "type": self.type_.text().strip(),
            "qty": self.qty.value(),
            "location": self.location.text().strip(),
            "received_from": self.received.text().strip(),
            "issued_to": self.issued_to.text().strip(),
            "balance": self.balance.value(),
            "remarks": self.remarks.toPlainText().strip()
        }

class FormsTab(QWidget):
    """Simple placeholder tab for the other forms: Certified Receipt, Spares Issue, Demand Supply"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("<b>Other Forms</b>")
        layout.addWidget(label)
        # you can extend these to full form UI similar to earlier scaffolds
        self.setLayout(layout)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INS - Warehouse Inventory")
        self.resize(1200,780)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#f4f7fb"))
        self.setPalette(pal)
        layout = QVBoxLayout(self)
        header = QLabel("INS")
        header.setFont(QFont("Arial", 26, QFont.Bold))
        header.setStyleSheet("color: #2d6cdf;")
        layout.addWidget(header, alignment=Qt.AlignLeft)

        tabs = QTabWidget()
        # Inventory tab
        inv_tab = QWidget(); inv_layout = QVBoxLayout(inv_tab)
        # controls
        ctrl = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Search SKU / name / description")
        self.add_btn = QPushButton("Add Item"); self.edit_btn = QPushButton("Edit Selected"); self.del_btn = QPushButton("Delete Selected")
        ctrl.addWidget(self.search); ctrl.addWidget(self.add_btn); ctrl.addWidget(self.edit_btn); ctrl.addWidget(self.del_btn)
        inv_layout.addLayout(ctrl)
        # scanner group
        scan_group = QGroupBox("Scanner / Stock Use")
        scan_layout = QHBoxLayout(); self.scan_input = QLineEdit(); self.scan_input.setPlaceholderText("Scan SKU here")
        self.scan_qty = QSpinBox(); self.scan_qty.setRange(1,100000); self.scan_qty.setValue(1)
        self.use_btn = QPushButton("Use (decrement)")
        scan_layout.addWidget(QLabel("Scanner:")); scan_layout.addWidget(self.scan_input); scan_layout.addWidget(QLabel("Qty:")); scan_layout.addWidget(self.scan_qty); scan_layout.addWidget(self.use_btn)
        scan_group.setLayout(scan_layout)
        inv_layout.addWidget(scan_group)
        # table
        self.table = QTableWidget(); self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["id","SKU","Name","Qty","Location","Remarks","Modified"])
        self.table.hideColumn(0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inv_layout.addWidget(self.table)
        # bottom actions
        bottom = QHBoxLayout()
        self.generate_labels_btn = QPushButton("Generate Labels for Selected")
        self.print_sheet_btn = QPushButton("Print Form for Selected")
        self.report_pdf_btn = QPushButton("Inventory Report (PDF)")
        self.export_csv_btn = QPushButton("Export CSV")
        self.tx_report_btn = QPushButton("Transactions Report")
        self.backup_btn = QPushButton("Run Backup Now")
        bottom.addWidget(self.generate_labels_btn); bottom.addWidget(self.print_sheet_btn); bottom.addWidget(self.report_pdf_btn)
        bottom.addWidget(self.export_csv_btn); bottom.addWidget(self.tx_report_btn); bottom.addWidget(self.backup_btn)
        inv_layout.addLayout(bottom)

        tabs.addTab(inv_tab, "Inventory Data Sheet")
        tabs.addTab(FormsTab(), "Other Vouchers & Forms")
        layout.addWidget(tabs)
        self.setLayout(layout)

        # signals
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit)
        self.del_btn.clicked.connect(self.on_delete)
        self.search.textChanged.connect(self.on_search)
        self.use_btn.clicked.connect(self.on_use)
        self.scan_input.returnPressed.connect(self.on_scan_enter)
        self.generate_labels_btn.clicked.connect(self.on_generate_labels)
        self.print_sheet_btn.clicked.connect(self.on_print_form)
        self.report_pdf_btn.clicked.connect(self.on_generate_report)
        self.export_csv_btn.clicked.connect(self.on_export_csv)
        self.tx_report_btn.clicked.connect(self.on_transactions_report)
        self.backup_btn.clicked.connect(self.on_backup)

    def refresh_table(self, rows=None):
        if rows is None:
            rows = db_forms.list_inventory()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r[0]))
            self.table.setItem(i, 1, QTableWidgetItem(r[1] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r[2] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(str(r[6] or 0)))
            self.table.setItem(i, 4, QTableWidgetItem(r[7] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r[11] or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r[13] or ""))
        self.table.resizeRowsToContents()

    def on_add(self):
        dlg = EditDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            if not v["sku"] or not v["name"]:
                QMessageBox.warning(self, "Validation", "SKU and Name required.")
                return
            try:
                db_forms.add_inventory(v["sku"], v["name"], v["description"], v["denomination"], v["type"], v["qty"], v["location"], v["received_from"], v["issued_to"], v["balance"], v["remarks"])
                QMessageBox.information(self, "Saved", "Item added.")
                self.refresh_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add: {e}")

    def _selected_id(self):
        cur = self.table.currentRow()
        if cur < 0: return None
        item = self.table.item(cur, 0)
        return item.text() if item else None

    def on_edit(self):
        id_ = self._selected_id()
        if not id_:
            QMessageBox.warning(self, "Select", "Select a row to edit.")
            return
        rec = db_forms.get_inventory_by_id(id_)
        dlg = EditDialog(record=rec, parent=self)
        if dlg.exec() == QDialog.Accepted:
            v = dlg.values()
            try:
                db_forms.update_inventory(id_, v["sku"], v["name"], v["description"], v["denomination"], v["type"], v["qty"], v["location"], v["received_from"], v["issued_to"], v["balance"], v["remarks"])
                QMessageBox.information(self, "Updated", "Record updated.")
                self.refresh_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Update failed: {e}")

    def on_delete(self):
        id_ = self._selected_id()
        if not id_:
            QMessageBox.warning(self, "Select", "Select a row to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete selected record?") != QMessageBox.StandardButton.Yes:
            return
        try:
            db_forms.delete_inventory(id_)
            QMessageBox.information(self, "Deleted", "Record deleted.")
            self.refresh_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def on_search(self, text):
        if not text:
            self.refresh_table()
            return
        rows = db_forms.search_inventory(text)
        self.refresh_table(rows)

    def on_use(self):
        sku = self.scan_input.text().strip()
        qty = self.scan_qty.value()
        if not sku:
            QMessageBox.warning(self, "Scanner", "Scan or enter SKU first.")
            return
        rec = db_forms.get_inventory_by_sku(sku)
        if not rec:
            QMessageBox.warning(self, "Not found", f"SKU {sku} not in inventory.")
            self.scan_input.clear(); return
        # decrement qty
        db_forms.adjust_qty_by_sku(sku, -qty, reason="usage (manual)", source="scanner")
        QMessageBox.information(self, "Updated", f"Decremented {qty} from {sku}.")
        self.scan_input.clear()
        self.refresh_table()

    def on_scan_enter(self):
        """Called when the scanner inputs value and presses Enter (or user presses Enter)"""
        sku = self.scan_input.text().strip()
        if not sku:
            return
        # default qty from spinner
        qty = self.scan_qty.value()
        rec = db_forms.get_inventory_by_sku(sku)
        if not rec:
            QMessageBox.warning(self, "Not found", f"SKU {sku} not in inventory.")
            self.scan_input.clear(); return
        # confirm quick dialog
        resp = QMessageBox.question(self, "Confirm Usage", f"Use {qty} of SKU {sku} ({rec[2]})?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            self.scan_input.clear(); return
        db_forms.adjust_qty_by_sku(sku, -qty, reason="usage (scanner)", source="scanner")
        QMessageBox.information(self, "Updated", f"{qty} units deducted from {sku}.")
        self.scan_input.clear()
        self.refresh_table()

    def on_generate_labels(self):
        id_ = self._selected_id()
        if not id_:
            QMessageBox.warning(self, "Select", "Select an item first.")
            return
        rec = db_forms.get_inventory_by_id(id_)
        if not rec:
            QMessageBox.warning(self, "Error", "Record not found.")
            return
        sku = rec[1]; name = rec[2]; qty = rec[6] or 1
        # allow user to override label count
        count, ok = QInputDialog.getInt(self, "Labels count", "Number of labels to generate (per product):", value=qty, min=1, max=10000)
        if not ok:
            return
        pdf = pdf_and_print.create_labels_pdf(sku, name, count)
        QMessageBox.information(self, "Labels", f"Labels PDF created: {pdf}\nChoose printer to print.")
        # choose printer
        printers = pdf_and_print.enum_printers()
        if printers:
            printer, ok = QInputDialog.getItem(self, "Select Printer", "Printer:", printers, 0, False)
            if ok and printer:
                # try SumatraPDF if installed, else warn and call shell
                sumatra = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"
                try:
                    if os.path.exists(sumatra):
                        pdf_and_print.print_pdf_sumatra(pdf, printer_name=printer, sumatra_path=sumatra)
                    else:
                        # fallback: printing to named printer via Sumatra is preferred; otherwise use Shell (default viewer)
                        QMessageBox.information(self, "Printer", "SumatraPDF not found: will use default system print (may open dialog). Install SumatraPDF for silent named-printer printing.")
                        pdf_and_print.print_pdf_shell(pdf)
                except Exception as e:
                    QMessageBox.critical(self, "Print error", str(e))
        else:
            # no printers found: fallback to shell
            pdf_and_print.print_pdf_shell(pdf)

    def on_print_form(self):
        id_ = self._selected_id()
        if not id_:
            QMessageBox.warning(self, "Select", "Select a record to print form.")
            return
        rec = db_forms.get_inventory_by_id(id_)
        pdf = pdf_and_print.create_inventory_sheet_pdf(rec)
        # show user a printer selection dialog (list installed printers)
        printers = pdf_and_print.enum_printers()
        if printers:
            printer, ok = QInputDialog.getItem(self, "Select Printer", "Printer:", printers, 0, False)
            if ok and printer:
                sumatra = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"
                try:
                    if os.path.exists(sumatra):
                        pdf_and_print.print_pdf_sumatra(pdf, printer_name=printer, sumatra_path=sumatra)
                    else:
                        # if Sumatra not present, use Shell (which will usually open print preview dialog)
                        pdf_and_print.print_pdf_shell(pdf)
                except Exception as e:
                    QMessageBox.critical(self, "Print error", str(e))
            else:
                # user cancelled printer selection -> fallback to shell preview/print
                pdf_and_print.print_pdf_shell(pdf)
        else:
            # no printers found
            pdf_and_print.print_pdf_shell(pdf)
            QMessageBox.information(self, "Print", "Used default system print command (no printer list available).")

    def on_generate_report(self):
        rows = db_forms.list_inventory()
        pdf = pdf_and_print.create_inventory_report_pdf(rows)
        QMessageBox.information(self, "Report", f"Inventory report created: {pdf}\nAttempting to print...")
        pdf_and_print.print_pdf_shell(pdf)

    def on_export_csv(self):
        rows = db_forms.list_inventory()
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", os.path.expanduser("~\\Desktop\\inventory_export.csv"), "CSV files (*.csv)")
        if not path: return
        # simple CSV
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id","sku","name","description","denomination","type","qty","location","received_from","issued_to","balance","remarks","created_utc","modified_utc"])
            for r in rows:
                writer.writerow(list(r))
        QMessageBox.information(self, "Export", f"Exported CSV to {path}")

    def on_transactions_report(self):
        rows = db_forms.list_transactions(limit=1000)
        # write to CSV quickly and open location
        path, _ = QFileDialog.getSaveFileName(self, "Save Transactions CSV", os.path.expanduser("~\\Desktop\\transactions.csv"), "CSV files (*.csv)")
        if not path: return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id","sku","delta","tx_type","reason","source","created_utc"])
            for r in rows:
                writer.writerow(list(r))
        QMessageBox.information(self, "Saved", f"Transactions exported to {path}")

    def on_backup(self):
        try:
            backup.backup_db()
            QMessageBox.information(self, "Backup", "Backup created in C:\\ProgramData\\MyWarehouse\\backups")
        except Exception as e:
            QMessageBox.critical(self, "Backup error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())
