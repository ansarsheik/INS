# label_pdf.py
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
import os
import tempfile

def create_labels_pdf(output_path, sku, name, qty, label_w_mm=70, label_h_mm=30):
    """
    Creates a PDF with `qty` pages, each a label containing name + code128 barcode + sku.
    """
    c = canvas.Canvas(output_path, pagesize=(label_w_mm*mm, label_h_mm*mm))
    for i in range(int(qty)):
        # Header
        c.setFont("Helvetica-Bold", 12)
        c.drawString(5*mm, (label_h_mm-6)*mm, name[:60])
        # Barcode (Code128)
        barcode = code128.Code128(sku, barHeight=12*mm, barWidth=0.34)
        barcode_x = 5*mm
        barcode_y = 6*mm
        barcode.drawOn(c, barcode_x, barcode_y)
        # SKU text under barcode
        c.setFont("Helvetica", 9)
        c.drawString(barcode_x, barcode_y - 4, sku)
        c.showPage()
    c.save()
    return output_path

def create_temp_labels_pdf(sku, name, qty):
    tmp_dir = tempfile.gettempdir()
    filename = f"labels_{sku}.pdf"
    path = os.path.join(tmp_dir, filename)
    create_labels_pdf(path, sku, name, qty)
    return path
