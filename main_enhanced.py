# main_enhanced.py
import sys, os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QInputDialog,
    QFileDialog, QSpinBox, QDialog, QFormLayout, QTextEdit
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtCore import Qt
import db_forms, pdf_and_print

# Ensure DB exists
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
            # record tuple ordering from DB: id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks...
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INS - Warehouse Inventory")
        self.resize(1100,700)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#f4f7fb"))
        self.setPalette(pal)
        layout = QVBoxLayout(self)
        header = QLabel("INS")
        header.setFont(QFont("Arial", 22, QFont.Bold))
        header.setStyleSheet("color: #2d6cdf;")
        layout.addWidget(header, alignment=Qt.AlignLeft)
        # top controls
        ctrl = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Search SKU / name / description")
        self.add_btn = QPushButton("Add Item"); self.edit_btn = QPushButton("Edit Selected"); self.del_btn = QPushButton("Delete Selected")
        self.scan_input = QLineEdit(); self.scan_input.setPlaceholderText("Scanner input (scan SKU here) - Enter quantity then press Use")
        self.scan_qty = QSpinBox(); self.scan_qty.setRange(1,100000); self.scan_qty.setValue(1)
        self.use_btn = QPushButton("Use (decrement stock)")
        ctrl.addWidget(self.search); ctrl.addWidget(self.add_btn); ctrl.addWidget(self.edit_btn); ctrl.addWidget(self.del_btn)
        layout.addLayout(ctrl)
        scan_row = QHBoxLayout(); scan_row.addWidget(QLabel("Scanner:")); scan_row.addWidget(self.scan_input); scan_row.addWidget(QLabel("Qty:")); scan_row.addWidget(self.scan_qty); scan_row.addWidget(self.use_btn)
        layout.addLayout(scan_row)
        # table
        self.table = QTableWidget(); self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["id","SKU","Name","Qty","Location","Remarks"])
        self.table.hideColumn(0)  # hide id
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        # bottom actions - labels, reports, export
        bottom = QHBoxLayout()
        self.generate_labels_btn = QPushButton("Generate Labels for Selected")
        self.print_sheet_btn = QPushButton("Print Form for Selected")
        self.report_pdf_btn = QPushButton("Inventory Report (PDF)")
        self.export_csv_btn = QPushButton("Export CSV")
        bottom.addWidget(self.generate_labels_btn); bottom.addWidget(self.print_sheet_btn); bottom.addWidget(self.report_pdf_btn); bottom.addWidget(self.export_csv_btn)
        layout.addLayout(bottom)
        # connect signals
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit)
        self.del_btn.clicked.connect(self.on_delete)
        self.search.textChanged.connect(self.on_search)
        self.use_btn.clicked.connect(self.on_use)
        self.generate_labels_btn.clicked.connect(self.on_generate_labels)
        self.print_sheet_btn.clicked.connect(self.on_print_form)
        self.report_pdf_btn.clicked.connect(self.on_generate_report)
        self.export_csv_btn.clicked.connect(self.on_export_csv)

    def refresh_table(self, rows=None):
        if rows is None:
            rows = db_forms.list_inventory()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            # r: id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc
            self.table.setItem(i, 0, QTableWidgetItem(r[0]))
            self.table.setItem(i, 1, QTableWidgetItem(r[1] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r[2] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(str(r[6] or 0)))
            self.table.setItem(i, 4, QTableWidgetItem(r[7] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r[11] or ""))
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
            return
        # decrement qty
        db_forms.adjust_qty_by_sku(sku, -qty)
        QMessageBox.information(self, "Updated", f"Decremented {qty} from {sku}.")
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
        # create labels pdf with qty pages
        pdf = pdf_and_print.create_labels_pdf(sku, name, qty)
        QMessageBox.information(self, "Labels", f"Labels PDF created: {pdf}\nSending to printer...")
        try:
            ok = pdf_and_print.print_pdf_shell(pdf)
            if not ok:
                QMessageBox.warning(self, "Print", "Shell print failed. Consider installing SumatraPDF and printing via Sumatra.")
        except Exception as e:
            QMessageBox.critical(self, "Print error", str(e))

    def on_print_form(self):
        id_ = self._selected_id()
        if not id_:
            QMessageBox.warning(self, "Select", "Select a record to print form.")
            return
        rec = db_forms.get_inventory_by_id(id_)
        pdf = pdf_and_print.create_inventory_sheet_pdf(rec)
        QMessageBox.information(self, "Form", f"Form PDF: {pdf}\nSending to printer...")
        try:
            pdf_and_print.print_pdf_shell(pdf)
        except Exception as e:
            QMessageBox.critical(self, "Print error", str(e))

    def on_generate_report(self):
        rows = db_forms.list_inventory()
        pdf = pdf_and_print.create_inventory_report_pdf(rows)
        QMessageBox.information(self, "Report", f"Inventory report created: {pdf}\nSending to printer...")
        try:
            pdf_and_print.print_pdf_shell(pdf)
        except Exception as e:
            QMessageBox.critical(self, "Print error", str(e))

    def on_export_csv(self):
        rows = db_forms.list_inventory()
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", os.path.expanduser("~\\Desktop\\inventory_export.csv"), "CSV files (*.csv)")
        if not path: return
        try:
            pdf_and_print.export_inventory_csv(rows, path)
            QMessageBox.information(self, "Export", f"Exported CSV to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())
