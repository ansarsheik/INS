# backup.py
import shutil, os, datetime
DB_PATH = r"C:\ProgramData\MyWarehouse\forms.db"
BACKUP_DIR = r"C:\ProgramData\MyWarehouse\backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_db(keep_days=30):
    now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    tmp_copy = os.path.join(BACKUP_DIR, f"db_copy_{now}.db")
    shutil.copy2(DB_PATH, tmp_copy)
    zip_name = os.path.join(BACKUP_DIR, f"backup_{now}.zip")
    shutil.make_archive(zip_name.replace('.zip',''), 'zip', BACKUP_DIR, os.path.basename(tmp_copy))
    os.remove(tmp_copy)
    # rotate old backups
    for f in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp):
            age = (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(fp))).days
            if age > keep_days:
                os.remove(fp)
