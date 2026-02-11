import json
import os
from datetime import datetime
from threading import Lock
from core.logger import logger

class Telemetry:
    """
    Local Telemetry System.
    Stores usage statistics in ~/.lia/telemetry.json
    """
    def __init__(self, file_path=None):
        if file_path is None:
            home = os.path.expanduser("~")
            base_dir = os.path.join(home, ".lia")
            os.makedirs(base_dir, exist_ok=True)
            self.file_path = os.path.join(base_dir, "telemetry.json")
        else:
            self.file_path = file_path
        
        self.lock = Lock()
        self._stats = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load telemetry: {e}")
        
        return {
            "total_commands": 0,
            "agent_stats": {}, # {agent_name: {success: 0, fail: 0, total_time: 0}}
            "last_start": datetime.now().isoformat(),
            "versions": {"core": "1.0.0"}
        }

    def _save(self):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self._stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save telemetry: {e}")

    def log_command(self, agent_name: str, success: bool, duration: float):
        with self.lock:
            self._stats["total_commands"] += 1
            
            if agent_name not in self._stats["agent_stats"]:
                self._stats["agent_stats"][agent_name] = {"success": 0, "fail": 0, "total_time": 0}
            
            stats = self._stats["agent_stats"][agent_name]
            if success:
                stats["success"] += 1
            else:
                stats["fail"] += 1
            
            stats["total_time"] += duration
            self._save()

    def get_summary(self):
        with self.lock:
            return self._stats

# Singleton
telemetry = Telemetry()
