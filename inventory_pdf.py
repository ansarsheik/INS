# inventory_pdf.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import datetime

def create_inventory_pdf(output_path, items, title="Inventory"):
    """
    items: list of tuples (id, sku, name, qty, created_utc, modified_utc)
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    margin = 20*mm
    y = height - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, title)
    y -= 10*mm
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Generated: {datetime.datetime.utcnow().isoformat()}Z")
    y -= 8*mm
    # table header
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "SKU")
    c.drawString(margin + 50*mm, y, "Name")
    c.drawRightString(width - margin, y, "Qty")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    for row in items:
        if y < margin + 20*mm:
            c.showPage()
            y = height - margin
        _, sku, name, qty, *_ = row
        c.drawString(margin, y, str(sku))
        c.drawString(margin + 50*mm, y, str(name)[:55])
        c.drawRightString(width - margin, y, str(qty))
        y -= 6*mm
    c.showPage()
    c.save()
    return output_path
