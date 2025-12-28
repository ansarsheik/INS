# pdf_and_print.py
import os, tempfile, datetime, csv, subprocess
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import pandas as pd

TMP = tempfile.gettempdir()

# 1) Generate single-item filled "Inventory Data Sheet" PDF (approx layout)
def create_inventory_sheet_pdf(record, out_path=None):
    # record: tuple (id, sku, name, description, denomination, type, qty, location, received_from, issued_to, balance, remarks, created_utc, modified_utc)
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
    values = [record[1], record[2], record[3], record[4], record[5], str(record[6]), record[7], record[8], record[9], str(record[10]), record[11] or ""]
    for lab, val in zip(labels, values):
        c.drawString(x, y, lab)
        c.drawString(x + 110, y, val)
        y -= 14
    # barcode area
    barcode = code128.Code128(record[1], barHeight=18*mm, barWidth=0.4)
    barcode.drawOn(c, margin, y - 30)
    c.showPage(); c.save()
    return out_path

# 2) Generate labels PDF with one page per label (qty)
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

# 3) Inventory report PDF (table)
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
    # headers
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

# 4) Print helpers: Windows shell or SumatraPDF
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

# 5) CSV export
def export_inventory_csv(rows, out_path=None):
    if out_path is None:
        out_path = os.path.join(TMP, f"inventory_export_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.csv")
    df = pd.DataFrame(rows, columns=["id","sku","name","description","denomination","type","qty","location","received_from","issued_to","balance","remarks","created_utc","modified_utc"])
    df.to_csv(out_path, index=False)
    return out_path
