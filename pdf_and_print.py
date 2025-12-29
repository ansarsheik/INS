# pdf_and_print.py
import os, tempfile, datetime, subprocess
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# for image barcodes preview
from barcode import Code128
from barcode.writer import ImageWriter

TMP = tempfile.gettempdir()

# Inventory sheet (unchanged)
def create_inventory_sheet_pdf(record, out_path=None):
    if out_path is None:
        out_path = os.path.join(TMP, f"inventory_sheet_{record[1]}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4
    margin = 20*mm
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, h - margin, "INS - INVENTORY DATA SHEET")
    c.setFont("Helvetica", 11)
    x = margin; y = h - margin - 20
    labels = ["SKU:", "Name:", "Description:", "Denomination:", "Type:", "Qty:", "Location:", "Received From:", "Issued To:", "Balance:", "Remarks:"]
    values = [record[1], record[2], record[3] or "", record[4] or "", record[5] or "", str(record[6] or ""), record[7] or "", record[8] or "", record[9] or "", str(record[10] or ""), record[11] or ""]
    for lab, val in zip(labels, values):
        c.drawString(x, y, lab)
        c.drawString(x + 110, y, val)
        y -= 14
    barcode = code128.Code128(record[1], barHeight=18*mm, barWidth=0.4)
    barcode.drawOn(c, margin, y - 30)
    c.showPage(); c.save()
    return out_path

# label PDF (one page per label)
def create_labels_pdf(sku, name, qty, out_path=None, label_w_mm=70, label_h_mm=30):
    if out_path is None:
        out_path = os.path.join(TMP, f"labels_{sku}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.pdf")
    c = canvas.Canvas(out_path, pagesize=(label_w_mm*mm, label_h_mm*mm))
    for i in range(max(1,int(qty))):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(5*mm, (label_h_mm-6)*mm, name[:60])
        barcode = code128.Code128(sku, barHeight=12*mm, barWidth=0.34)
        barcode.drawOn(c, 5*mm, 6*mm)
        c.setFont("Helvetica", 9)
        c.drawString(5*mm, 3*mm, sku)
        c.showPage()
    c.save()
    return out_path

def create_inventory_report_pdf(rows, out_path=None, title="Inventory Report"):
    if out_path is None:
        out_path = os.path.join(TMP, f"inventory_report_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    y = h - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, title)
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Generated: {datetime.datetime.utcnow().isoformat()}Z")
    y -= 14
    col_x = [margin, margin+40*mm, margin+100*mm, margin+160*mm]
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col_x[0], y, "SKU"); c.drawString(col_x[1], y, "Name"); c.drawString(col_x[2], y, "Desc"); c.drawRightString(w - margin, y, "Qty")
    y -= 12
    c.setFont("Helvetica", 9)
    for r in rows:
        if y < margin + 40:
            c.showPage(); y = h - margin
        sku = r[1]; name = r[2]; desc = (r[3] or "")[:40]; qty = str(r[6] or "")
        c.drawString(col_x[0], y, sku)
        c.drawString(col_x[1], y, name[:40])
        c.drawString(col_x[2], y, desc)
        c.drawRightString(w - margin, y, qty)
        y -= 12
    c.showPage(); c.save()
    return out_path

# ---------------------------
# New: PDF builders for other forms
# ---------------------------
def create_certified_receipt_pdf(record, out_path=None):
    # record: (id,set_no,part_no,item_desc,denom_qty,qty_received,received_from,received_by,remarks,created_utc)
    if out_path is None:
        out_path = os.path.join(TMP, f"certified_receipt_{record[1] or 'rec'}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, h - margin, "Certified Receipt Voucher")
    y = h - margin - 30
    labels = ["Set No:", "Part No:", "Item Description:", "Denomination/Qty:", "Qty Received:", "Received From:", "Received By:", "Remarks:"]
    vals = [record[1] or "", record[2] or "", record[3] or "", record[4] or "", str(record[5] or ""), record[6] or "", record[7] or "", record[8] or ""]
    c.setFont("Helvetica", 11)
    for lab, val in zip(labels, vals):
        c.drawString(margin, y, lab); c.drawString(margin+120, y, val); y -= 16
    c.showPage(); c.save(); return out_path

def create_spares_issue_pdf(record, out_path=None):
    # record: (id,sl_no,part_no,description,lf_no,item,qty_issued,balance,issued_to,remarks,created_utc)
    if out_path is None:
        out_path = os.path.join(TMP, f"spares_issue_{record[1] or 'si'}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, h - margin, "Spares Issue Voucher")
    y = h - margin - 30
    labels = ["SL No:", "Part No:", "Description:", "LF No:", "Item:", "Qty Issued:", "Balance:", "Issued To:", "Remarks:"]
    vals = [record[1] or "", record[2] or "", record[3] or "", record[4] or "", record[5] or "", str(record[6] or ""), str(record[7] or ""), record[8] or "", record[9] or ""]
    c.setFont("Helvetica", 11)
    for lab, val in zip(labels, vals):
        c.drawString(margin, y, lab); c.drawString(margin+120, y, val); y -= 16
    c.showPage(); c.save(); return out_path

def create_demand_supply_pdf(record, out_path=None):
    # record: (id,patt_no,description,mand_dept,lf_no,qty_req,qty_held,balance,location,remarks,created_utc)
    if out_path is None:
        out_path = os.path.join(TMP, f"demand_supply_{record[1] or 'ds'}.pdf")
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4; margin = 20*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(margin, h - margin, "Demand on the Supply Office for Naval Stores")
    y = h - margin - 30
    labels = ["Pattern No:", "Description:", "Mand/Dept:", "LF No:", "Qty Required:", "Qty Held:", "Balance:", "Location:", "Remarks:"]
    vals = [record[1] or "", record[2] or "", record[3] or "", record[4] or "", str(record[5] or ""), str(record[6] or ""), str(record[7] or ""), record[8] or "", record[9] or ""]
    c.setFont("Helvetica", 11)
    for lab, val in zip(labels, vals):
        c.drawString(margin, y, lab); c.drawString(margin+160, y, val); y -= 16
    c.showPage(); c.save(); return out_path

# ---------------------------
# Barcode image generation (preview)
# ---------------------------
def generate_barcode_images(sku, name, count, out_dir=None):
    """
    Generates PNG barcode images using python-barcode (ImageWriter) and returns
    a list of file paths (one per label).
    """
    if out_dir is None:
        out_dir = os.path.join(TMP, f"barcode_preview_{sku}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    # Use Code128 writer
    for i in range(max(1, int(count))):
        base = os.path.join(out_dir, f"{sku}_{i+1}")
        # Code128 via python-barcode
        code = Code128(sku, writer=ImageWriter())
        fname = code.save(base)  # returns path with .png
        paths.append(fname)
    return paths

# ---------------------------
# Printing helpers (unchanged)
# ---------------------------
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

def print_pdf_sumatra(path, printer_name=None, sumatra_path=r"C:\Program Files\SumatraPDF\SumatraPDF.exe"):
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
