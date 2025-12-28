# print_windows.py
import os
import subprocess
import sys

def print_pdf_default(pdf_path):
    """
    Attempts to print using Windows Shell. This usually opens the default PDF viewer's print action.
    For more robust unattended printing to a specific printer, install SumatraPDF and use CLI.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)
    try:
        # This will use the ShellExecute "print" verb
        # It is asynchronous and depends on default PDF application behavior.
        import win32api
        win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
        return True
    except Exception as e:
        print("ShellExecute print failed:", e)
        return False

def print_pdf_sumatra(pdf_path, printer_name=None, sumatra_path=r"C:\Program Files\SumatraPDF\SumatraPDF.exe"):
    """
    If you have SumatraPDF installed, use its CLI for robust printing.
    Example: SumatraPDF.exe -print-to "Printer Name" "file.pdf"
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)
    if not os.path.exists(sumatra_path):
        raise FileNotFoundError(sumatra_path)
    cmd = [sumatra_path]
    if printer_name:
        cmd += ["-print-to", printer_name]
    else:
        cmd += ["-print-to-default"]
    cmd.append(pdf_path)
    subprocess.Popen(cmd, shell=False)
    return True
