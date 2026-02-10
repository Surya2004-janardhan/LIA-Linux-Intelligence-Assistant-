import psutil
import time
import threading
from core.logger import logger

class Guardian:
    def __init__(self, check_interval=60):
        self.check_interval = check_interval
        self.running = False
        self._thread = None

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logger.info("Guardian Daemon started.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()

    def _run(self):
        while self.running:
            try:
                # Check Disk Usage
                disk = psutil.disk_usage('/')
                if disk.percent > 90:
                    logger.warning(f"CRITICAL: Disk usage at {disk.percent}%!")

                # Check RAM
                ram = psutil.virtual_memory()
                if ram.percent > 95:
                    logger.warning(f"CRITICAL: RAM usage at {ram.percent}%!")

                # Check CPU (Average over 5s)
                cpu = psutil.cpu_percent(interval=5)
                if cpu > 90:
                    logger.warning(f"HIGH LOAD: CPU at {cpu}%")

            except Exception as e:
                logger.error(f"Guardian encountered an error: {e}")

            time.sleep(self.check_interval)

# Singleton instance
guardian = Guardian()
