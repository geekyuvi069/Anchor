import shutil
import os
import json
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path(".anchor/backups")
HISTORY_FILE = BACKUP_DIR / "history.json"

class BackupManager:
    def __init__(self):
        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True)
        
        self.history = []
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r") as f:
                    self.history = json.load(f)
            except json.JSONDecodeError:
                self.history = []

    def create_backup(self, file_path: str):
        """
        Creates a copy of the file before editing.
        """
        src = Path(file_path).resolve()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_name = f"{src.name}.{timestamp}.bak"
        dst = BACKUP_DIR / backup_name
        
        shutil.copy2(src, dst)
        
        entry = {
            "original_file": str(src),
            "backup_file": str(dst),
            "timestamp": timestamp
        }
        self.history.append(entry)
        self._save_history()
        return str(dst)

    def restore_last_backup(self):
        """
        Restores the file from the most recent backup.
        """
        if not self.history:
            return None
        
        last_entry = self.history.pop()
        src = Path(last_entry["original_file"])
        backup = Path(last_entry["backup_file"])
        
        if backup.exists():
            shutil.copy2(backup, src)
            self._save_history()
            return str(src)
        else:
            raise FileNotFoundError(f"Backup file {backup} not found.")

    def _save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)
