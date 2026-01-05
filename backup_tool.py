import sqlite3
import os
import time
from datetime import datetime

# CONFIGURATION
SOURCE_DB = 'hospital.db'
BACKUP_DIR = 'backups'

def perform_backup():
    # 1. Ensure Backup Directory Exists
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    # 2. Generate Timestamped Filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(BACKUP_DIR, f"hospital_backup_{timestamp}.db")

    print(f"[*] Starting Hot Backup of {SOURCE_DB}...")

    try:
        # 3. Connect to Source and Destination
        # We use the SQLite Online Backup API (not just file copy) 
        # to ensure data consistency even if the DB is being written to.
        source_conn = sqlite3.connect(SOURCE_DB)
        dest_conn = sqlite3.connect(backup_file)

        # 4. Perform Backup
        source_conn.backup(dest_conn)
        
        print(f"[+] Backup Successful: {backup_file}")
        
    except sqlite3.Error as e:
        print(f"[-] Backup Failed: {e}")
        
    finally:
        if dest_conn: dest_conn.close()
        if source_conn: source_conn.close()

if __name__ == "__main__":
    perform_backup()