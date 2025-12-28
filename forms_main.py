# forms_main.py
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QFormLayout, QLineEdit, QSpinBox,
    QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt

import db_forms

APP_TMP = os.path.join(os.environ.get("TEMP", "."), "warehouse_forms")

class FormTab(QWidget):
    def __init__(self, form_builder, list_loader, headers):
        super().__init__()
        self.form_builder = form_builder
        self.list_loader = list_loader
        self.headers = headers
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        # form area
        self.form_area = self.form_builder()
        layout.addLayout(self.form_area)
        # buttons
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.clear_btn = QPushButton("Clear")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        # table area
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        layout.addWidget(QLabel("Saved records:"))
        layout.addWidget(self.table)
        self.setLayout(layout)

        # signals
        self.save_btn.clicked.connect(self._on_save)
        self.clear_btn.clicked.connect(self._on_clear)

        # initial load
        self.load_records()

    def _on_save(self):
        try:
            self.save_action()
            QMessageBox.information(self, "Saved", "Record saved successfully.")
            self.load_records()
            self._on_clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")

    def _on_clear(self):
        # clear all QLineEdit, QSpinBox, QTextEdit children in the form area
        for i in range(self.form_area.count()):
            item = self.form_area.itemAt(i)
            if item is None: continue
            widget = item.widget()
            # form layouts will have no widget directly; check nested items
        # simple approach: find children by type
        for child in self.findChildren(QLineEdit):
            child.clear()
        for child in self.findChildren(QSpinBox):
            child.setValue(0)
        for child in self.findChildren(QTextEdit):
            child.clear()

    def load_records(self):
        rows = self.list_loader()
        self.table.setRowCount(len(rows))
        for rindex, row in enumerate(rows):
            for cindex, col in enumerate(row):
                # convert None to empty
                txt = "" if col is None else str(col)
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(rindex, cindex, item)

# Now builders for each form
def build_inventory_form():
    from PySide6.QtWidgets import QFormLayout, QLineEdit, QSpinBox, QTextEdit
    form = QFormLayout()
    form.item_no = QLineEdit(); form.part_no = QLineEdit(); form.description = QLineEdit()
    form.denomination = QLineEdit(); form.type_ = QLineEdit()
    form.qty = QSpinBox(); form.qty.setRange(0, 1000000)
    form.location = QLineEdit(); form.received_from = QLineEdit(); form.issued_to = QLineEdit()
    form.balance = QSpinBox(); form.balance.setRange(0, 1000000)
    form.remarks = QTextEdit(); form.remarks.setFixedHeight(60)

    form.addRow("Item No:", form.item_no)
    form.addRow("Part No:", form.part_no)
    form.addRow("Description:", form.description)
    form.addRow("Denomination:", form.denomination)
    form.addRow("Type:", form.type_)
    form.addRow("Qty:", form.qty)
    form.addRow("Location:", form.location)
    form.addRow("Received From:", form.received_from)
    form.addRow("Issued To:", form.issued_to)
    form.addRow("Balance:", form.balance)
    form.addRow("Remarks:", form.remarks)
    return form

def build_certified_receipt_form():
    from PySide6.QtWidgets import QFormLayout, QLineEdit, QSpinBox, QTextEdit
    form = QFormLayout()
    form.set_no = QLineEdit(); form.part_no = QLineEdit(); form.item_desc = QLineEdit()
    form.denom_qty = QLineEdit(); form.qty_received = QSpinBox(); form.qty_received.setRange(0,100000)
    form.received_from = QLineEdit(); form.received_by = QLineEdit()
    form.remarks = QTextEdit(); form.remarks.setFixedHeight(60)
    form.addRow("Set No:", form.set_no)
    form.addRow("Part No:", form.part_no)
    form.addRow("Item Description:", form.item_desc)
    form.addRow("Denomination/Qty:", form.denom_qty)
    form.addRow("Qty Received:", form.qty_received)
    form.addRow("Received From:", form.received_from)
    form.addRow("Received By:", form.received_by)
    form.addRow("Remarks:", form.remarks)
    return form

def build_spares_issue_form():
    from PySide6.QtWidgets import QFormLayout, QLineEdit, QSpinBox, QTextEdit
    form = QFormLayout()
    form.sl_no = QLineEdit(); form.part_no = QLineEdit(); form.description = QLineEdit()
    form.lf_no = QLineEdit(); form.item = QLineEdit()
    form.qty_issued = QSpinBox(); form.qty_issued.setRange(0,100000)
    form.balance = QSpinBox(); form.balance.setRange(0,100000)
    form.issued_to = QLineEdit(); form.remarks = QTextEdit(); form.remarks.setFixedHeight(60)
    form.addRow("SL No:", form.sl_no)
    form.addRow("Part No:", form.part_no)
    form.addRow("Description:", form.description)
    form.addRow("LF No:", form.lf_no)
    form.addRow("Item:", form.item)
    form.addRow("Qty Issued:", form.qty_issued)
    form.addRow("Balance:", form.balance)
    form.addRow("Issued To:", form.issued_to)
    form.addRow("Remarks:", form.remarks)
    return form

def build_demand_supply_form():
    from PySide6.QtWidgets import QFormLayout, QLineEdit, QSpinBox, QTextEdit
    form = QFormLayout()
    form.patt_no = QLineEdit(); form.description = QLineEdit(); form.mand_dept = QLineEdit()
    form.lf_no = QLineEdit(); form.qty_req = QSpinBox(); form.qty_req.setRange(0,100000)
    form.qty_held = QSpinBox(); form.qty_held.setRange(0,100000)
    form.balance = QSpinBox(); form.balance.setRange(0,100000)
    form.location = QLineEdit(); form.remarks = QTextEdit(); form.remarks.setFixedHeight(60)
    form.addRow("Pattern No:", form.patt_no)
    form.addRow("Description:", form.description)
    form.addRow("Mand/Dept:", form.mand_dept)
    form.addRow("LF No:", form.lf_no)
    form.addRow("Qty Required:", form.qty_req)
    form.addRow("Qty Held:", form.qty_held)
    form.addRow("Balance:", form.balance)
    form.addRow("Location:", form.location)
    form.addRow("Remarks:", form.remarks)
    return form

# Actions connect the forms to DB functions
def attach_inventory_actions(tab: FormTab, form_layout):
    def save_action():
        # extract fields from layout
        item_no = form_layout.item_no.text().strip()
        part_no = form_layout.part_no.text().strip()
        description = form_layout.description.text().strip()
        denomination = form_layout.denomination.text().strip()
        type_ = form_layout.type_.text().strip()
        qty = form_layout.qty.value()
        location = form_layout.location.text().strip()
        received_from = form_layout.received_from.text().strip()
        issued_to = form_layout.issued_to.text().strip()
        balance = form_layout.balance.value()
        remarks = form_layout.remarks.toPlainText().strip()
        if not item_no and not part_no:
            raise ValueError("Provide Item No or Part No")
        db_forms.save_inventory(item_no, part_no, description, denomination, type_, qty, location, received_from, issued_to, balance, remarks)
    tab.save_action = save_action
    tab.list_loader = db_forms.list_inventory
    tab.load_records()

def attach_certified_actions(tab: FormTab, form_layout):
    def save_action():
        set_no = form_layout.set_no.text().strip()
        part_no = form_layout.part_no.text().strip()
        item_desc = form_layout.item_desc.text().strip()
        denom_qty = form_layout.denom_qty.text().strip()
        qty_received = form_layout.qty_received.value()
        received_from = form_layout.received_from.text().strip()
        received_by = form_layout.received_by.text().strip()
        remarks = form_layout.remarks.toPlainText().strip()
        if not set_no and not part_no:
            raise ValueError("Provide Set No or Part No")
        db_forms.save_certified_receipt(set_no, part_no, item_desc, denom_qty, qty_received, received_from, received_by, remarks)
    tab.save_action = save_action
    tab.list_loader = db_forms.list_certified_receipt
    tab.load_records()

def attach_spares_actions(tab: FormTab, form_layout):
    def save_action():
        sl_no = form_layout.sl_no.text().strip()
        part_no = form_layout.part_no.text().strip()
        description = form_layout.description.text().strip()
        lf_no = form_layout.lf_no.text().strip()
        item = form_layout.item.text().strip()
        qty_issued = form_layout.qty_issued.value()
        balance = form_layout.balance.value()
        issued_to = form_layout.issued_to.text().strip()
        remarks = form_layout.remarks.toPlainText().strip()
        if not sl_no and not part_no:
            raise ValueError("Provide SL No or Part No")
        db_forms.save_spares_issue(sl_no, part_no, description, lf_no, item, qty_issued, balance, issued_to, remarks)
    tab.save_action = save_action
    tab.list_loader = db_forms.list_spares_issue
    tab.load_records()

def attach_demand_actions(tab: FormTab, form_layout):
    def save_action():
        patt_no = form_layout.patt_no.text().strip()
        description = form_layout.description.text().strip()
        mand_dept = form_layout.mand_dept.text().strip()
        lf_no = form_layout.lf_no.text().strip()
        qty_req = form_layout.qty_req.value()
        qty_held = form_layout.qty_held.value()
        balance = form_layout.balance.value()
        location = form_layout.location.text().strip()
        remarks = form_layout.remarks.toPlainText().strip()
        if not patt_no and not description:
            raise ValueError("Provide Pattern No or Description")
        db_forms.save_demand_supply(patt_no, description, mand_dept, lf_no, qty_req, qty_held, balance, location, remarks)
    tab.save_action = save_action
    tab.list_loader = db_forms.list_demand_supply
    tab.load_records()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warehouse Forms - Inventory & Vouchers")
        self.resize(1100, 700)
        layout = QVBoxLayout()
        label = QLabel("<h2>Inventory Forms - Data Entry</h2>")
        layout.addWidget(label)
        tabs = QTabWidget()
        # inventory tab
        inv_form_layout = build_inventory_form()
        inv_tab = FormTab(lambda: inv_form_layout, db_forms.list_inventory,
                         ["id","item_no","part_no","description","denomination","type","qty","location","received_from","issued_to","balance","remarks","created_utc"])
        attach_inventory_actions(inv_tab, inv_form_layout)
        tabs.addTab(inv_tab, "Inventory Data Sheet")
        # certified receipt
        cert_form_layout = build_certified_receipt_form()
        cert_tab = FormTab(lambda: cert_form_layout, db_forms.list_certified_receipt,
                          ["id","set_no","part_no","item_desc","denom_qty","qty_received","received_from","received_by","remarks","created_utc"])
        attach_certified_actions(cert_tab, cert_form_layout)
        tabs.addTab(cert_tab, "Certified Receipt Voucher")
        # spares issue
        spares_form_layout = build_spares_issue_form()
        spares_tab = FormTab(lambda: spares_form_layout, db_forms.list_spares_issue,
                            ["id","sl_no","part_no","description","lf_no","item","qty_issued","balance","issued_to","remarks","created_utc"])
        attach_spares_actions(spares_tab, spares_form_layout)
        tabs.addTab(spares_tab, "Spares Issue Voucher")
        # demand supply
        demand_form_layout = build_demand_supply_form()
        demand_tab = FormTab(lambda: demand_form_layout, db_forms.list_demand_supply,
                             ["id","patt_no","description","mand_dept","lf_no","qty_req","qty_held","balance","location","remarks","created_utc"])
        attach_demand_actions(demand_tab, demand_form_layout)
        tabs.addTab(demand_tab, "Demand on Supply Office")
        layout.addWidget(tabs)
        self.setLayout(layout)
        # ensure DB exists
        db_forms.ensure_db()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
