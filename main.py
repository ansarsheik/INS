# main.py
import sys, os
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLineEdit, QListWidget, QLabel, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt
import db_init
from label_pdf import create_temp_labels_pdf
from inventory_pdf import create_inventory_pdf
from print_windows import print_pdf_default, print_pdf_sumatra
import tempfile

APP_TMP = tempfile.gettempdir()

class MainWin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warehouse Inventory - Desktop")
        self.resize(800, 500)
        self.layout = QVBoxLayout()
        # input row
        row = QHBoxLayout()
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Item name")
        self.sku_input = QLineEdit(); self.sku_input.setPlaceholderText("SKU (optional)")
        self.qty_input = QSpinBox(); self.qty_input.setRange(1, 10000); self.qty_input.setValue(1)
        row.addWidget(QLabel("Name:")); row.addWidget(self.name_input)
        row.addWidget(QLabel("SKU:")); row.addWidget(self.sku_input)
        row.addWidget(QLabel("Qty:")); row.addWidget(self.qty_input)
        self.add_btn = QPushButton("Add Item")
        row.addWidget(self.add_btn)
        self.layout.addLayout(row)
        # list and actions
        self.listw = QListWidget()
        self.layout.addWidget(self.listw)
        actions = QHBoxLayout()
        self.gen_labels_btn = QPushButton("Generate & Print Labels for Selected")
        self.print_inventory_btn = QPushButton("Print Inventory View")
        self.backup_btn = QPushButton("Run Backup Now")
        actions.addWidget(self.gen_labels_btn)
        actions.addWidget(self.print_inventory_btn)
        actions.addWidget(self.backup_btn)
        self.layout.addLayout(actions)
        self.setLayout(self.layout)

        # signals
        self.add_btn.clicked.connect(self.add_item)
        self.gen_labels_btn.clicked.connect(self.generate_labels)
        self.print_inventory_btn.clicked.connect(self.print_inventory)
        self.backup_btn.clicked.connect(self.run_backup)

        # load items
        db_init.ensure_db()
        self.refresh_list()

    def refresh_list(self):
        self.listw.clear()
        items = db_init.get_all_items()
        for row in items:
            _id, sku, name, qty, *_ = row
            self.listw.addItem(f"{sku} | {name} | qty: {qty}")

    def add_item(self):
        name = self.name_input.text().strip()
        sku = self.sku_input.text().strip()
        qty = self.qty_input.value()
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter an item name.")
            return
        sku_ret = db_init.add_item(sku, name, qty)
        QMessageBox.information(self, "Added", f"Item added with SKU: {sku_ret}")
        self.name_input.clear(); self.sku_input.clear(); self.qty_input.setValue(1)
        self.refresh_list()

    def generate_labels(self):
        # require selected item
        sel = self.listw.currentItem()
        if not sel:
            QMessageBox.warning(self, "No selection", "Please select an item from the list.")
            return
        text = sel.text()
        sku = text.split('|')[0].strip()
        item = db_init.get_item_by_sku(sku)
        if not item:
            QMessageBox.warning(self, "Not found", "Selected item not found in DB.")
            return
        _id, sku, name, qty = item
        # create labels pdf with qty pages
        pdf_path = create_temp_labels_pdf(sku, name, qty)
        QMessageBox.information(self, "Labels created", f"Labels PDF created: {pdf_path}\nSending to printer...")
        # print using default method
        ok = print_pdf_default(pdf_path)
        if not ok:
            QMessageBox.warning(self, "Print failed", "Default print failed. If you have SumatraPDF installed, the app can use it for robust printing.")
        else:
            QMessageBox.information(self, "Print called", "Print command sent to default PDF handler.")

    def print_inventory(self):
        items = db_init.get_all_items()
        if not items:
            QMessageBox.information(self, "Empty", "No items to print.")
            return
        pdf_path = os.path.join(APP_TMP, "inventory_view.pdf")
        create_inventory_pdf(pdf_path, items, title="Warehouse Inventory")
        QMessageBox.information(self, "Inventory PDF", f"Inventory PDF created: {pdf_path}\nSending to printer...")
        ok = print_pdf_default(pdf_path)
        if not ok:
            QMessageBox.warning(self, "Print failed", "Default print failed. Consider installing SumatraPDF for robust printing.")

    def run_backup(self):
        from backup import backup_db
        backup_db()
        QMessageBox.information(self, "Backup", "Backup script executed (check ProgramData backups folder).")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWin()
    w.show()
    sys.exit(app.exec())
