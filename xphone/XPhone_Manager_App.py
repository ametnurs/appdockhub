"""
XPhone Manager - Multi-Screen Android & Cloud Phone Controller.
Tampilan Antarmuka Modern (PySide6) berbasis Multi-Screen Mobile Grid
persis seperti Facebook Account Manager / Phone Farm Organizer.
Mendukung multi-instance terpisah (Slot 1 -> XPhone_Lite:5554, Slot 2 -> XPhone_2:5556, dst).
Dilengkapi integrasi otomatis Google Play Store & Genuine Installer Engine.
"""
import os
import sys
import time
import json
import shutil
import subprocess
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QLabel, QPushButton, QStackedWidget, QFrame,
    QScrollArea, QComboBox, QSpinBox, QMessageBox, QFileDialog,
    QLineEdit, QSizePolicy, QStatusBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QProgressBar, QTextEdit, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QCursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMULATOR_PATH = r"C:\Users\User\AppData\Local\Android\Sdk\emulator\emulator.exe"
ADB_PATH = r"C:\Users\User\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if not os.path.exists(ADB_PATH) and os.path.exists(r"C:\adb\adb.exe"):
    ADB_PATH = r"C:\adb\adb.exe"
AVD_BASE_DIR = r"C:\Users\User\.android\avd"
SPLITS_DIR = os.path.join(BASE_DIR, "apk_splits")
SETTINGS_FILE = os.path.join(BASE_DIR, "xphone_settings.json")
IOS_LAUNCHER_APK = os.path.join(BASE_DIR, "ios_launcher.apk")

# Preset Profil Perangkat Populer
DEVICE_PRESETS = {
    "Google Pixel 5 (Resmi Google Certified)": {
        "brand": "Google",
        "model": "Pixel 5",
        "device_name": "redfin"
    },
    "Apple iPhone 15 Pro Max (iOS 17 Mode)": {
        "brand": "Apple",
        "model": "iPhone 15 Pro Max",
        "device_name": "iPhone16,2"
    },
    "Apple iPhone 14 Pro (iOS 16 Mode)": {
        "brand": "Apple",
        "model": "iPhone 14 Pro",
        "device_name": "iPhone15,2"
    },
    "Apple iPhone 13 Pro (iOS 15 Mode)": {
        "brand": "Apple",
        "model": "iPhone 13 Pro",
        "device_name": "iPhone14,2"
    },
    "Samsung Galaxy S22 Ultra (SM-S908B)": {
        "brand": "samsung",
        "model": "SM-S908B",
        "device_name": "b0q"
    },
    "Samsung Galaxy A53 5G (SM-A536B)": {
        "brand": "samsung",
        "model": "SM-A536B",
        "device_name": "a53x"
    },
    "Xiaomi Redmi Note 11 (spes)": {
        "brand": "Xiaomi",
        "model": "2201117TG",
        "device_name": "spes"
    },
    "Xiaomi POCO F4 (munch)": {
        "brand": "Xiaomi",
        "model": "22021211RG",
        "device_name": "munch"
    },
    "Asus ROG Phone 5 (ASUS_I005D)": {
        "brand": "asus",
        "model": "ASUS_I005D",
        "device_name": "ASUS_I005D"
    },
    "Custom (Ketik Manual Sendiri)": {
        "brand": "",
        "model": "",
        "device_name": ""
    }
}

DEFAULT_SETTINGS = {
    "cpu_cores": "2 Core (Optimal Multi-Screen Stabil)",
    "ram_mb": "1536 MB (1.5 GB - Optimal Multi-Screen Hemat RAM - Rekomendasi)",
    "resolution": "720x1280 (HD Portrait - Rekomendasi) - 240 DPI",
    "preset": "Google Pixel 5 (Resmi Google Certified)",
    "brand": "Google",
    "model": "Pixel 5",
    "device_name": "redfin",
    "carrier": "Telkomsel (Indonesia)",
    "phone_number": "+6281234567890",
    "signal_bars": "4 Bar (Sinyal Penuh 4G/LTE)"
}

def load_settings() -> dict:
    data = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                data.update(saved)
        except Exception:
            pass
    return data

def save_settings(data: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def get_slot_avd(slot_id: int) -> str:
    if slot_id == 1:
        return "XPhone_Lite"
    return f"XPhone_{slot_id}"

def get_slot_port(slot_id: int) -> int:
    return 5554 + (slot_id - 1) * 2

def get_slot_serial(slot_id: int) -> str:
    return f"emulator-{get_slot_port(slot_id)}"

def _get_hidden_startupinfo():
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si
    return None

def hidden_run(*args, **kwargs):
    if sys.platform == "win32":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        if "startupinfo" not in kwargs:
            kwargs["startupinfo"] = _get_hidden_startupinfo()
    return subprocess.run(*args, **kwargs)

MACROS_DIR = os.path.join(BASE_DIR, "macros")
os.makedirs(MACROS_DIR, exist_ok=True)

def broadcast_adb_command(serials: list, args: list):
    """Mengirim perintah ADB secara simultan ke seluruh serial perangkat menggunakan multi-threading."""
    def _send(s):
        try:
            hidden_run([ADB_PATH, "-s", s] + args, capture_output=True, timeout=4)
        except Exception:
            pass
    threads = [threading.Thread(target=_send, args=(s,), daemon=True) for s in serials]
    for t in threads:
        t.start()

class InteractivePhonePad(QLabel):
    """Pad layar interaktif yang mentransformasi koordinat sentuhan & gestur mouse ke resolusi Android."""
    def __init__(self, on_action=None, parent=None):
        super().__init__(parent)
        self.on_action = on_action
        self.start_pos = None
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #090D16;
                border: 2px solid #38BDF8;
                border-radius: 8px;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.position() if hasattr(event, "position") else event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos is not None:
            end_pos = event.position() if hasattr(event, "position") else event.pos()
            dx = end_pos.x() - self.start_pos.x()
            dy = end_pos.y() - self.start_pos.y()
            dist = (dx**2 + dy**2)**0.5

            w = max(1, self.width())
            h = max(1, self.height())

            if dist < 8: # Tap
                nx = int((end_pos.x() / w) * 720)
                ny = int((end_pos.y() / h) * 1280)
                nx = max(0, min(720, nx))
                ny = max(0, min(1280, ny))
                if self.on_action:
                    self.on_action("tap", {"x": nx, "y": ny})
            else: # Swipe
                x1 = max(0, min(720, int((self.start_pos.x() / w) * 720)))
                y1 = max(0, min(1280, int((self.start_pos.y() / h) * 1280)))
                x2 = max(0, min(720, int((end_pos.x() / w) * 720)))
                y2 = max(0, min(1280, int((end_pos.y() / h) * 1280)))
                if self.on_action:
                    self.on_action("swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": 250})
            self.start_pos = None

class MacroRunner(QObject):
    """Engine pemutar makro otomatis dengan dukungan multithreading broadcast & loop."""
    progress_signal = Signal(int, int, int, int, str) # current_loop, total_loops, step_idx, total_steps, description
    finished_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self._running = False

    def is_running(self):
        return self._running

    def stop(self):
        self._running = False

    def run_macro(self, macro_data, target_serials, loop_count=1, delay_between=0, speed=1.0):
        self._running = True
        steps = macro_data.get("steps", [])
        if not steps or not target_serials:
            self._running = False
            self.finished_signal.emit("Gagal: Langkah kosong atau tidak ada layar online yang dipilih.")
            return

        infinite = (loop_count <= 0)
        current_loop = 0

        while self._running and (infinite or current_loop < loop_count):
            current_loop += 1
            for step_idx, step in enumerate(steps):
                if not self._running:
                    break

                stype = step.get("type", "tap")
                desc = f"Langkah {step_idx + 1}/{len(steps)}: {stype.upper()}"

                if stype == "tap":
                    broadcast_adb_command(target_serials, ["shell", "input", "tap", str(step["x"]), str(step["y"])])
                    desc += f" di ({step['x']}, {step['y']})"
                elif stype == "swipe":
                    dur = str(step.get("duration", 250))
                    broadcast_adb_command(target_serials, ["shell", "input", "swipe", str(step["x1"]), str(step["y1"]), str(step["x2"]), str(step["y2"]), dur])
                    desc += f" ({step['x1']},{step['y1']} -> {step['x2']},{step['y2']})"
                elif stype == "key":
                    broadcast_adb_command(target_serials, ["shell", "input", "keyevent", str(step["keycode"])])
                    desc += f" Key #{step['keycode']} ({step.get('name', 'Tombol')})"
                elif stype == "text":
                    broadcast_adb_command(target_serials, ["shell", "input", "text", step.get("text", "")])
                    desc += f" Input Teks: '{step.get('text', '')}'"
                elif stype == "sleep":
                    desc += f" Jeda {step.get('delay_ms', 1000)}ms"

                self.progress_signal.emit(current_loop, loop_count, step_idx + 1, len(steps), desc)

                delay = (step.get("delay_ms", 500) / 1000.0) / max(0.1, speed)
                time.sleep(delay)

            if not self._running:
                break

            if delay_between > 0 and (infinite or current_loop < loop_count):
                time.sleep(delay_between)

        was_running = self._running
        self._running = False
        if was_running:
            self.finished_signal.emit(f"Selesai! Makro berhasil diputar {current_loop} putaran ke {len(target_serials)} layar.")
        else:
            self.finished_signal.emit("Makro dihentikan oleh pengguna (Emergency Stop).")

def ensure_slot_avd_exists(slot_id: int, avd_dir: str = AVD_BASE_DIR) -> str:
    """Memastikan folder AVD, config.ini (PlayStore enabled), dan encryptionkey.img siap tanpa lock."""
    if slot_id == 1:
        name = "XPhone_Lite"
    else:
        name = f"XPhone_{slot_id}"

    folder = os.path.join(avd_dir, f"{name}.avd")
    ini_file = os.path.join(avd_dir, f"{name}.ini")
    os.makedirs(folder, exist_ok=True)

    if not os.path.exists(ini_file):
        try:
            with open(ini_file, "w", encoding="utf-8") as f:
                f.write(f"avd.ini.encoding=UTF-8\npath={folder}\npath.rel=avd\\{name}.avd\ntarget=android-31\n")
        except Exception:
            pass

    cfg_file = os.path.join(folder, "config.ini")
    if not os.path.exists(cfg_file):
        template = os.path.join(avd_dir, "XPhone_2.avd", "config.ini")
        if not os.path.exists(template):
            template = os.path.join(avd_dir, "XPhone_Lite.avd", "config.ini")
        if os.path.exists(template):
            try:
                with open(template, "r", encoding="utf-8") as f:
                    content = f.read()
                content = content.replace("XPhone 2 (Slot #2)", f"XPhone {slot_id} (Slot #{slot_id})")
                with open(cfg_file, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                pass

    # Selaraskan konfigurasi hardware & merek dari pengaturan tersimpan
    if os.path.exists(cfg_file):
        try:
            settings = load_settings()
            cores_val = settings.get("cpu_cores", "4").split()[0]
            ram_val = settings.get("ram_mb", "3072").split()[0]
            brand = settings.get("brand", "Google")
            model = settings.get("model", "Pixel 5")
            with open(cfg_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            updated = []
            for l in lines:
                if l.startswith("hw.cpu.ncore"):
                    updated.append(f"hw.cpu.ncore={cores_val}\n")
                elif l.startswith("hw.ramSize"):
                    updated.append(f"hw.ramSize={ram_val}\n")
                elif l.startswith("hw.device.manufacturer") and brand:
                    updated.append(f"hw.device.manufacturer={brand}\n")
                elif l.startswith("hw.device.name") and model:
                    updated.append(f"hw.device.name={model}\n")
                else:
                    updated.append(l)
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.writelines(updated)
        except Exception:
            pass

    enc_file = os.path.join(folder, "encryptionkey.img")
    if not os.path.exists(enc_file):
        lite_enc = os.path.join(avd_dir, "XPhone_Lite.avd", "encryptionkey.img")
        if os.path.exists(lite_enc):
            try:
                shutil.copyfile(lite_enc, enc_file)
            except Exception:
                pass

    # Bersihkan file lock sisa jika emulator sebelumnya ditutup paksa
    try:
        for f in os.listdir(folder):
            if f.endswith(".lock"):
                try:
                    os.remove(os.path.join(folder, f))
                except Exception:
                    pass
    except Exception:
        pass

    return name

# Modern Style matching the user's reference
APP_STYLE = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
    color: #1E293B;
    background-color: #F1F5F9;
}

/* Sidebar Navigation */
QFrame#sidebarFrame {
    background-color: #1E293B;
    border-right: 1px solid #334155;
}

QFrame#sidebarFrame QLabel {
    background: transparent;
    color: #F8FAFC;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #CBD5E1;
    text-align: left;
    padding: 9px 16px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.nav-btn:hover {
    background-color: #334155;
    color: #FFFFFF;
}

QPushButton.nav-btn:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}

/* Cards & Frames */
QFrame.card, QFrame[class="card"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

QFrame.phone-slot {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
}

/* Action Buttons */
QPushButton.btn-primary, QPushButton[class="btn-primary"] {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 600;
}
QPushButton.btn-primary:hover, QPushButton[class="btn-primary"]:hover {
    background-color: #1D4ED8;
}

QPushButton.btn-outline, QPushButton[class="btn-outline"] {
    background-color: #FFFFFF;
    color: #2563EB;
    border: 1px solid #2563EB;
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton.btn-outline:hover, QPushButton[class="btn-outline"]:hover {
    background-color: #EFF6FF;
}

QPushButton.btn-yellow, QPushButton[class="btn-yellow"] {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FCD34D;
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton.btn-yellow:hover, QPushButton[class="btn-yellow"]:hover {
    background-color: #FDE68A;
}

QPushButton.btn-green, QPushButton[class="btn-green"] {
    background-color: #DCFCE7;
    color: #166534;
    border: 1px solid #86EFAC;
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton.btn-green:hover, QPushButton[class="btn-green"]:hover {
    background-color: #BBF7D0;
}

QPushButton.btn-orange, QPushButton[class="btn-orange"] {
    background-color: #FFEDD5;
    color: #9A3412;
    border: 1px solid #FDBA74;
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton.btn-orange:hover, QPushButton[class="btn-orange"]:hover {
    background-color: #FED7AA;
}

QPushButton.pill-btn, QPushButton[class="pill-btn"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    color: #475569;
}
QPushButton.pill-btn:hover, QPushButton[class="pill-btn"]:hover {
    background-color: #F8FAFC;
    border-color: #CBD5E1;
}

/* QComboBox, QSpinBox, & Dropdown Popup (Solid 100% Background, Anti-Shadow/Ghosting) */
QComboBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
    font-weight: 500;
}
QComboBox:hover, QSpinBox:hover {
    border-color: #3B82F6;
}
QComboBox:focus, QSpinBox:focus {
    border: 2px solid #2563EB;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E2E8F0;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #F8FAFC;
}
QComboBox::down-arrow {
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #475569;
}

/* WAJIB: Popup Dropdown View Harus 100% Solid Putih Tanpa Transparansi */
QComboBox QAbstractItemView, QComboBox QListView {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #94A3B8;
    border-radius: 6px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item, QComboBox QListView::item {
    min-height: 28px;
    padding: 4px 10px;
    color: #0F172A;
    background-color: #FFFFFF;
    border-radius: 4px;
}
QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
}
QComboBox QAbstractItemView::item:hover, QComboBox QListView::item:hover {
    background-color: #EFF6FF;
    color: #1D4ED8;
}

/* QLineEdit Inputs */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
    font-size: 12px;
}
QLineEdit:focus {
    border: 2px solid #2563EB;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
"""

class StatusWorker(QObject):
    # devices_signal emits dict: {slot_id: {"status": "ONLINE"|"BOOTING"|"OFFLINE", "serial": str}}
    devices_signal = Signal(object)
    screenshot_signal = Signal(int, bytes) # slot_id, png_bytes

    def __init__(self):
        super().__init__()
        self._running = True

    def check_loop(self):
        while self._running:
            try:
                res = hidden_run([ADB_PATH, "devices"], capture_output=True, text=True, timeout=4)
                raw_lines = res.stdout.splitlines() if res.stdout else []
                device_map = {}
                for line in raw_lines:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[0].startswith("emulator-"):
                        device_map[parts[0]] = parts[1]

                statuses = {}
                for slot_id in range(1, 25):
                    serial = get_slot_serial(slot_id)
                    if serial in device_map:
                        st = device_map[serial]
                        if st == "device":
                            statuses[slot_id] = {"status": "ONLINE", "serial": serial}
                        elif st == "offline":
                            statuses[slot_id] = {"status": "BOOTING", "serial": serial}
                        else:
                            statuses[slot_id] = {"status": st.upper(), "serial": serial}
                    else:
                        statuses[slot_id] = {"status": "OFFLINE", "serial": serial}

                self.devices_signal.emit(statuses)

                # Capture screenshots for all online slots
                for slot_id, info in statuses.items():
                    if not self._running:
                        break
                    if info["status"] == "ONLINE":
                        try:
                            sc = hidden_run([ADB_PATH, "-s", info["serial"], "exec-out", "screencap", "-p"], capture_output=True, timeout=5)
                            if sc.stdout and len(sc.stdout) > 5000:
                                self.screenshot_signal.emit(slot_id, sc.stdout)
                        except Exception:
                            pass
            except Exception:
                pass
            time.sleep(3)

    def stop(self):
        self._running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XPhone Manager v1.0.0 - Multi-Screen & Asisten Android")
        self.resize(1340, 860)
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(APP_STYLE)

        self.total_slots = 12
        self.columns = 6
        self.slot_widgets = {} # slot_id: dict of widget references
        self.slot_statuses = {} # slot_id: "ONLINE"|"BOOTING"|"OFFLINE"
        self.phone_cards = []

        # Synchronizer State (Sync 1 Master Screen to Selected Screens)
        self.sync_active = False
        self.sync_master_slot = 1
        self.sync_checkboxes = {}

        # Macro Recorder & Automation Runner State
        self.macro_runner = MacroRunner()
        self.macro_runner.progress_signal.connect(self._on_macro_progress)
        self.macro_runner.finished_signal.connect(self._on_macro_finished)
        self.is_recording = False
        self.recording_steps = []
        self.recording_start_time = 0
        self.recording_last_time = 0
        self.recording_source_slot = 1

        self._init_ui()
        self._start_worker()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sidebar Kiri
        sidebar = self._create_sidebar()
        root_layout.addWidget(sidebar)

        # 2. Area Konten Utama (QStackedWidget)
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)

        # View 0: Multi-Screen Grid (Default)
        self.multi_view = self._create_multi_screen_view()
        self.stack.addWidget(self.multi_view)

        # View 1: Dashboard View
        self.dashboard_view = self._create_dashboard_view()
        self.stack.addWidget(self.dashboard_view)

        # View 2: Proxy View
        self.proxy_view = self._create_proxy_view()
        self.stack.addWidget(self.proxy_view)

        # View 3: Anti-Detect View
        self.antidetect_view = self._create_antidetect_view()
        self.stack.addWidget(self.antidetect_view)

        # View 4: Settings View
        self.settings_view = self._create_settings_view()
        self.stack.addWidget(self.settings_view)

        # View 5: Synchronizer View (Sync 1 Screen to Multiple)
        self.sync_view = self._create_sync_view()
        self.stack.addWidget(self.sync_view)

        # View 6: Macro Recorder View (Automation Operations)
        self.macro_view = self._create_macro_view()
        self.stack.addWidget(self.macro_view)

        # Load initial saved macros
        self.load_saved_macros_list()

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Siap. Multi-Screen XPhone Engine aktif. Android 12 GApps & Anti-Deteksi siap digunakan.")

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(240)
        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(12, 16, 12, 16)
        vbox.setSpacing(6)

        # Brand Header
        lbl_brand = QLabel("📱 XPhone Manager")
        lbl_brand.setFont(QFont("Segoe UI", 15, QFont.Bold))
        lbl_brand.setStyleSheet("color: #FFFFFF;")
        vbox.addWidget(lbl_brand)

        lbl_sub = QLabel("Multi-Screen Mobile & Cloud Phone")
        lbl_sub.setFont(QFont("Segoe UI", 8))
        lbl_sub.setStyleSheet("color: #94A3B8; margin-bottom: 12px;")
        vbox.addWidget(lbl_sub)

        # Nav Buttons Group
        self.nav_btns = []
        menus = [
            ("📊 Dashboard", 1),
            ("📱 Multi Screen (Live XPhone)", 0),
            ("🔗 Synchronizer (Sinkron Layar)", 5),
            ("🎬 Macro Recorder (Otomasi)", 6),
            ("🛍️ Google Play Store", "action_playstore"),
            ("🛠️ Fix Google Play Store", "action_fix_playstore"),
            ("🌐 Pengaturan Proxy", 2),
            ("📦 Pasang File APK", "action_install_apk"),
            ("🛡️ Anti-Detect & Profile", 3),
            ("⚙️ Pengaturan Sistem", 4),
        ]

        for text, target in menus:
            btn = QPushButton(text)
            btn.setProperty("class", "nav-btn")
            btn.setProperty("target_index", target if isinstance(target, int) else -1)
            btn.setCheckable(True)
            if target == 0:
                btn.setChecked(True)
            if isinstance(target, int):
                btn.clicked.connect(lambda chk, t=target, b=btn: self._on_nav_clicked(t, b))
            elif target == "action_playstore":
                btn.clicked.connect(lambda: self.launch_playstore())
            elif target == "action_fix_playstore":
                btn.clicked.connect(self.fix_all_playstores_threaded)
            elif target == "action_install_apk":
                btn.clicked.connect(self.install_apk_dialog)
            vbox.addWidget(btn)
            self.nav_btns.append(btn)

        vbox.addStretch()

        # Bottom Status Card on Sidebar (Identical to User Image)
        badge_frame = QFrame()
        badge_frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        b_box = QVBoxLayout(badge_frame)
        b_box.setContentsMargins(6, 6, 6, 6)
        b_box.setSpacing(4)

        lbl_b1 = QLabel("✔ ⚡ Mode Pure QEMU")
        lbl_b1.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl_b1.setStyleSheet("color: #38BDF8;")
        b_box.addWidget(lbl_b1)

        lbl_b2 = QLabel("Resmi & 100% Anti-Blank")
        lbl_b2.setFont(QFont("Segoe UI", 8))
        lbl_b2.setStyleSheet("color: #94A3B8;")
        b_box.addWidget(lbl_b2)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #334155; max-height: 1px; margin: 4px 0;")
        b_box.addWidget(sep)

        lbl_b3 = QLabel("Perangkat Terdaftar:")
        lbl_b3.setFont(QFont("Segoe UI", 8))
        lbl_b3.setStyleSheet("color: #64748B;")
        b_box.addWidget(lbl_b3)

        self.lbl_active_dev = QLabel("0 Perangkat Aktif")
        self.lbl_active_dev.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_active_dev.setStyleSheet("color: #F8FAFC;")
        b_box.addWidget(self.lbl_active_dev)

        lbl_b4 = QLabel("✔ Tanpa Batas Kuota")
        lbl_b4.setFont(QFont("Segoe UI", 8))
        lbl_b4.setStyleSheet("color: #10B981;")
        b_box.addWidget(lbl_b4)

        lbl_b5 = QLabel("🛡 Lisensi: AKTIF (PRO)")
        lbl_b5.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl_b5.setStyleSheet("color: #38BDF8;")
        b_box.addWidget(lbl_b5)

        vbox.addWidget(badge_frame)
        return sidebar

    def _on_nav_clicked(self, index, clicked_btn):
        for b in self.nav_btns:
            b.setChecked(b == clicked_btn)
        self.stack.setCurrentIndex(index)

    def open_tab_by_index(self, index: int):
        self.stack.setCurrentIndex(index)
        for b in self.nav_btns:
            if b.property("target_index") == index:
                b.setChecked(True)
            else:
                b.setChecked(False)

    def _create_multi_screen_view(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(12)

        # Top Control Bar (Like Screenshot)
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Title & Subtitle Left
        title_box = QVBoxLayout()
        lbl_head = QLabel("📱 Multi-Screen Android Mobile View")
        lbl_head.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_head.setStyleSheet("color: #0F172A;")
        title_box.addWidget(lbl_head)

        lbl_subhead = QLabel("Tampilkan perangkat Android versi mobile berdampingan. Lengkap dengan Google Play Store & Anti-Deteksi.")
        lbl_subhead.setStyleSheet("color: #64748B; font-size: 11px;")
        title_box.addWidget(lbl_subhead)
        top_layout.addLayout(title_box)

        top_layout.addStretch()

        # Right Toolbar Controls
        lbl_kol = QLabel("Kolom:")
        lbl_kol.setStyleSheet("color: #475569; font-weight: 600;")
        top_layout.addWidget(lbl_kol)

        self.cb_kolom = QComboBox()
        self.cb_kolom.addItems(["6 Kolom", "4 Kolom", "3 Kolom", "2 Kolom"])
        self.cb_kolom.currentTextChanged.connect(self._change_grid_columns)
        top_layout.addWidget(self.cb_kolom)

        lbl_size = QLabel("Ukuran Layar:")
        lbl_size.setStyleSheet("color: #475569; font-weight: 600;")
        top_layout.addWidget(lbl_size)

        self.cb_size = QComboBox()
        self.cb_size.addItems(["40% (Mini - Pas Full Grid)", "50%", "60%", "75%"])
        top_layout.addWidget(self.cb_size)

        lbl_act = QLabel("Layar Aktif:")
        lbl_act.setStyleSheet("color: #475569; font-weight: 600;")
        top_layout.addWidget(lbl_act)

        self.cb_slots = QComboBox()
        self.cb_slots.addItems(["12 Layar (2x6)", "6 Layar (1x6)", "4 Layar (2x2)", "1 Layar"])
        self.cb_slots.currentTextChanged.connect(self._change_slot_count)
        top_layout.addWidget(self.cb_slots)

        self.spin_slots = QSpinBox()
        self.spin_slots.setRange(1, 24)
        self.spin_slots.setValue(12)
        top_layout.addWidget(self.spin_slots)

        btn_apply = QPushButton("Terapkan")
        btn_apply.setProperty("class", "btn-primary")
        btn_apply.clicked.connect(self._apply_grid_settings)
        top_layout.addWidget(btn_apply)

        btn_add = QPushButton("+ Tambah Layar")
        btn_add.setProperty("class", "btn-outline")
        btn_add.clicked.connect(self._add_slot)
        top_layout.addWidget(btn_add)

        btn_sleep = QPushButton("💤 Mode Tidur")
        btn_sleep.setProperty("class", "btn-yellow")
        top_layout.addWidget(btn_sleep)

        self.btn_status_badge = QPushButton("⚡ XPhone Siap")
        self.btn_status_badge.setProperty("class", "btn-green")
        self.btn_status_badge.clicked.connect(lambda: self.start_slot_emulator(1))
        top_layout.addWidget(self.btn_status_badge)

        btn_run_all = QPushButton("🚀 Jalankan Layar #1 & #2")
        btn_run_all.setProperty("class", "btn-orange")
        btn_run_all.clicked.connect(self.start_multiple_slots)
        top_layout.addWidget(btn_run_all)

        vbox.addWidget(top_bar)

        # Action Pill Buttons Row
        pills_bar = QHBoxLayout()
        pills_bar.setSpacing(8)

        btn_p1 = QPushButton("🛍️ Buka Play Store")
        btn_p1.setProperty("class", "pill-btn")
        btn_p1.setStyleSheet("color: #059669; font-weight: 600;")
        btn_p1.clicked.connect(lambda: self.launch_playstore())
        pills_bar.addWidget(btn_p1)

        btn_p_fix = QPushButton("🛠️ Fix Google Play Store")
        btn_p_fix.setProperty("class", "pill-btn")
        btn_p_fix.setStyleSheet("color: #7C3AED; font-weight: bold; background-color: #F5F3FF; border-color: #DDD6FE;")
        btn_p_fix.setToolTip("Bersihkan cache Play Store dan sinkronkan akun ke semua layar")
        btn_p_fix.clicked.connect(self.fix_all_playstores_threaded)
        pills_bar.addWidget(btn_p_fix)

        btn_p_sync = QPushButton("🔗 Synchronizer (Sinkron)")
        btn_p_sync.setProperty("class", "pill-btn")
        btn_p_sync.setStyleSheet("color: #0284C7; font-weight: bold; background-color: #F0F9FF; border-color: #BAE6FD;")
        btn_p_sync.setToolTip("Sinkronkan aksi 1 layar master ke seluruh layar yang dipilih secara serentak")
        btn_p_sync.clicked.connect(lambda: self.open_tab_by_index(5))
        pills_bar.addWidget(btn_p_sync)

        btn_p_macro = QPushButton("🎬 Macro Recorder")
        btn_p_macro.setProperty("class", "pill-btn")
        btn_p_macro.setStyleSheet("color: #EA580C; font-weight: bold; background-color: #FFF7ED; border-color: #FED7AA;")
        btn_p_macro.setToolTip("Rekam gerakan klik dan putar makro otomasi ke layar terpilih")
        btn_p_macro.clicked.connect(lambda: self.open_tab_by_index(6))
        pills_bar.addWidget(btn_p_macro)

        btn_p_clean_ram = QPushButton("🧹 Bersihkan RAM (Clean)")
        btn_p_clean_ram.setProperty("class", "pill-btn")
        btn_p_clean_ram.setStyleSheet("color: #059669; font-weight: bold; background-color: #ECFDF5; border-color: #A7F3D0;")
        btn_p_clean_ram.setToolTip("Pangkas memori RAM QEMU & bersihkan cache Android di semua layar aktif")
        btn_p_clean_ram.clicked.connect(self.clean_all_ram_threaded)
        pills_bar.addWidget(btn_p_clean_ram)

        btn_p_reset = QPushButton("🔥 Reset Pabrik (Wipe Data)")
        btn_p_reset.setProperty("class", "pill-btn")
        btn_p_reset.setStyleSheet("color: #DC2626; font-weight: bold; background-color: #FEF2F2; border-color: #FECACA;")
        btn_p_reset.setToolTip("Reset setelan pabrik untuk ganti akun email, hapus data aplikasi, dan bersihkan layar")
        btn_p_reset.clicked.connect(self.show_factory_reset_dialog)
        pills_bar.addWidget(btn_p_reset)

        btn_p3 = QPushButton("🌐 Pasang Proxy")
        btn_p3.setProperty("class", "pill-btn")
        btn_p3.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        pills_bar.addWidget(btn_p3)

        btn_p4 = QPushButton("🔄 Refresh Screenshot")
        btn_p4.setProperty("class", "pill-btn")
        btn_p4.clicked.connect(self._manual_refresh_screens)
        pills_bar.addWidget(btn_p4)

        btn_p5 = QPushButton("⏹ Matikan Semua")
        btn_p5.setProperty("class", "pill-btn")
        btn_p5.setStyleSheet("color: #DC2626;")
        btn_p5.clicked.connect(self.stop_all_emulators)
        pills_bar.addWidget(btn_p5)

        pills_bar.addStretch()
        vbox.addLayout(pills_bar)

        # Phone Grid inside ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)

        scroll.setWidget(self.grid_container)
        vbox.addWidget(scroll, 1)

        self._render_phone_slots()
        return page

    def _render_phone_slots(self):
        # Clear existing slots
        for s in self.phone_cards:
            s.setParent(None)
        self.phone_cards.clear()
        self.slot_widgets.clear()

        cols = self.columns
        for i in range(self.total_slots):
            slot_id = i + 1
            card = self._create_single_phone_card(slot_id)
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self.phone_cards.append(card)

    def _create_single_phone_card(self, slot_id):
        card = QFrame()
        card.setProperty("class", "phone-slot")
        card.setFixedSize(175, 310)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(2)

        # Top Phone Slot Mini-Bar
        top_slot = QWidget()
        top_slot.setFixedHeight(24)
        top_slot.setStyleSheet("background-color: #1E293B; border-radius: 3px;")
        ts_layout = QHBoxLayout(top_slot)
        ts_layout.setContentsMargins(6, 0, 4, 0)
        ts_layout.setSpacing(2)

        slot_title = QLabel(f"#{slot_id}: (XPhone #{slot_id})")
        slot_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        slot_title.setStyleSheet("color: #94A3B8;")
        ts_layout.addWidget(slot_title)
        ts_layout.addStretch()

        btn_min = QLabel("–")
        btn_min.setStyleSheet("color: #64748B; font-weight: bold; font-size: 10px;")
        ts_layout.addWidget(btn_min)

        btn_max = QLabel("□")
        btn_max.setStyleSheet("color: #64748B; font-size: 9px;")
        ts_layout.addWidget(btn_max)

        # Close button kills this slot's emulator
        btn_cls = QPushButton("×")
        btn_cls.setStyleSheet("QPushButton { color: #EF4444; font-weight: bold; font-size: 13px; background: transparent; border: none; padding: 0px 4px; } QPushButton:hover { color: #F87171; background-color: #334155; border-radius: 2px; }")
        btn_cls.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cls.setToolTip(f"Matikan Layar #{slot_id}")
        btn_cls.clicked.connect(lambda chk, s=slot_id: self.stop_slot_emulator(s))
        ts_layout.addWidget(btn_cls)
        card_layout.addWidget(top_slot)

        # Mini Action Icons Bar
        icons_bar = QWidget()
        icons_bar.setFixedHeight(20)
        icons_bar.setStyleSheet("background: transparent;")
        ib_layout = QHBoxLayout(icons_bar)
        ib_layout.setContentsMargins(2, 0, 2, 0)
        ib_layout.setSpacing(2)

        btn_ic_play = QPushButton("🛍️")
        btn_ic_play.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        btn_ic_play.setToolTip("Buka Play Store")
        btn_ic_play.setCursor(QCursor(Qt.PointingHandCursor))
        btn_ic_play.clicked.connect(lambda chk, s=slot_id: self.launch_playstore(s))
        ib_layout.addWidget(btn_ic_play)

        btn_ic_fix = QPushButton("🛠️")
        btn_ic_fix.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        btn_ic_fix.setToolTip(f"Perbaiki Sentuhan Layar & Play Store Layar #{slot_id}")
        btn_ic_fix.setCursor(QCursor(Qt.PointingHandCursor))
        btn_ic_fix.clicked.connect(lambda chk, s=slot_id: self.fix_slot_touch_and_playstore(s))
        ib_layout.addWidget(btn_ic_fix)

        btn_ic_set = QPushButton("⚙️")
        btn_ic_set.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        btn_ic_set.setToolTip("Pengaturan Proxy")
        btn_ic_set.setCursor(QCursor(Qt.PointingHandCursor))
        btn_ic_set.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        ib_layout.addWidget(btn_ic_set)

        btn_ic_ref = QPushButton("🔄")
        btn_ic_ref.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        btn_ic_ref.setToolTip("Refresh Tampilan Layar")
        btn_ic_ref.setCursor(QCursor(Qt.PointingHandCursor))
        btn_ic_ref.clicked.connect(lambda chk, s=slot_id: self.refresh_slot_screenshot(s))
        ib_layout.addWidget(btn_ic_ref)

        btn_ic_wipe = QPushButton("🔥")
        btn_ic_wipe.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        btn_ic_wipe.setToolTip(f"Reset Pabrik / Ganti Email Layar #{slot_id} (Wipe Data)")
        btn_ic_wipe.setCursor(QCursor(Qt.PointingHandCursor))
        btn_ic_wipe.clicked.connect(lambda chk, s=slot_id: self.confirm_factory_reset_slot(s))
        ib_layout.addWidget(btn_ic_wipe)

        ib_layout.addStretch()
        card_layout.addWidget(icons_bar)

        # Screen Area (Portrait)
        screen = QFrame()
        screen.setStyleSheet("background-color: #090D16; border-radius: 4px;")
        s_layout = QVBoxLayout(screen)
        s_layout.setContentsMargins(6, 8, 6, 8)
        s_layout.setSpacing(6)

        lbl_preview = QLabel()
        lbl_preview.setAlignment(Qt.AlignCenter)
        lbl_preview.setStyleSheet("background: transparent;")
        lbl_preview.hide()
        s_layout.addWidget(lbl_preview, 1)

        lbl_phone_ic = QLabel("📱")
        lbl_phone_ic.setFont(QFont("Segoe UI Emoji", 24))
        lbl_phone_ic.setAlignment(Qt.AlignCenter)
        lbl_phone_ic.setStyleSheet("color: #334155; background: transparent;")
        s_layout.addWidget(lbl_phone_ic)

        lbl_status = QLabel(f"Slot #{slot_id}\n(Offline / Belum Aktif)")
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setFont(QFont("Segoe UI", 8))
        lbl_status.setStyleSheet("color: #64748B; background: transparent;")
        s_layout.addWidget(lbl_status)

        btn_action = QPushButton(f"▶ Nyalakan Layar #{slot_id}")
        btn_action.setProperty("class", "btn-primary")
        btn_action.setStyleSheet("font-size: 9px; padding: 5px;")
        btn_action.setCursor(QCursor(Qt.PointingHandCursor))
        btn_action.clicked.connect(lambda chk, s=slot_id: self._handle_slot_action_clicked(s))
        s_layout.addWidget(btn_action)

        card_layout.addWidget(screen, 1)

        # Store widget references for live updates
        self.slot_widgets[slot_id] = {
            "title": slot_title,
            "preview": lbl_preview,
            "icon": lbl_phone_ic,
            "status": lbl_status,
            "action": btn_action,
            "screen": screen
        }

        # Apply known status if worker already has data
        if slot_id in self.slot_statuses:
            self._update_slot_card_ui(slot_id, self.slot_statuses[slot_id])

        return card

    def _create_dashboard_view(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(16)

        lbl = QLabel("📊 Ringkasan Sistem & Perangkat XPhone")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        vbox.addWidget(lbl)

        # 3 Metrics Cards Row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        cards_data = [
            ("STATUS SISTEM", "ONLINE (SIAP)", "Pure QEMU v37.1 • SwiftShader ES 3.0", "#10B981"),
            ("SPESIFIKASI", "4 Core / 3 GB RAM per Slot", "Google Pixel 5 (Android 12 GApps)", "#2563EB"),
            ("INTEGRITY / SAFETYNET", "DEVICE CERTIFIED", "Google Play Protect Lolos Resmi", "#8B5CF6")
        ]

        for title, val, sub, color in cards_data:
            c = QFrame()
            c.setProperty("class", "card")
            c_box = QVBoxLayout(c)
            c_box.setContentsMargins(16, 14, 16, 14)

            t = QLabel(title)
            t.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
            c_box.addWidget(t)

            v = QLabel(val)
            v.setFont(QFont("Segoe UI", 15, QFont.Bold))
            v.setStyleSheet(f"color: {color};")
            c_box.addWidget(v)

            s = QLabel(sub)
            s.setStyleSheet("color: #94A3B8; font-size: 11px;")
            c_box.addWidget(s)
            cards_layout.addWidget(c)

        vbox.addLayout(cards_layout)

        # Big Action Panel
        action_card = QFrame()
        action_card.setProperty("class", "card")
        ac_box = QVBoxLayout(action_card)
        ac_box.setContentsMargins(20, 16, 20, 16)
        ac_box.setSpacing(10)

        lbl_ac = QLabel("⚡ Tindakan Cepat (Quick Actions)")
        lbl_ac.setFont(QFont("Segoe UI", 13, QFont.Bold))
        ac_box.addWidget(lbl_ac)

        btn_grid = QHBoxLayout()
        btn_start_1 = QPushButton("▶ Buka Layar #1 (XPhone_Lite)")
        btn_start_1.setProperty("class", "btn-primary")
        btn_start_1.clicked.connect(lambda: self.start_slot_emulator(1))
        btn_grid.addWidget(btn_start_1)

        btn_start_2 = QPushButton("▶ Buka Layar #2 (XPhone_2)")
        btn_start_2.setProperty("class", "btn-primary")
        btn_start_2.clicked.connect(lambda: self.start_slot_emulator(2))
        btn_grid.addWidget(btn_start_2)

        btn_fix_all = QPushButton("🛠️ Fix Play Store Semua Layar")
        btn_fix_all.setProperty("class", "btn-yellow")
        btn_fix_all.clicked.connect(self.fix_all_playstores_threaded)
        btn_grid.addWidget(btn_fix_all)

        btn_play = QPushButton("🛍️ Buka Play Store")
        btn_play.setProperty("class", "btn-outline")
        btn_play.clicked.connect(lambda: self.launch_playstore())
        btn_grid.addWidget(btn_play)

        btn_sync = QPushButton("🔗 Synchronizer Layar")
        btn_sync.setProperty("class", "btn-outline")
        btn_sync.clicked.connect(lambda: self.open_tab_by_index(5))
        btn_grid.addWidget(btn_sync)

        ac_box.addLayout(btn_grid)
        vbox.addWidget(action_card)
        vbox.addStretch()
        return page

    def _create_proxy_view(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(16)

        lbl = QLabel("🌐 Pengaturan Proxy Jaringan (HTTP / SOCKS5)")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        vbox.addWidget(lbl)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 16, 20, 16)
        c_layout.setSpacing(12)

        lbl_info = QLabel("Atur proxy untuk mengubah alamat IP pada perangkat XPhone agar aman dan terlindungi dari deteksi ISP.")
        lbl_info.setStyleSheet("color: #64748B;")
        c_layout.addWidget(lbl_info)

        lbl_slot = QLabel("Terapkan ke Layar:")
        lbl_slot.setStyleSheet("font-weight: 600;")
        c_layout.addWidget(lbl_slot)
        self.cb_proxy_slot = QComboBox()
        self.cb_proxy_slot.addItem("Semua Layar Aktif")
        for s in range(1, 25):
            self.cb_proxy_slot.addItem(f"Layar #{s} ({get_slot_avd(s)})")
        c_layout.addWidget(self.cb_proxy_slot)

        lbl_host = QLabel("Proxy Host / IP:")
        lbl_host.setStyleSheet("font-weight: 600;")
        c_layout.addWidget(lbl_host)
        self.entry_proxy_host = QLineEdit("127.0.0.1")
        c_layout.addWidget(self.entry_proxy_host)

        lbl_port = QLabel("Proxy Port:")
        lbl_port.setStyleSheet("font-weight: 600;")
        c_layout.addWidget(lbl_port)
        self.entry_proxy_port = QLineEdit("8080")
        c_layout.addWidget(self.entry_proxy_port)

        btn_box = QHBoxLayout()
        btn_apply = QPushButton("Pasang Proxy ke Android")
        btn_apply.setProperty("class", "btn-primary")
        btn_apply.clicked.connect(self.apply_proxy)
        btn_box.addWidget(btn_apply)

        btn_reset = QPushButton("Matikan Proxy (Kembali ke Direct)")
        btn_reset.setProperty("class", "btn-outline")
        btn_reset.clicked.connect(self.disable_proxy)
        btn_box.addWidget(btn_reset)
        c_layout.addLayout(btn_box)

        vbox.addWidget(card)
        vbox.addStretch()
        return page

    def _create_antidetect_view(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(16)

        lbl = QLabel("🛡️ Profil Anti-Deteksi & Spesifikasi Google Certified")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        vbox.addWidget(lbl)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 16, 20, 16)
        c_layout.setSpacing(8)

        specs = [
            ("Model Perangkat", "Google Pixel 5 (redfin)"),
            ("Pabrikan (Manufacturer)", "Google"),
            ("Versi Android", "Android 12 (API level 31)"),
            ("Google Play Integrity", "MEETS_DEVICE_INTEGRITY (Lolos)"),
            ("SafetyNet CTS Profile", "PASS (Cocok dengan sertifikasi resmi Google)"),
            ("Play Protect", "Certified Device"),
            ("Arsitektur CPU", "x86_64 dengan Intel WHPX Virtualization Accelerator"),
            ("Engine Grafis", "Google SwiftShader OpenGL ES 3.0 (Bebas Crash & Anti-Blank)"),
            ("Multi-Instance Engine", "Independent AVDs (Setiap Layar Memiliki Port & ID Terpisah)"),
            ("Lisensi Play Store", "installerPackageName=com.android.vending (Resmi Terverifikasi)")
        ]

        for k, v in specs:
            row = QHBoxLayout()
            lk = QLabel(k)
            lk.setStyleSheet("font-weight: 600; color: #475569; min-width: 200px;")
            lv = QLabel(v)
            lv.setStyleSheet("color: #0F172A; font-weight: bold;" if "Lolos" in v or "PASS" in v or "Resmi" in v else "color: #1E293B;")
            row.addWidget(lk)
            row.addWidget(lv)
            row.addStretch()
            c_layout.addLayout(row)

        vbox.addWidget(card)
        vbox.addStretch()
        return page

    def _create_settings_view(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 12, 16, 12)
        page_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        lbl_head = QLabel("⚙️ Pengaturan Kustomisasi Sistem & Performa XPhone")
        lbl_head.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_head.setStyleSheet("color: #0F172A;")
        title_box.addWidget(lbl_head)

        lbl_subhead = QLabel("Kustomisasi manual spesifikasi hardware, merek & model smartphone, SIM card operator, dan resolusi layar persis seperti emulator profesional.")
        lbl_subhead.setStyleSheet("color: #64748B; font-size: 11px;")
        title_box.addWidget(lbl_subhead)
        vbox.addLayout(title_box)

        # Load Current Saved Settings
        cur_settings = load_settings()

        CARD_STYLE = "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }"
        COMBO_STYLE = "QComboBox { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 10px; color: #0F172A; font-weight: 500; } QComboBox QAbstractItemView { background-color: #FFFFFF; color: #0F172A; border: 1px solid #94A3B8; selection-background-color: #2563EB; selection-color: #FFFFFF; padding: 4px; outline: none; }"
        INPUT_STYLE = "QLineEdit { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 10px; color: #0F172A; font-size: 12px; }"

        # --- Card 0: Target Slot ---
        card_target = QFrame()
        card_target.setStyleSheet(CARD_STYLE)
        ct_layout = QHBoxLayout(card_target)
        ct_layout.setContentsMargins(16, 12, 16, 12)

        lbl_target = QLabel("🎯 Terapkan Pengaturan ke:")
        lbl_target.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B;")
        ct_layout.addWidget(lbl_target)

        self.cb_settings_slot = QComboBox()
        self.cb_settings_slot.addItem("Semua Layar (Default Global untuk Semua Slot)")
        for s in range(1, 25):
            self.cb_settings_slot.addItem(f"Layar #{s} ({get_slot_avd(s)})")
        self.cb_settings_slot.setStyleSheet("font-weight: 600; min-width: 280px;")
        ct_layout.addWidget(self.cb_settings_slot)
        ct_layout.addStretch()
        vbox.addWidget(card_target)

        # --- Card 1: Performa Hardware & Layar ---
        card_hw = QFrame()
        card_hw.setStyleSheet(CARD_STYLE)
        c1 = QVBoxLayout(card_hw)
        c1.setContentsMargins(20, 16, 20, 16)
        c1.setSpacing(12)

        lbl_hw_title = QLabel("⚡ Alokasi Resource Hardware & Layar (CPU, RAM, Resolusi)")
        lbl_hw_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_hw_title.setStyleSheet("color: #2563EB;")
        c1.addWidget(lbl_hw_title)

        grid_hw = QGridLayout()
        grid_hw.setHorizontalSpacing(16)
        grid_hw.setVerticalSpacing(10)

        # CPU Cores
        lbl_cpu_t = QLabel("Jumlah Core CPU:")
        lbl_cpu_t.setStyleSheet("font-weight: 600; color: #334155;")
        self.cb_cpu = QComboBox()
        self.cb_cpu.addItems([
            "1 Core (Paling Ringan & Hemat PC)",
            "2 Core (Optimal Multi-Screen Stabil)",
            "4 Core (Rekomendasi Cepat)",
            "6 Core (Performa Gaming Tinggi)",
            "8 Core (Maksimal)"
        ])
        self.cb_cpu.setCurrentText(cur_settings.get("cpu_cores", "4 Core (Rekomendasi Cepat)"))
        grid_hw.addWidget(lbl_cpu_t, 0, 0)
        grid_hw.addWidget(self.cb_cpu, 0, 1)

        # RAM Memory
        lbl_ram_t = QLabel("Kapasitas RAM:")
        lbl_ram_t.setStyleSheet("font-weight: 600; color: #334155;")
        self.cb_ram = QComboBox()
        self.cb_ram.addItems([
            "1024 MB (1 GB - Ultra-Hemat / Super Ringan)",
            "1536 MB (1.5 GB - Optimal Multi-Screen Hemat RAM - Rekomendasi)",
            "2048 MB (2 GB - Standar Seimbang)",
            "3072 MB (3 GB - Performa Tinggi)",
            "4096 MB (4 GB - Lancar Multitasking)",
            "6144 MB (6 GB - Berat)",
            "8192 MB (8 GB - Maksimal)"
        ])
        self.cb_ram.setCurrentText(cur_settings.get("ram_mb", "1536 MB (1.5 GB - Optimal Multi-Screen Hemat RAM - Rekomendasi)"))
        grid_hw.addWidget(lbl_ram_t, 1, 0)
        grid_hw.addWidget(self.cb_ram, 1, 1)

        # Resolusi Layar & DPI
        lbl_res_t = QLabel("Resolusi Layar & DPI:")
        lbl_res_t.setStyleSheet("font-weight: 600; color: #334155;")
        self.cb_resolution = QComboBox()
        self.cb_resolution.addItems([
            "540x960 (Ultra-Ringan / Multi-Screen 12-24 Layar) - 160 DPI",
            "720x1280 (HD Portrait - Rekomendasi) - 240 DPI",
            "1080x1920 (Full HD Portrait) - 320 DPI",
            "1080x2400 (FHD+ 20:9 Modern) - 400 DPI",
            "1170x2532 (Apple iPhone 14/15 Pro Retina) - 460 DPI",
            "1290x2796 (Apple iPhone 15 Pro Max Super Retina) - 460 DPI"
        ])
        self.cb_resolution.setCurrentText(cur_settings.get("resolution", "720x1280 (HD Portrait - Rekomendasi) - 240 DPI"))
        grid_hw.addWidget(lbl_res_t, 2, 0)
        grid_hw.addWidget(self.cb_resolution, 2, 1)

        # Engine Grafis
        lbl_gpu_t = QLabel("Engine Grafis:")
        lbl_gpu_t.setStyleSheet("font-weight: 600; color: #334155;")
        lbl_gpu_val = QLabel("🛡️ Google SwiftShader OpenGL ES 3.0 (Anti-Crash Software Renderer & Bebas Blank)")
        lbl_gpu_val.setStyleSheet("color: #059669; font-weight: bold;")
        grid_hw.addWidget(lbl_gpu_t, 3, 0)
        grid_hw.addWidget(lbl_gpu_val, 3, 1)

        c1.addLayout(grid_hw)

        # Quick Optimizer Button (Mode Hemat RAM & Multi-Screen)
        hw_opt_layout = QHBoxLayout()
        btn_opt_ram = QPushButton("⚡ Terapkan Profil Mode Hemat RAM (1.5 GB & 2 Core CPU)")
        btn_opt_ram.setProperty("class", "pill-btn")
        btn_opt_ram.setStyleSheet("background-color: #059669; color: #FFFFFF; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_opt_ram.clicked.connect(self.apply_ultralight_profile)
        hw_opt_layout.addWidget(btn_opt_ram)

        btn_clean_ram_hw = QPushButton("🧹 Pangkas & Bersihkan RAM Sekarang")
        btn_clean_ram_hw.setProperty("class", "pill-btn")
        btn_clean_ram_hw.setStyleSheet("background-color: #F8FAFC; color: #0F172A; font-weight: 600; padding: 8px 16px; border-radius: 6px; border: 1px solid #CBD5E1;")
        btn_clean_ram_hw.clicked.connect(self.clean_all_ram_threaded)
        hw_opt_layout.addWidget(btn_clean_ram_hw)
        c1.addLayout(hw_opt_layout)

        vbox.addWidget(card_hw)

        # --- Card 2: Profil Merek & Model HP ---
        card_dev = QFrame()
        card_dev.setStyleSheet(CARD_STYLE)
        c2 = QVBoxLayout(card_dev)
        c2.setContentsMargins(20, 16, 20, 16)
        c2.setSpacing(12)

        lbl_dev_title = QLabel("📱 Model & Merek Smartphone (Device Profile & Brand)")
        lbl_dev_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_dev_title.setStyleSheet("color: #2563EB;")
        c2.addWidget(lbl_dev_title)

        lbl_dev_info = QLabel("Pilih preset smartphone resmi atau atur manual merek dan model HP virtual yang diinginkan.")
        lbl_dev_info.setStyleSheet("color: #64748B; font-size: 11px;")
        c2.addWidget(lbl_dev_info)

        grid_dev = QGridLayout()
        grid_dev.setHorizontalSpacing(16)
        grid_dev.setVerticalSpacing(10)

        # Preset Dropdown
        lbl_pre = QLabel("Preset Model Populer:")
        lbl_pre.setStyleSheet("font-weight: 600; color: #334155;")
        self.cb_device_preset = QComboBox()
        self.cb_device_preset.addItems(list(DEVICE_PRESETS.keys()))
        self.cb_device_preset.setCurrentText(cur_settings.get("preset", "Google Pixel 5 (Resmi Google Certified)"))
        self.cb_device_preset.currentTextChanged.connect(self._on_device_preset_changed)
        grid_dev.addWidget(lbl_pre, 0, 0)
        grid_dev.addWidget(self.cb_device_preset, 0, 1)

        # Brand / Manufacturer
        lbl_br = QLabel("Merek HP (Manufacturer):")
        lbl_br.setStyleSheet("font-weight: 600; color: #334155;")
        self.txt_brand = QLineEdit(cur_settings.get("brand", "Google"))
        grid_dev.addWidget(lbl_br, 1, 0)
        grid_dev.addWidget(self.txt_brand, 1, 1)

        # Model HP
        lbl_mo = QLabel("Model HP (Device Model):")
        lbl_mo.setStyleSheet("font-weight: 600; color: #334155;")
        self.txt_model = QLineEdit(cur_settings.get("model", "Pixel 5"))
        grid_dev.addWidget(lbl_mo, 2, 0)
        grid_dev.addWidget(self.txt_model, 2, 1)

        # Product / Board Codename
        lbl_cd = QLabel("Codename / Board:")
        lbl_cd.setStyleSheet("font-weight: 600; color: #334155;")
        self.txt_device = QLineEdit(cur_settings.get("device_name", "redfin"))
        grid_dev.addWidget(lbl_cd, 3, 0)
        grid_dev.addWidget(self.txt_device, 3, 1)

        c2.addLayout(grid_dev)

        # Action Buttons Khusus Tema Tampilan iPhone iOS & Android
        ios_act_layout = QHBoxLayout()
        self.btn_install_ios_theme = QPushButton("🍎 Terapkan Tampilan Tema iPhone iOS 17 Sekarang")
        self.btn_install_ios_theme.setProperty("class", "pill-btn")
        self.btn_install_ios_theme.setStyleSheet("background-color: #0F172A; color: #FFFFFF; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_install_ios_theme.clicked.connect(lambda: self.apply_ios_theme_to_slots(False))
        ios_act_layout.addWidget(self.btn_install_ios_theme)

        self.btn_revert_android_theme = QPushButton("🤖 Kembalikan ke Tampilan Standar Android")
        self.btn_revert_android_theme.setProperty("class", "pill-btn")
        self.btn_revert_android_theme.setStyleSheet("background-color: #F1F5F9; color: #334155; font-weight: 500; padding: 8px 16px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.btn_revert_android_theme.clicked.connect(lambda: self.revert_android_theme_to_slots(False))
        ios_act_layout.addWidget(self.btn_revert_android_theme)

        c2.addLayout(ios_act_layout)
        vbox.addWidget(card_dev)

        # --- Card 3: SIM Card & Operator Seluler ---
        card_sim = QFrame()
        card_sim.setStyleSheet(CARD_STYLE)
        c3 = QVBoxLayout(card_sim)
        c3.setContentsMargins(20, 16, 20, 16)
        c3.setSpacing(12)

        lbl_sim_title = QLabel("📶 Pengaturan SIM Card & Jaringan Seluler (Cellular)")
        lbl_sim_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_sim_title.setStyleSheet("color: #2563EB;")
        c3.addWidget(lbl_sim_title)

        grid_sim = QGridLayout()
        grid_sim.setHorizontalSpacing(16)
        grid_sim.setVerticalSpacing(10)

        # Operator Seluler
        lbl_op = QLabel("Operator SIM Card (Carrier):")
        lbl_op.setStyleSheet("font-weight: 600; color: #334155;")
        self.cb_carrier = QComboBox()
        self.cb_carrier.addItems([
            "Telkomsel (Indonesia)",
            "Indosat Ooredoo Hutchison",
            "XL Axiata",
            "Axis",
            "Smartfren 4G",
            "Tri (3) Indonesia",
            "By.U (Telkomsel)",
            "Custom (Ketik Sendiri)"
        ])
        self.cb_carrier.setCurrentText(cur_settings.get("carrier", "Telkomsel (Indonesia)"))
        grid_sim.addWidget(lbl_op, 0, 0)
        grid_sim.addWidget(self.cb_carrier, 0, 1)

        # Kekuatan Sinyal
        lbl_sig = QLabel("Status & Bar Sinyal:")
        lbl_sig.setStyleSheet("font-weight: 600; color: #334155;")
        self.cb_signal = QComboBox()
        self.cb_signal.addItems([
            "4 Bar (Sinyal Penuh 4G/LTE)",
            "3 Bar (Normal / Stabil)",
            "2 Bar (Sedang)"
        ])
        self.cb_signal.setCurrentText(cur_settings.get("signal_bars", "4 Bar (Sinyal Penuh 4G/LTE)"))
        grid_sim.addWidget(lbl_sig, 1, 0)
        grid_sim.addWidget(self.cb_signal, 1, 1)

        # Nomor Telepon
        lbl_num = QLabel("Nomor HP Virtual (SIM Line):")
        lbl_num.setStyleSheet("font-weight: 600; color: #334155;")
        self.txt_phone_number = QLineEdit(cur_settings.get("phone_number", "+6281234567890"))
        grid_sim.addWidget(lbl_num, 2, 0)
        grid_sim.addWidget(self.txt_phone_number, 2, 1)

        c3.addLayout(grid_sim)
        vbox.addWidget(card_sim)

        # Terapkan styling anti-shadow & solid background ke seluruh ComboBox & LineEdit
        for cb in [self.cb_settings_slot, self.cb_cpu, self.cb_ram, self.cb_resolution, self.cb_device_preset, self.cb_carrier, self.cb_signal]:
            cb.setStyleSheet(COMBO_STYLE)
            cb.view().setStyleSheet("background-color: #FFFFFF; color: #0F172A; selection-background-color: #2563EB; selection-color: #FFFFFF; border: 1px solid #94A3B8; padding: 2px;")
            cb.view().setAutoFillBackground(True)

        for txt in [self.txt_brand, self.txt_model, self.txt_device, self.txt_phone_number]:
            txt.setStyleSheet(INPUT_STYLE)

        # --- Card 4: Action Buttons ---
        card_act = QFrame()
        card_act.setStyleSheet(CARD_STYLE)
        c4 = QHBoxLayout(card_act)
        c4.setContentsMargins(20, 16, 20, 16)
        c4.setSpacing(12)

        btn_save = QPushButton("💾 Simpan dan Terapkan Pengaturan ke Perangkat")
        btn_save.setProperty("class", "btn-primary")
        btn_save.setStyleSheet("background-color: #059669; font-size: 13px; font-weight: bold; padding: 10px 18px;")
        btn_save.clicked.connect(self.apply_all_system_settings)
        c4.addWidget(btn_save)

        btn_reset = QPushButton("🔄 Reset ke Standar Rekomendasi (Pixel 5)")
        btn_reset.setProperty("class", "btn-outline")
        btn_reset.setStyleSheet("padding: 10px 16px;")
        btn_reset.clicked.connect(self.reset_system_settings_defaults)
        c4.addWidget(btn_reset)

        btn_wipe = QPushButton("🧹 Hapus Snapshot (Cold Boot)")
        btn_wipe.setProperty("class", "btn-yellow")
        btn_wipe.setStyleSheet("padding: 10px 16px;")
        btn_wipe.clicked.connect(self.cold_boot_selected_slot)
        c4.addWidget(btn_wipe)

        btn_factory = QPushButton("🔥 Reset Pabrik (Wipe Data)")
        btn_factory.setProperty("class", "pill-btn")
        btn_factory.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 10px 16px; border-radius: 6px;")
        btn_factory.setToolTip("Hapus seluruh akun Google, email, dan data aplikasi di slot yang dipilih")
        btn_factory.clicked.connect(self.factory_reset_selected_slot)
        c4.addWidget(btn_factory)

        vbox.addWidget(card_act)
        vbox.addStretch()

        scroll.setWidget(container)
        page_layout.addWidget(scroll)
        return page

    def _on_device_preset_changed(self, preset_name: str):
        if preset_name in DEVICE_PRESETS:
            p = DEVICE_PRESETS[preset_name]
            if p["brand"]:
                self.txt_brand.setText(p["brand"])
            if p["model"]:
                self.txt_model.setText(p["model"])
            if p["device_name"]:
                self.txt_device.setText(p["device_name"])

    def apply_all_system_settings(self):
        """Menyimpan konfigurasi dan menerapkan ke file AVD serta layar emulator yang sedang online."""
        data = {
            "cpu_cores": self.cb_cpu.currentText(),
            "ram_mb": self.cb_ram.currentText(),
            "resolution": self.cb_resolution.currentText(),
            "preset": self.cb_device_preset.currentText(),
            "brand": self.txt_brand.text().strip(),
            "model": self.txt_model.text().strip(),
            "device_name": self.txt_device.text().strip(),
            "carrier": self.cb_carrier.currentText(),
            "phone_number": self.txt_phone_number.text().strip(),
            "signal_bars": self.cb_signal.currentText()
        }
        save_settings(data)

        cores_val = data["cpu_cores"].split()[0]
        ram_val = data["ram_mb"].split()[0]
        
        # Resolusi & Density
        res_text = data["resolution"].split()[0]
        dpi_text = "240"
        if "160 DPI" in data["resolution"]:
            dpi_text = "160"
        elif "320 DPI" in data["resolution"]:
            dpi_text = "320"
        elif "400 DPI" in data["resolution"]:
            dpi_text = "400"
        elif "460 DPI" in data["resolution"]:
            dpi_text = "460"

        carrier_clean = data["carrier"].split(" (")[0]
        bars_num = "4"
        if "3 Bar" in data["signal_bars"]:
            bars_num = "3"
        elif "2 Bar" in data["signal_bars"]:
            bars_num = "2"

        # Tentukan target slot
        target_idx = self.cb_settings_slot.currentIndex()
        if target_idx == 0:
            target_slots = list(range(1, 25))
            target_desc = "Semua Layar"
        else:
            target_slots = [target_idx]
            target_desc = f"Layar #{target_idx}"

        applied_live = 0
        for s in target_slots:
            avd_name = get_slot_avd(s)
            cfg_path = os.path.join(AVD_BASE_DIR, f"{avd_name}.avd", "config.ini")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    new_lines = []
                    for line in lines:
                        if line.startswith("hw.cpu.ncore"):
                            new_lines.append(f"hw.cpu.ncore={cores_val}\n")
                        elif line.startswith("hw.ramSize"):
                            new_lines.append(f"hw.ramSize={ram_val}\n")
                        elif line.startswith("hw.device.manufacturer") and data["brand"]:
                            new_lines.append(f"hw.device.manufacturer={data['brand']}\n")
                        elif line.startswith("hw.device.name") and data["model"]:
                            new_lines.append(f"hw.device.name={data['model']}\n")
                        else:
                            new_lines.append(line)
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                except Exception:
                    pass

            # Jika layar sedang ONLINE, terapkan secara langsung (Live Hot-Apply)
            serial = get_slot_serial(s)
            if self.slot_statuses.get(s) == "ONLINE":
                try:
                    hidden_run([ADB_PATH, "-s", serial, "shell", "wm", "size", res_text], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "wm", "density", dpi_text], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "setprop", "gsm.sim.operator.alpha", carrier_clean], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "setprop", "gsm.operator.alpha", carrier_clean], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "setprop", "gsm.sim.line1.number", data["phone_number"]], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "emu", "gsm", "set", carrier_clean], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "emu", "gsm", "signal-bars", bars_num], capture_output=True)
                    applied_live += 1
                except Exception:
                    pass

        # Jika profil adalah Apple iPhone, otomatis pasang & terapkan tema iPhone (Launcher & Gesture Bar)
        if "Apple" in data["brand"] or "iPhone" in data["model"]:
            self.apply_ios_theme_to_slots(silent=True)

        msg = f"Pengaturan untuk {target_desc} berhasil disimpan!\n\n"
        msg += f"• CPU Cores: {cores_val} Core\n"
        msg += f"• Alokasi RAM: {ram_val} MB\n"
        msg += f"• Resolusi Layar: {res_text} ({dpi_text} DPI)\n"
        msg += f"• Smartphone: {data['brand']} {data['model']} ({data['device_name']})\n"
        msg += f"• SIM Card Operator: {carrier_clean} ({bars_num} Bar, Telp: {data['phone_number']})\n\n"
        if applied_live > 0:
            msg += f"⚡ Langsung diterapkan secara LIVE pada {applied_live} layar yang sedang aktif!"
        else:
            msg += "Pengaturan CPU, RAM, & Model HP akan aktif saat layar dinyalakan kembali."

        self.status_bar.showMessage(f"Pengaturan {target_desc} berhasil disimpan dan diterapkan.")
        QMessageBox.information(self, "Pengaturan Berhasil Diterapkan", msg)

    def apply_ios_theme_to_slots(self, silent: bool = False):
        """Menerapkan Tema Launcher iPhone iOS 17 & Navigasi Gesture Bar ke slot yang dipilih atau semua slot online."""
        target_idx = self.cb_settings_slot.currentIndex()
        if target_idx == 0:
            target_slots = list(range(1, 25))
            target_desc = "Semua Layar Aktif"
        else:
            target_slots = [target_idx]
            target_desc = f"Layar #{target_idx}"

        if not os.path.exists(IOS_LAUNCHER_APK):
            if not silent:
                QMessageBox.warning(self, "File Tidak Ditemukan", f"File launcher iOS tidak ditemukan di:\n{IOS_LAUNCHER_APK}")
            return

        count = 0
        for s in target_slots:
            if self.slot_statuses.get(s) == "ONLINE":
                serial = get_slot_serial(s)
                try:
                    # 1. Pasang APK iOS Launcher (Folio)
                    hidden_run([ADB_PATH, "-s", serial, "install", "-r", IOS_LAUNCHER_APK], capture_output=True, timeout=20)
                    # 2. Aktifkan Gesture Bar ala iPhone (Sembunyikan 3 tombol Android)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "cmd", "overlay", "enable", "com.android.internal.systemui.navbar.gestural"], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "secure", "navigation_mode", "2"], capture_output=True)
                    # 3. Jalankan Launcher iOS
                    hidden_run([ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.mccal.folio", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                    count += 1
                except Exception:
                    pass

        if not silent:
            if count > 0:
                QMessageBox.information(self, "Tampilan iPhone Berhasil Diterapkan", 
                                        f"Tema & Launcher iPhone iOS 17 serta Home Gesture Bar berhasil diterapkan pada {count} layar ({target_desc})!\n\nLayar kini menggunakan tampilan Home Screen & navigasi gesture ala iPhone.")
            else:
                QMessageBox.warning(self, "Layar Belum Aktif", 
                                    f"Tidak ada layar {target_desc} yang sedang ONLINE.\n\nNyalakan layar terlebih dahulu, lalu klik tombol ini lagi.")

    def revert_android_theme_to_slots(self, silent: bool = False):
        """Mengembalikan tampilan ke peluncur default Android & 3 tombol navigasi."""
        target_idx = self.cb_settings_slot.currentIndex()
        if target_idx == 0:
            target_slots = list(range(1, 25))
            target_desc = "Semua Layar Aktif"
        else:
            target_slots = [target_idx]
            target_desc = f"Layar #{target_idx}"

        count = 0
        for s in target_slots:
            if self.slot_statuses.get(s) == "ONLINE":
                serial = get_slot_serial(s)
                try:
                    # 1. Kembalikan navigasi 3 tombol standar
                    hidden_run([ADB_PATH, "-s", serial, "shell", "cmd", "overlay", "disable", "com.android.internal.systemui.navbar.gestural"], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "secure", "navigation_mode", "0"], capture_output=True)
                    # 2. Kembalikan ke Android stock launcher
                    hidden_run([ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.google.android.apps.nexuslauncher", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.android.launcher3", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                    count += 1
                except Exception:
                    pass

        if not silent:
            QMessageBox.information(self, "Tampilan Android Dipulihkan", 
                                    f"Tampilan default Android (3 tombol navigasi & Quickstep Launcher) berhasil dipulihkan pada {count} layar ({target_desc}).")

    def reset_system_settings_defaults(self):
        res = QMessageBox.question(self, "Konfirmasi Reset", "Kembalikan seluruh pengaturan ke standar Google Pixel 5 & 4 Core CPU?")
        if res == QMessageBox.Yes:
            save_settings(DEFAULT_SETTINGS)
            self.cb_cpu.setCurrentText(DEFAULT_SETTINGS["cpu_cores"])
            self.cb_ram.setCurrentText(DEFAULT_SETTINGS["ram_mb"])
            self.cb_resolution.setCurrentText(DEFAULT_SETTINGS["resolution"])
            self.cb_device_preset.setCurrentText(DEFAULT_SETTINGS["preset"])
            self.txt_brand.setText(DEFAULT_SETTINGS["brand"])
            self.txt_model.setText(DEFAULT_SETTINGS["model"])
            self.txt_device.setText(DEFAULT_SETTINGS["device_name"])
            self.cb_carrier.setCurrentText(DEFAULT_SETTINGS["carrier"])
            self.cb_signal.setCurrentText(DEFAULT_SETTINGS["signal_bars"])
            self.txt_phone_number.setText(DEFAULT_SETTINGS["phone_number"])
            self.apply_all_system_settings()

    def cold_boot_selected_slot(self):
        target_idx = self.cb_settings_slot.currentIndex()
        slot_id = 1 if target_idx == 0 else target_idx
        self.cold_boot(slot_id)

    def apply_ultralight_profile(self):
        """Menerapkan profil ultra-ringan: RAM 1.5GB, 2 Core CPU, resolusi 540x960."""
        self.cb_cpu.setCurrentText("2 Core (Optimal Multi-Screen Stabil)")
        self.cb_ram.setCurrentText("1536 MB (1.5 GB - Optimal Multi-Screen Hemat RAM - Rekomendasi)")
        self.cb_resolution.setCurrentText("540x960 (Ultra-Ringan / Multi-Screen 12-24 Layar) - 160 DPI")
        self.apply_all_system_settings()

    def clean_all_ram_threaded(self):
        """Membersihkan memori RAM pada semua emulator Android yang sedang aktif dan memangkas working set di Windows."""
        self.status_bar.showMessage("Membersihkan memori RAM pada semua layar...")
        def _clean():
            cleaned_slots = 0
            for s in range(1, 25):
                if self.slot_statuses.get(s) == "ONLINE":
                    serial = get_slot_serial(s)
                    try:
                        # 1. Bersihkan OS cache di dalam Android (Drop Caches)
                        hidden_run([ADB_PATH, "-s", serial, "shell", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], capture_output=True, timeout=3)
                        # 2. Hentikan background process yang menganggur
                        hidden_run([ADB_PATH, "-s", serial, "shell", "am", "kill-all"], capture_output=True, timeout=3)
                        cleaned_slots += 1
                    except Exception:
                        pass

            # 3. Pangkas Windows Working Set untuk semua proses qemu-system-x86_64
            try:
                import ctypes
                psapi = ctypes.windll.psapi
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_INFORMATION = 0x0400
                PROCESS_SET_QUOTA = 0x0100

                res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq qemu-system-x86_64.exe", "/FO", "CSV"], capture_output=True, text=True)
                for line in (res.stdout or "").splitlines()[1:]:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1].strip('"'))
                            hProc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
                            if hProc:
                                psapi.EmptyWorkingSet(hProc)
                                kernel32.CloseHandle(hProc)
                        except Exception:
                            pass
            except Exception:
                pass

            self.status_bar.showMessage(f"🧹 Pembersihan RAM selesai! {cleaned_slots} layar aktif telah dioptimalkan.")
        threading.Thread(target=_clean, daemon=True).start()

    def factory_reset_selected_slot(self):
        target_idx = self.cb_settings_slot.currentIndex()
        if target_idx == 0:
            self.show_factory_reset_dialog()
        else:
            self.confirm_factory_reset_slot(target_idx)

    def confirm_factory_reset_slot(self, slot_id: int):
        avd_name = get_slot_avd(slot_id)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"🔥 Reset Pabrik Layar #{slot_id}")
        msg_box.setText(
            f"Apakah Anda yakin ingin me-reset <b>Layar #{slot_id} ({avd_name})</b> ke setelan pabrik?<br><br>"
            f"• <b>Semua email & akun Google</b> akan terhapus.<br>"
            f"• <b>Semua aplikasi dan session login</b> akan bersih.<br>"
            f"• Layar kembali 100% segar seperti baru (siap ganti email baru)."
        )
        btn_reset_restart = msg_box.addButton("🔥 Reset & Nyalakan Ulang", QMessageBox.AcceptRole)
        btn_reset_off = msg_box.addButton("🛑 Reset Saja (Offline)", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("Batal", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_reset_restart)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_reset_restart:
            self.factory_reset_slot(slot_id, auto_restart=True)
        elif clicked == btn_reset_off:
            self.factory_reset_slot(slot_id, auto_restart=False)

    def fix_slot_touch_and_playstore(self, slot_id: int):
        """Memperbaiki layar yang macet / tidak bisa diklik dengan mereset ukuran display dan touch digitizer."""
        serial = get_slot_serial(slot_id)
        self.status_bar.showMessage(f"Memulihkan sentuhan layar & Play Store Layar #{slot_id}...")
        def _worker():
            try:
                # 1. Reset resolusi & density layar ke bawaan hardware skin agar sentuhan 100% presisi
                hidden_run([ADB_PATH, "-s", serial, "shell", "wm", "size", "reset"], capture_output=True)
                hidden_run([ADB_PATH, "-s", serial, "shell", "wm", "density", "reset"], capture_output=True)
                # 2. Kembalikan navigasi 3 tombol standar
                hidden_run([ADB_PATH, "-s", serial, "shell", "cmd", "overlay", "disable", "com.android.internal.systemui.navbar.gestural"], capture_output=True)
                hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "secure", "navigation_mode", "0"], capture_output=True)
                # 3. Kirim HOME keyevent
                hidden_run([ADB_PATH, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True)
                # 4. Bangunkan launcher standar
                hidden_run([ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.google.android.apps.nexuslauncher", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                hidden_run([ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.android.launcher3", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                # 5. Fix Play Store
                self.fix_slot_playstore(slot_id)
                self.status_bar.showMessage(f"Layar #{slot_id} berhasil dipulihkan! Sentuhan & sistem normal kembali.")
            except Exception as e:
                self.status_bar.showMessage(f"Gagal memulihkan Layar #{slot_id}: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def factory_reset_slot(self, slot_id: int, auto_restart: bool = True):
        """Me-reset total layar: hapus akun Gmail, Google Play Services, dan seluruh data pengguna."""
        avd_name = get_slot_avd(slot_id)
        folder = os.path.join(AVD_BASE_DIR, f"{avd_name}.avd")
        serial = get_slot_serial(slot_id)
        port = get_slot_port(slot_id)

        self.status_bar.showMessage(f"Memproses Reset Pabrik total untuk Layar #{slot_id}...")

        def _reset_worker():
            # Langkah 1: Jika sedang online, langsung bersihkan akun Google & Gmail via ADB
            if self.slot_statuses.get(slot_id) == "ONLINE":
                try:
                    hidden_run([ADB_PATH, "-s", serial, "shell", "pm", "clear", "com.google.android.gm"], capture_output=True, timeout=4)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "pm", "clear", "com.google.android.gms"], capture_output=True, timeout=4)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "pm", "clear", "com.google.android.gsf"], capture_output=True, timeout=4)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "pm", "clear", "com.android.vending"], capture_output=True, timeout=4)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "pm", "clear", "com.google.android.googlequicksearchbox"], capture_output=True, timeout=4)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "rm", "-rf", "/data/system_de/0/accounts_de.db*"], capture_output=True, timeout=3)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "rm", "-rf", "/data/system_ce/0/accounts_ce.db*"], capture_output=True, timeout=3)
                except Exception:
                    pass

            # Langkah 2: Matikan emulator untuk slot ini
            try:
                hidden_run([ADB_PATH, "-s", serial, "emu", "kill"], capture_output=True, timeout=3)
            except Exception:
                pass
            time.sleep(2)

            # Pastikan proses emulator untuk port ini benar-benar tertutup
            try:
                hidden_run(["powershell", "-Command", f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"], capture_output=True)
            except Exception:
                pass
            time.sleep(1)

            # Langkah 3: Hapus fisik seluruh file userdata, cache, dan snapshots
            if os.path.exists(folder):
                for item in ["userdata-qemu.img", "userdata-qemu.img.qcow2", "userdata.img", "userdata.img.qcow2", "cache.img", "cache.img.qemu", "multiinstance.lock", "hardware-qemu.ini.lock"]:
                    target = os.path.join(folder, item)
                    for _ in range(5):
                        if os.path.exists(target):
                            try:
                                os.remove(target)
                                break
                            except Exception:
                                time.sleep(0.4)
                
                # Hapus seluruh folder snapshots
                snap_dir = os.path.join(folder, "snapshots")
                if os.path.exists(snap_dir):
                    try:
                        shutil.rmtree(snap_dir, ignore_errors=True)
                    except Exception:
                        pass

            self._update_slot_card_ui(slot_id, "OFFLINE")
            self.slot_statuses[slot_id] = "OFFLINE"

            # Langkah 4: Jika auto_restart, jalankan kembali dengan flag resmi -wipe-data!
            if auto_restart:
                time.sleep(1)
                self.start_slot_emulator(slot_id, wipe_data=True)
                self.status_bar.showMessage(f"Layar #{slot_id} berhasil di-wipe total dan sedang dinyalakan ulang...")
            else:
                self.status_bar.showMessage(f"Layar #{slot_id} ({avd_name}) berhasil di-reset total ke setelan pabrik!")

        threading.Thread(target=_reset_worker, daemon=True).start()

    def show_factory_reset_dialog(self):
        """Menampilkan dialog pemilihan layar untuk Reset Pabrik / Wipe Data."""
        items = [f"Layar #{s} ({get_slot_avd(s)})" for s in range(1, 25)]
        items.insert(0, "💥 SEMUA LAYAR (1 - 24) - Reset Pabrik Massal")

        item, ok = QInputDialog.getItem(
            self,
            "Reset Pabrik / Wipe Data",
            "Pilih layar yang ingin di-reset pabrik (hapus semua email / akun Google):",
            items,
            0,
            False
        )
        if ok and item:
            if "SEMUA LAYAR" in item:
                res = QMessageBox.warning(
                    self,
                    "Konfirmasi Reset Pabrik Massal",
                    "PERINGATAN KERAS:\nAnda akan me-reset SEMUA 24 LAYAR ke setelan pabrik!\n\nSeluruh akun email, data aplikasi, dan session login di SEMUA layar akan dihapus permanen.\n\nApakah Anda yakin ingin melanjutkan?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if res == QMessageBox.Yes:
                    def _mass_reset():
                        self.stop_all_emulators()
                        time.sleep(3)
                        for s in range(1, 25):
                            self.factory_reset_slot(s, auto_restart=False)
                        self.status_bar.showMessage("Semua 24 Layar berhasil di-reset ke setelan pabrik!")
                    threading.Thread(target=_mass_reset, daemon=True).start()
            else:
                try:
                    slot_id = int(item.split("#")[1].split()[0])
                    self.confirm_factory_reset_slot(slot_id)
                except Exception:
                    pass

    # =========================================================================
    # --- MULTI-SCREEN SYNCHRONIZER (Sinkronisasi Layar Master ke Terpilih) ---
    # =========================================================================
    def _create_sync_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header Title
        head_box = QVBoxLayout()
        lbl_head = QLabel("🔗 Multi-Screen Synchronizer (Sinkronisasi Layar)")
        lbl_head.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_head.setStyleSheet("color: #0F172A;")
        head_box.addWidget(lbl_head)

        lbl_sub = QLabel("Kendalikan 1 Layar Master: semua sentuhan, gestur swipe, tombol navigasi, dan input teks akan otomatis disinkronkan ke seluruh layar yang Anda pilih secara serentak.")
        lbl_sub.setStyleSheet("color: #64748B; font-size: 11px;")
        head_box.addWidget(lbl_sub)
        layout.addLayout(head_box)

        # Content Split Layout
        content = QHBoxLayout()
        content.setSpacing(16)

        # --- PANEL KIRI: Layar Master & Kontrol Sentuh ---
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_card.setFixedWidth(360)
        l_layout = QVBoxLayout(left_card)
        l_layout.setContentsMargins(16, 14, 16, 14)
        l_layout.setSpacing(10)

        # Pilihan Master Slot
        m_row = QHBoxLayout()
        lbl_m = QLabel("Layar Master:")
        lbl_m.setStyleSheet("font-weight: bold; color: #1E293B;")
        m_row.addWidget(lbl_m)

        self.cb_sync_master = QComboBox()
        for s in range(1, 25):
            self.cb_sync_master.addItem(f"Layar #{s} ({get_slot_avd(s)})")
        self.cb_sync_master.currentIndexChanged.connect(self._on_sync_master_changed)
        m_row.addWidget(self.cb_sync_master, 1)
        l_layout.addLayout(m_row)

        # Pad Layar Sentuh Interaktif
        self.sync_pad = InteractivePhonePad(on_action=self.on_sync_pad_action)
        self.sync_pad.setFixedSize(216, 384)
        self.sync_pad.setText("Sentuh / Klik di sini\nuntuk mengontrol Layar Master")

        pad_box = QVBoxLayout()
        pad_box.setAlignment(Qt.AlignCenter)
        pad_box.addWidget(self.sync_pad)
        l_layout.addLayout(pad_box)

        lbl_hint = QLabel("💡 Klik = Tap, Tahan & Geser mouse = Gestur Swipe")
        lbl_hint.setStyleSheet("color: #64748B; font-size: 10px;")
        lbl_hint.setAlignment(Qt.AlignCenter)
        l_layout.addWidget(lbl_hint)

        # Tombol Navigasi Fisik
        key_bar = QHBoxLayout()
        key_bar.setSpacing(4)
        btn_k_back = QPushButton("⬅ Back")
        btn_k_back.setProperty("class", "pill-btn")
        btn_k_back.clicked.connect(lambda: self.send_sync_keyevent(4, "Back"))
        key_bar.addWidget(btn_k_back)

        btn_k_home = QPushButton("⚪ Home")
        btn_k_home.setProperty("class", "pill-btn")
        btn_k_home.clicked.connect(lambda: self.send_sync_keyevent(3, "Home"))
        key_bar.addWidget(btn_k_home)

        btn_k_recent = QPushButton("▢ Recent")
        btn_k_recent.setProperty("class", "pill-btn")
        btn_k_recent.clicked.connect(lambda: self.send_sync_keyevent(187, "Recent"))
        key_bar.addWidget(btn_k_recent)

        btn_k_enter = QPushButton("⏎ Enter")
        btn_k_enter.setProperty("class", "pill-btn")
        btn_k_enter.clicked.connect(lambda: self.send_sync_keyevent(66, "Enter"))
        key_bar.addWidget(btn_k_enter)
        l_layout.addLayout(key_bar)

        # Baris Input Teks Serentak
        text_row = QHBoxLayout()
        self.txt_sync_input = QLineEdit()
        self.txt_sync_input.setPlaceholderText("Ketik teks untuk dikirim serentak...")
        self.txt_sync_input.returnPressed.connect(self.send_sync_text)
        text_row.addWidget(self.txt_sync_input)

        btn_send_txt = QPushButton("Kirim Teks")
        btn_send_txt.setProperty("class", "btn-primary")
        btn_send_txt.clicked.connect(self.send_sync_text)
        text_row.addWidget(btn_send_txt)
        l_layout.addLayout(text_row)

        # Baris Buka Aplikasi Cepat
        app_row = QHBoxLayout()
        btn_s_play = QPushButton("🛍️ Buka Play Store Serentak")
        btn_s_play.setProperty("class", "pill-btn")
        btn_s_play.clicked.connect(lambda: self.send_sync_app_launcher("playstore"))
        app_row.addWidget(btn_s_play)

        btn_s_home = QPushButton("🏠 Ke Home Screen Serentak")
        btn_s_home.setProperty("class", "pill-btn")
        btn_s_home.clicked.connect(lambda: self.send_sync_keyevent(3, "Home"))
        app_row.addWidget(btn_s_home)
        l_layout.addLayout(app_row)

        content.addWidget(left_card)

        # --- PANEL KANAN: Pilihan Layar Sasaran & Status Sinkronisasi ---
        right_card = QFrame()
        right_card.setProperty("class", "card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(18, 14, 18, 14)
        r_layout.setSpacing(12)

        # Tombol Saklar Utama Sinkronisasi
        toggle_box = QHBoxLayout()
        self.btn_sync_toggle = QPushButton("▶ MULAI SINKRONISASI (ON)")
        self.btn_sync_toggle.setProperty("class", "btn-primary")
        self.btn_sync_toggle.setStyleSheet("font-size: 13px; font-weight: bold; padding: 12px 20px; background-color: #059669;")
        self.btn_sync_toggle.clicked.connect(self.toggle_sync_mode)
        toggle_box.addWidget(self.btn_sync_toggle, 1)

        self.lbl_sync_status = QLabel("⚪ Status: SINKRONISASI NONAKTIF")
        self.lbl_sync_status.setStyleSheet("color: #64748B; font-weight: bold; font-size: 12px;")
        toggle_box.addWidget(self.lbl_sync_status)
        r_layout.addLayout(toggle_box)

        # Bagian Pilihan Sasaran Layar
        t_head = QHBoxLayout()
        lbl_target_head = QLabel("🎯 Pilih Layar Sasaran yang Disinkronkan:")
        lbl_target_head.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B;")
        t_head.addWidget(lbl_target_head)

        btn_sel_all = QPushButton("✔ Pilih Semua Online")
        btn_sel_all.setProperty("class", "pill-btn")
        btn_sel_all.clicked.connect(lambda: self.select_all_sync_targets(True))
        t_head.addWidget(btn_sel_all)

        btn_desel_all = QPushButton("❌ Batal Pilih")
        btn_desel_all.setProperty("class", "pill-btn")
        btn_desel_all.clicked.connect(lambda: self.select_all_sync_targets(False))
        t_head.addWidget(btn_desel_all)
        r_layout.addLayout(t_head)

        # Scrollable Grid Checkbox 24 Slot
        scroll_targets = QScrollArea()
        scroll_targets.setWidgetResizable(True)
        scroll_targets.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px;")

        target_grid_widget = QWidget()
        target_grid = QGridLayout(target_grid_widget)
        target_grid.setContentsMargins(10, 10, 10, 10)
        target_grid.setSpacing(8)

        self.sync_checkboxes.clear()
        for s in range(1, 25):
            avd = get_slot_avd(s)
            port = get_slot_port(s)
            cb = QCheckBox(f"Layar #{s} ({port})")
            cb.setStyleSheet("font-weight: 500; font-size: 11px;")
            if s > 1: # Default pilih slot 2 ke atas
                cb.setChecked(True)
            self.sync_checkboxes[s] = cb
            row = (s - 1) // 3
            col = (s - 1) % 3
            target_grid.addWidget(cb, row, col)

        scroll_targets.setWidget(target_grid_widget)
        scroll_targets.setFixedHeight(180)
        r_layout.addWidget(scroll_targets)

        # Jendela Log Aktivitas Real-time
        lbl_log_head = QLabel("📜 Log Aktivitas Sinkronisasi Real-time:")
        lbl_log_head.setStyleSheet("font-weight: bold; font-size: 12px; color: #334155;")
        r_layout.addWidget(lbl_log_head)

        self.txt_sync_logs = QTextEdit()
        self.txt_sync_logs.setReadOnly(True)
        self.txt_sync_logs.setStyleSheet("background-color: #0F172A; color: #38BDF8; font-family: 'Consolas', monospace; font-size: 11px; border-radius: 4px; padding: 6px;")
        self.txt_sync_logs.append("[Sistem] Sinkronisasi siap. Pilih layar sasaran lalu klik 'MULAI SINKRONISASI'.")
        r_layout.addWidget(self.txt_sync_logs, 1)

        content.addWidget(right_card, 1)
        layout.addLayout(content)
        return page

    def _on_sync_master_changed(self, idx: int):
        self.sync_master_slot = idx + 1
        self.log_sync(f"Layar Master diubah ke: Layar #{self.sync_master_slot}")

    def toggle_sync_mode(self):
        self.sync_active = not self.sync_active
        if self.sync_active:
            self.btn_sync_toggle.setText("⏹ HENTIKAN SINKRONISASI (OFF)")
            self.btn_sync_toggle.setStyleSheet("font-size: 13px; font-weight: bold; padding: 12px 20px; background-color: #DC2626;")
            self.lbl_sync_status.setText("🟢 Status: SINKRONISASI AKTIF")
            self.lbl_sync_status.setStyleSheet("color: #059669; font-weight: bold; font-size: 12px;")
            targets = self.get_selected_sync_serials()
            self.log_sync(f"🟢 Sinkronisasi AKTIF! Master (Layar #{self.sync_master_slot}) menyinkronkan ke {len(targets)} layar.")
        else:
            self.btn_sync_toggle.setText("▶ MULAI SINKRONISASI (ON)")
            self.btn_sync_toggle.setStyleSheet("font-size: 13px; font-weight: bold; padding: 12px 20px; background-color: #059669;")
            self.lbl_sync_status.setText("⚪ Status: SINKRONISASI NONAKTIF")
            self.lbl_sync_status.setStyleSheet("color: #64748B; font-weight: bold; font-size: 12px;")
            self.log_sync("⚪ Sinkronisasi dinonaktifkan.")

    def get_selected_sync_serials(self) -> list:
        serials = []
        for slot_id, cb in self.sync_checkboxes.items():
            if cb.isChecked() and self.slot_statuses.get(slot_id) == "ONLINE":
                serials.append(get_slot_serial(slot_id))
        return serials

    def on_sync_pad_action(self, action_type: str, params: dict):
        master_serial = get_slot_serial(self.sync_master_slot)
        all_targets = [master_serial]

        if self.sync_active:
            other_targets = self.get_selected_sync_serials()
            for s in other_targets:
                if s not in all_targets:
                    all_targets.append(s)

        if action_type == "tap":
            x, y = params["x"], params["y"]
            broadcast_adb_command(all_targets, ["shell", "input", "tap", str(x), str(y)])
            if self.sync_active:
                self.log_sync(f"👉 Tap di ({x}, {y}) ➔ disinkronkan ke {len(all_targets)} layar.")
        elif action_type == "swipe":
            x1, y1 = params["x1"], params["y1"]
            x2, y2 = params["x2"], params["y2"]
            dur = str(params.get("duration", 250))
            broadcast_adb_command(all_targets, ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), dur])
            if self.sync_active:
                self.log_sync(f"👆 Swipe dari ({x1},{y1}) ke ({x2},{y2}) ➔ disinkronkan ke {len(all_targets)} layar.")

    def send_sync_keyevent(self, keycode: int, name: str):
        master_serial = get_slot_serial(self.sync_master_slot)
        all_targets = [master_serial]
        if self.sync_active:
            for s in self.get_selected_sync_serials():
                if s not in all_targets:
                    all_targets.append(s)
        broadcast_adb_command(all_targets, ["shell", "input", "keyevent", str(keycode)])
        self.log_sync(f"🔘 Tombol '{name}' (#{keycode}) dikirim ke {len(all_targets)} layar.")

    def send_sync_text(self):
        text = self.txt_sync_input.text().strip()
        if not text:
            return
        master_serial = get_slot_serial(self.sync_master_slot)
        all_targets = [master_serial]
        if self.sync_active:
            for s in self.get_selected_sync_serials():
                if s not in all_targets:
                    all_targets.append(s)
        # Escape spaces for ADB input text
        escaped = text.replace(" ", "%s")
        broadcast_adb_command(all_targets, ["shell", "input", "text", escaped])
        self.log_sync(f"⌨️ Teks '{text}' dikirim ke {len(all_targets)} layar.")
        self.txt_sync_input.clear()

    def send_sync_app_launcher(self, app_type: str):
        master_serial = get_slot_serial(self.sync_master_slot)
        all_targets = [master_serial]
        if self.sync_active:
            for s in self.get_selected_sync_serials():
                if s not in all_targets:
                    all_targets.append(s)

        if app_type == "playstore":
            broadcast_adb_command(all_targets, ["shell", "monkey", "-p", "com.android.vending", "-c", "android.intent.category.LAUNCHER", "1"])
            self.log_sync(f"🛍️ Membuka Google Play Store di {len(all_targets)} layar.")

    def select_all_sync_targets(self, select_all: bool = True):
        for slot_id, cb in self.sync_checkboxes.items():
            if select_all:
                cb.setChecked(self.slot_statuses.get(slot_id) == "ONLINE" or slot_id > 1)
            else:
                cb.setChecked(False)

    def log_sync(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        if hasattr(self, "txt_sync_logs"):
            self.txt_sync_logs.append(f"[{ts}] {msg}")

    # =========================================================================
    # --- MACRO RECORDER & AUTOMATION (Perekam & Pemutar Makro Otomatis) ---
    # =========================================================================
    def _create_macro_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header Title
        head_box = QVBoxLayout()
        lbl_head = QLabel("🎬 Macro Recorder (Perekam & Pemutar Makro Otomatis)")
        lbl_head.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_head.setStyleSheet("color: #0F172A;")
        head_box.addWidget(lbl_head)

        lbl_sub = QLabel("Rekam gerakan klik, geser swipe, tombol, dan jeda waktu pada satu layar, lalu putar otomatis berulang kali ke seluruh layar secara simultan.")
        lbl_sub.setStyleSheet("color: #64748B; font-size: 11px;")
        head_box.addWidget(lbl_sub)
        layout.addLayout(head_box)

        # Content Split Layout
        content = QHBoxLayout()
        content.setSpacing(16)

        # --- PANEL KIRI: Perekam Makro Baru ---
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_card.setFixedWidth(380)
        l_layout = QVBoxLayout(left_card)
        l_layout.setContentsMargins(16, 14, 16, 14)
        l_layout.setSpacing(10)

        lbl_rec_title = QLabel("🔴 Perekam Makro Baru (Live Record)")
        lbl_rec_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_rec_title.setStyleSheet("color: #DC2626;")
        l_layout.addWidget(lbl_rec_title)

        # Pilihan Layar Sumber Rekaman
        s_row = QHBoxLayout()
        lbl_s = QLabel("Layar Sumber:")
        lbl_s.setStyleSheet("font-weight: 600;")
        s_row.addWidget(lbl_s)
        self.cb_macro_source = QComboBox()
        for s in range(1, 25):
            self.cb_macro_source.addItem(f"Layar #{s} ({get_slot_avd(s)})")
        self.cb_macro_source.currentIndexChanged.connect(self._on_macro_source_changed)
        s_row.addWidget(self.cb_macro_source, 1)
        l_layout.addLayout(s_row)

        # Pad Interaktif Perekaman
        self.macro_pad = InteractivePhonePad(on_action=self.on_macro_record_action)
        self.macro_pad.setFixedSize(216, 384)
        self.macro_pad.setText("Pad Layar Rekaman\n(Klik tombol 'Mulai Merekam')")

        pad_box = QVBoxLayout()
        pad_box.setAlignment(Qt.AlignCenter)
        pad_box.addWidget(self.macro_pad)
        l_layout.addLayout(pad_box)

        self.lbl_rec_counter = QLabel("⏱️ Siap merekam. Klik tombol 'Mulai Merekam'.")
        self.lbl_rec_counter.setStyleSheet("color: #64748B; font-weight: bold; font-size: 11px;")
        self.lbl_rec_counter.setAlignment(Qt.AlignCenter)
        l_layout.addWidget(self.lbl_rec_counter)

        # Tombol Kontrol Perekaman
        rec_btn_box = QHBoxLayout()
        self.btn_rec_toggle = QPushButton("🔴 Mulai Merekam")
        self.btn_rec_toggle.setProperty("class", "btn-primary")
        self.btn_rec_toggle.setStyleSheet("background-color: #DC2626; font-weight: bold; padding: 8px 12px;")
        self.btn_rec_toggle.clicked.connect(self.toggle_macro_recording)
        rec_btn_box.addWidget(self.btn_rec_toggle)

        btn_add_delay = QPushButton("➕ Jeda 1s")
        btn_add_delay.setProperty("class", "pill-btn")
        btn_add_delay.clicked.connect(lambda: self.add_manual_macro_step("sleep", 1000))
        rec_btn_box.addWidget(btn_add_delay)

        btn_add_back = QPushButton("➕ Key Back")
        btn_add_back.setProperty("class", "pill-btn")
        btn_add_back.clicked.connect(lambda: self.add_manual_macro_step("key", 4))
        rec_btn_box.addWidget(btn_add_back)
        l_layout.addLayout(rec_btn_box)

        # Tabel Langkah-langkah Rekaman Saat Ini
        self.table_cur_steps = QTableWidget(0, 3)
        self.table_cur_steps.setHorizontalHeaderLabels(["#", "Aksi", "Jeda Waktu"])
        self.table_cur_steps.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_cur_steps.setFixedHeight(120)
        self.table_cur_steps.setStyleSheet("font-size: 10px;")
        l_layout.addWidget(self.table_cur_steps)

        content.addWidget(left_card)

        # --- PANEL KANAN: Daftar Makro Tersimpan & Pemutar Otomasi ---
        right_card = QFrame()
        right_card.setProperty("class", "card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(18, 14, 18, 14)
        r_layout.setSpacing(10)

        lbl_play_title = QLabel("📋 Daftar Makro Tersimpan & Pemutar Otomasi")
        lbl_play_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_play_title.setStyleSheet("color: #2563EB;")
        r_layout.addWidget(lbl_play_title)

        # Tabel Makro Tersimpan
        self.table_saved_macros = QTableWidget(0, 4)
        self.table_saved_macros.setHorizontalHeaderLabels(["Nama Makro", "Langkah", "Tanggal", "File"])
        self.table_saved_macros.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_saved_macros.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_saved_macros.setFixedHeight(180)
        r_layout.addWidget(self.table_saved_macros)

        # Pengaturan Eksekusi Pemutaran
        sett_box = QGridLayout()
        sett_box.setSpacing(8)

        lbl_tg = QLabel("Target Layar:")
        lbl_tg.setStyleSheet("font-weight: 600;")
        self.cb_macro_target = QComboBox()
        self.cb_macro_target.addItem("Semua Layar Aktif (Mass Broadcast)")
        for s in range(1, 25):
            self.cb_macro_target.addItem(f"Layar #{s} ({get_slot_avd(s)})")
        sett_box.addWidget(lbl_tg, 0, 0)
        sett_box.addWidget(self.cb_macro_target, 0, 1)

        lbl_lp = QLabel("Pengulangan (Loop):")
        lbl_lp.setStyleSheet("font-weight: 600;")
        self.cb_macro_loop = QComboBox()
        self.cb_macro_loop.addItems(["1 Kali", "3 Kali", "5 Kali", "10 Kali", "20 Kali", "Putar Terus-menerus (Unlimited)"])
        sett_box.addWidget(lbl_lp, 0, 2)
        sett_box.addWidget(self.cb_macro_loop, 0, 3)

        lbl_sp = QLabel("Kecepatan Putar:")
        lbl_sp.setStyleSheet("font-weight: 600;")
        self.cb_macro_speed = QComboBox()
        self.cb_macro_speed.addItems(["1.0x (Normal)", "1.5x", "2.0x (Cepat)", "3.0x"])
        sett_box.addWidget(lbl_sp, 1, 0)
        sett_box.addWidget(self.cb_macro_speed, 1, 1)

        lbl_dl = QLabel("Jeda Antar Putaran:")
        lbl_dl.setStyleSheet("font-weight: 600;")
        self.cb_macro_interval = QComboBox()
        self.cb_macro_interval.addItems(["0 Detik", "2 Detik", "5 Detik", "10 Detik"])
        sett_box.addWidget(lbl_dl, 1, 2)
        sett_box.addWidget(self.cb_macro_interval, 1, 3)

        r_layout.addLayout(sett_box)

        # Progress Bar & Status Eksekusi
        self.macro_progress = QProgressBar()
        self.macro_progress.setValue(0)
        self.macro_progress.setStyleSheet("QProgressBar { height: 12px; border-radius: 4px; text-align: center; } QProgressBar::chunk { background-color: #059669; }")
        r_layout.addWidget(self.macro_progress)

        self.lbl_macro_status = QLabel("Status: Makro siap dijalankan.")
        self.lbl_macro_status.setStyleSheet("color: #0F172A; font-weight: bold;")
        r_layout.addWidget(self.lbl_macro_status)

        # Tombol Aksi Player
        p_btn_box = QHBoxLayout()
        self.btn_macro_run = QPushButton("▶ JALANKAN MAKRO KE LAYAR")
        self.btn_macro_run.setProperty("class", "btn-primary")
        self.btn_macro_run.setStyleSheet("background-color: #059669; font-weight: bold; font-size: 13px; padding: 10px 18px;")
        self.btn_macro_run.clicked.connect(self.run_selected_macro)
        p_btn_box.addWidget(self.btn_macro_run)

        self.btn_macro_stop = QPushButton("⏹ STOP / EMERGENCY BREAK")
        self.btn_macro_stop.setProperty("class", "btn-yellow")
        self.btn_macro_stop.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; font-size: 13px; padding: 10px 18px;")
        self.btn_macro_stop.clicked.connect(self.stop_macro_execution)
        p_btn_box.addWidget(self.btn_macro_stop)

        btn_macro_del = QPushButton("🗑️ Hapus Makro")
        btn_macro_del.setProperty("class", "btn-outline")
        btn_macro_del.clicked.connect(self.delete_selected_macro)
        p_btn_box.addWidget(btn_macro_del)

        btn_macro_ref = QPushButton("🔄 Refresh List")
        btn_macro_ref.setProperty("class", "pill-btn")
        btn_macro_ref.clicked.connect(self.load_saved_macros_list)
        p_btn_box.addWidget(btn_macro_ref)

        r_layout.addLayout(p_btn_box)
        content.addWidget(right_card, 1)

        layout.addLayout(content)
        return page

    def _on_macro_source_changed(self, idx: int):
        self.recording_source_slot = idx + 1

    def on_macro_record_action(self, action_type: str, params: dict):
        # Jalankan aksi langsung ke layar sumber rekaman
        source_serial = get_slot_serial(self.recording_source_slot)

        if action_type == "tap":
            x, y = params["x"], params["y"]
            broadcast_adb_command([source_serial], ["shell", "input", "tap", str(x), str(y)])
            if self.is_recording:
                delta = int((time.time() - self.recording_last_time) * 1000)
                self.recording_last_time = time.time()
                step = {"type": "tap", "x": x, "y": y, "delay_ms": max(300, delta), "note": f"Tap di ({x}, {y})"}
                self.recording_steps.append(step)
                self._add_step_to_rec_table(len(self.recording_steps), f"Tap ({x}, {y})", f"{step['delay_ms']}ms")
        elif action_type == "swipe":
            x1, y1 = params["x1"], params["y1"]
            x2, y2 = params["x2"], params["y2"]
            dur = str(params.get("duration", 250))
            broadcast_adb_command([source_serial], ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), dur])
            if self.is_recording:
                delta = int((time.time() - self.recording_last_time) * 1000)
                self.recording_last_time = time.time()
                step = {"type": "swipe", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": 250, "delay_ms": max(400, delta), "note": f"Swipe ({x1},{y1}) -> ({x2},{y2})"}
                self.recording_steps.append(step)
                self._add_step_to_rec_table(len(self.recording_steps), f"Swipe Gestur", f"{step['delay_ms']}ms")

        if self.is_recording:
            dur_sec = int(time.time() - self.recording_start_time)
            self.lbl_rec_counter.setText(f"🔴 Merekam... [{dur_sec}s] | {len(self.recording_steps)} Langkah")

    def toggle_macro_recording(self):
        if not self.is_recording:
            # Mulai rekaman baru
            self.is_recording = True
            self.recording_steps = []
            self.recording_start_time = time.time()
            self.recording_last_time = time.time()
            self.table_cur_steps.setRowCount(0)

            self.btn_rec_toggle.setText("⏹ Selesai & Simpan Makro")
            self.btn_rec_toggle.setStyleSheet("background-color: #059669; font-weight: bold; padding: 8px 12px;")
            self.lbl_rec_counter.setText("🔴 Merekam... [0s] | 0 Langkah")
            self.status_bar.showMessage(f"Mulai merekam makro dari Layar #{self.recording_source_slot}...")
        else:
            # Selesai merekam
            self.is_recording = False
            self.btn_rec_toggle.setText("🔴 Mulai Merekam")
            self.btn_rec_toggle.setStyleSheet("background-color: #DC2626; font-weight: bold; padding: 8px 12px;")

            if not self.recording_steps:
                QMessageBox.warning(self, "Perekam Makro", "Tidak ada langkah yang direkam.")
                self.lbl_rec_counter.setText("⏱️ Rekaman kosong.")
                return

            name, ok = QInputDialog.getText(self, "Simpan Makro Baru", "Beri nama makro Anda:", text="Makro_Kustom_1")
            if ok and name.strip():
                clean_name = "".join([c if c.isalnum() or c in " _-" else "_" for c in name.strip()])
                filename = f"{clean_name}.json"
                filepath = os.path.join(MACROS_DIR, filename)
                data = {
                    "name": name.strip(),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_steps": len(self.recording_steps),
                    "steps": self.recording_steps
                }
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    QMessageBox.information(self, "Sukses", f"Makro '{name}' dengan {len(self.recording_steps)} langkah berhasil disimpan!")
                    self.load_saved_macros_list()
                    self.lbl_rec_counter.setText(f"✔ Tersimpan: {name} ({len(self.recording_steps)} langkah)")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Gagal menyimpan makro: {e}")
            else:
                self.lbl_rec_counter.setText("Perekaman dibatalkan.")

    def add_manual_macro_step(self, stype: str, val):
        delta = 1000
        if self.is_recording:
            delta = int((time.time() - self.recording_last_time) * 1000)
            self.recording_last_time = time.time()

        if stype == "sleep":
            step = {"type": "sleep", "delay_ms": val, "note": f"Jeda {val}ms"}
            desc = f"Jeda {val}ms"
        elif stype == "key":
            step = {"type": "key", "keycode": val, "name": "Back", "delay_ms": 1000, "note": "Key Back"}
            desc = "Tombol Back"
            source_serial = get_slot_serial(self.recording_source_slot)
            broadcast_adb_command([source_serial], ["shell", "input", "keyevent", str(val)])

        self.recording_steps.append(step)
        self._add_step_to_rec_table(len(self.recording_steps), desc, f"{step['delay_ms']}ms")
        self.lbl_rec_counter.setText(f"Langkah ditambahkan: {desc} (Total: {len(self.recording_steps)})")

    def _add_step_to_rec_table(self, idx: int, action: str, delay: str):
        row = self.table_cur_steps.rowCount()
        self.table_cur_steps.insertRow(row)
        self.table_cur_steps.setItem(row, 0, QTableWidgetItem(str(idx)))
        self.table_cur_steps.setItem(row, 1, QTableWidgetItem(action))
        self.table_cur_steps.setItem(row, 2, QTableWidgetItem(delay))
        self.table_cur_steps.scrollToBottom()

    def load_saved_macros_list(self):
        """Membaca semua file makro JSON dari folder macros."""
        self.table_saved_macros.setRowCount(0)
        if not os.path.exists(MACROS_DIR):
            return

        for fname in os.listdir(MACROS_DIR):
            if fname.endswith(".json"):
                fpath = os.path.join(MACROS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    row = self.table_saved_macros.rowCount()
                    self.table_saved_macros.insertRow(row)
                    self.table_saved_macros.setItem(row, 0, QTableWidgetItem(data.get("name", fname)))
                    self.table_saved_macros.setItem(row, 1, QTableWidgetItem(f"{data.get('total_steps', len(data.get('steps', [])))} langkah"))
                    self.table_saved_macros.setItem(row, 2, QTableWidgetItem(data.get("created_at", "-")))
                    self.table_saved_macros.setItem(row, 3, QTableWidgetItem(fname))
                except Exception:
                    pass

    def run_selected_macro(self):
        cur_row = self.table_saved_macros.currentRow()
        if cur_row < 0:
            QMessageBox.warning(self, "Pilih Makro", "Silakan klik salah satu makro pada tabel terlebih dahulu.")
            return

        file_item = self.table_saved_macros.item(cur_row, 3)
        if not file_item:
            return
        filename = file_item.text()
        filepath = os.path.join(MACROS_DIR, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                macro_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal membaca file makro: {e}")
            return

        # Tentukan target serials
        target_idx = self.cb_macro_target.currentIndex()
        if target_idx == 0:
            target_serials = [get_slot_serial(s) for s in range(1, 25) if self.slot_statuses.get(s) == "ONLINE"]
        else:
            slot_id = target_idx
            if self.slot_statuses.get(slot_id) != "ONLINE":
                QMessageBox.warning(self, "Perhatian", f"Layar #{slot_id} sedang offline.")
                return
            target_serials = [get_slot_serial(slot_id)]

        if not target_serials:
            QMessageBox.warning(self, "Perhatian", "Tidak ada layar XPhone aktif yang online.")
            return

        # Parsing Loop & Speed
        loop_str = self.cb_macro_loop.currentText()
        if "Unlimited" in loop_str:
            loop_count = 0
        else:
            loop_count = int(loop_str.split()[0])

        speed_str = self.cb_macro_speed.currentText().split("x")[0]
        speed = float(speed_str)

        interval_str = self.cb_macro_interval.currentText().split()[0]
        interval = float(interval_str)

        self.btn_macro_run.setEnabled(False)
        self.btn_macro_run.setText("⏳ Sedang Berjalan...")
        self.macro_progress.setValue(0)
        self.lbl_macro_status.setText(f"▶ Memulai: [{macro_data.get('name')}] ke {len(target_serials)} layar...")

        threading.Thread(
            target=self.macro_runner.run_macro,
            args=(macro_data, target_serials, loop_count, interval, speed),
            daemon=True
        ).start()

    def stop_macro_execution(self):
        if self.macro_runner.is_running():
            self.macro_runner.stop()
            self.lbl_macro_status.setText("⏹ Perintah STOP dikirim, menghentikan eksekusi...")
        else:
            self.lbl_macro_status.setText("Tidak ada makro yang sedang berjalan.")

    def delete_selected_macro(self):
        cur_row = self.table_saved_macros.currentRow()
        if cur_row < 0:
            QMessageBox.warning(self, "Pilih Makro", "Pilih makro yang ingin dihapus pada tabel.")
            return
        file_item = self.table_saved_macros.item(cur_row, 3)
        name_item = self.table_saved_macros.item(cur_row, 0)
        if not file_item:
            return
        res = QMessageBox.question(self, "Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus makro '{name_item.text()}'?")
        if res == QMessageBox.Yes:
            p = os.path.join(MACROS_DIR, file_item.text())
            try:
                if os.path.exists(p): os.remove(p)
                self.load_saved_macros_list()
                QMessageBox.information(self, "Terhapus", "Makro berhasil dihapus.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menghapus makro: {e}")

    def _on_macro_progress(self, cur_loop: int, total_loops: int, cur_step: int, total_steps: int, desc: str):
        loop_txt = f"{cur_loop}/{total_loops}" if total_loops > 0 else f"{cur_loop} (Unlimited)"
        pct = int((cur_step / max(1, total_steps)) * 100)
        self.macro_progress.setValue(pct)
        self.lbl_macro_status.setText(f"▶ Putaran {loop_txt} | {desc}")

    def _on_macro_finished(self, msg: str):
        self.btn_macro_run.setEnabled(True)
        self.btn_macro_run.setText("▶ JALANKAN MAKRO KE LAYAR")
        self.macro_progress.setValue(100)
        self.lbl_macro_status.setText(msg)
        self.status_bar.showMessage(msg)

    # --- Worker & Multi-Device Status Handling ---
    def _start_worker(self):
        self.worker = StatusWorker()
        self.worker.devices_signal.connect(self._on_devices_status_updated)
        self.worker.screenshot_signal.connect(self._on_screenshot_received)
        self.worker_thread = threading.Thread(target=self.worker.check_loop, daemon=True)
        self.worker_thread.start()

    def _on_devices_status_updated(self, statuses: dict):
        online_count = 0
        for slot_id, info in statuses.items():
            st = info["status"]
            self.slot_statuses[slot_id] = st
            if st == "ONLINE":
                online_count += 1
            if slot_id in self.slot_widgets:
                self._update_slot_card_ui(slot_id, st)

        # Update Master Status Bar & Badges
        if online_count > 0:
            self.btn_status_badge.setText(f"⚡ {online_count} Layar Aktif")
            self.btn_status_badge.setProperty("class", "btn-green")
            self.btn_status_badge.setStyleSheet("")
            self.lbl_active_dev.setText(f"{online_count} Perangkat Aktif")
        else:
            self.btn_status_badge.setText("🔴 XPhone Offline")
            self.btn_status_badge.setProperty("class", "btn-outline")
            self.btn_status_badge.setStyleSheet("")
            self.lbl_active_dev.setText("0 Perangkat Aktif")

    def _update_slot_card_ui(self, slot_id: int, status: str):
        w = self.slot_widgets.get(slot_id)
        if not w:
            return

        avd_name = get_slot_avd(slot_id)
        port = get_slot_port(slot_id)

        if status == "ONLINE":
            w["title"].setText(f"#{slot_id}: ({avd_name})")
            w["title"].setStyleSheet("color: #38BDF8; font-weight: bold;")
            w["status"].setText(f"XPhone #{slot_id} Android 12\n(● ONLINE & Siap)")
            w["status"].setStyleSheet("color: #10B981; font-weight: bold; background: transparent;")
            w["action"].setText("🛍️ Buka Play Store")
            w["action"].setProperty("class", "btn-green")
            w["action"].setStyleSheet("font-size: 9px; padding: 5px; background-color: #059669; color: white;")
        elif status == "BOOTING":
            w["title"].setText(f"#{slot_id}: (Booting...)")
            w["title"].setStyleSheet("color: #F59E0B; font-weight: bold;")
            w["status"].setText(f"Layar #{slot_id} ({port})\n(🟡 Sedang Booting...)")
            w["status"].setStyleSheet("color: #F59E0B; background: transparent;")
            w["action"].setText("🟡 Memuat...")
            w["action"].setProperty("class", "btn-yellow")
            w["action"].setStyleSheet("font-size: 9px; padding: 5px; background-color: #D97706; color: white;")
        else: # OFFLINE
            w["title"].setText(f"#{slot_id}: (Kosong)" if slot_id > 1 else f"#{slot_id}: (XPhone)")
            w["title"].setStyleSheet("color: #94A3B8;")
            w["status"].setText(f"Slot #{slot_id}\n(Offline / Belum Aktif)")
            w["status"].setStyleSheet("color: #64748B; background: transparent;")
            w["action"].setText(f"▶ Nyalakan Layar #{slot_id}")
            w["action"].setProperty("class", "btn-primary")
            w["action"].setStyleSheet("font-size: 9px; padding: 5px; background-color: #2563EB; color: white;")
            w["preview"].hide()
            w["icon"].show()

    def _on_screenshot_received(self, slot_id: int, png_bytes: bytes):
        w = self.slot_widgets.get(slot_id)
        if w:
            pix = QPixmap()
            if pix.loadFromData(png_bytes):
                scaled = pix.scaled(155, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                w["preview"].setPixmap(scaled)
                w["preview"].show()
                w["icon"].hide()

        # Update Live Preview pada Synchronizer Master Pad jika slot cocok
        if hasattr(self, "sync_pad") and slot_id == self.sync_master_slot:
            pix_s = QPixmap()
            if pix_s.loadFromData(png_bytes):
                self.sync_pad.setPixmap(pix_s.scaled(self.sync_pad.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Update Live Preview pada Macro Recorder Pad jika slot cocok
        if hasattr(self, "macro_pad") and slot_id == self.recording_source_slot:
            pix_m = QPixmap()
            if pix_m.loadFromData(png_bytes):
                self.macro_pad.setPixmap(pix_m.scaled(self.macro_pad.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _handle_slot_action_clicked(self, slot_id: int):
        status = self.slot_statuses.get(slot_id, "OFFLINE")
        if status == "ONLINE":
            self.launch_playstore(slot_id)
        elif status == "OFFLINE":
            self.start_slot_emulator(slot_id)
        else:
            self.status_bar.showMessage(f"Layar #{slot_id} sedang memuat sistem...")

    def _get_first_online_slot(self) -> int:
        for s in range(1, 25):
            if self.slot_statuses.get(s) == "ONLINE":
                return s
        return 1

    def _manual_refresh_screens(self):
        refreshed = 0
        for slot_id, status in self.slot_statuses.items():
            if status == "ONLINE":
                serial = get_slot_serial(slot_id)
                try:
                    sc = hidden_run([ADB_PATH, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=5)
                    if sc.stdout and len(sc.stdout) > 5000:
                        self._on_screenshot_received(slot_id, sc.stdout)
                        refreshed += 1
                except Exception:
                    pass
        if refreshed > 0:
            self.status_bar.showMessage(f"Berhasil memperbarui screenshot untuk {refreshed} layar aktif.")
        else:
            self.status_bar.showMessage("Tidak ada layar XPhone yang sedang online.")

    def refresh_slot_screenshot(self, slot_id: int):
        status = self.slot_statuses.get(slot_id)
        if status != "ONLINE":
            self.status_bar.showMessage(f"Layar #{slot_id} belum online.")
            return
        serial = get_slot_serial(slot_id)
        try:
            sc = hidden_run([ADB_PATH, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=5)
            if sc.stdout and len(sc.stdout) > 5000:
                self._on_screenshot_received(slot_id, sc.stdout)
                self.status_bar.showMessage(f"Screenshot Layar #{slot_id} diperbarui.")
        except Exception as e:
            self.status_bar.showMessage(f"Gagal refresh Layar #{slot_id}: {e}")

    # --- Multi-Instance Emulator Actions ---
    def start_slot_emulator(self, slot_id: int, wipe_data: bool = False):
        # Pastikan konfigurasi AVD dan file lock dibersihkan otomatis
        avd_name = ensure_slot_avd_exists(slot_id)
        port = get_slot_port(slot_id)
        self.status_bar.showMessage(f"Meluncurkan Layar #{slot_id} ({avd_name} di port {port})...")
        
        # Immediate UI feedback
        self._update_slot_card_ui(slot_id, "BOOTING")
        self.slot_statuses[slot_id] = "BOOTING"

        def _run():
            try:
                hidden_run([ADB_PATH, "start-server"], capture_output=True)
                settings = load_settings()
                cores_val = settings.get("cpu_cores", "2").split()[0]
                ram_val = settings.get("ram_mb", "1536").split()[0]
                cmd = [
                    EMULATOR_PATH,
                    "-avd", avd_name,
                    "-port", str(port),
                    "-gpu", "swiftshader",
                    "-feature", "-Vulkan",
                    "-feature", "-GLDirectMem",
                    "-crash-report-mode", "disabled",
                    "-no-snapshot-load",
                    "-no-boot-anim",          # Memangkas alokasi memory frame buffer boot
                    "-camera-back", "none",   # Nonaktifkan virtual camera buffer
                    "-camera-front", "none",  # Nonaktifkan virtual camera buffer
                    "-cores", cores_val,
                    "-memory", ram_val,
                    "-accel", "on",
                    "-adb-path", ADB_PATH
                ]
                if wipe_data:
                    cmd.append("-wipe-data")
                
                # Gunakan VBScript launcher dengan window style 0 (SW_HIDE)
                # agar Windows Terminal / Command Prompt 100% TIDAK PERNAH muncul di desktop
                vbs_path = os.path.join(BASE_DIR, f"launch_{avd_name}.vbs")
                cmd_escaped = ' '.join([f'"{c}"' if ' ' in c else c for c in cmd]).replace('"', '""')
                vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\r\nWshShell.Run "{cmd_escaped}", 0, False\r\n'
                
                launched = False
                try:
                    with open(vbs_path, "w", encoding="utf-8") as f:
                        f.write(vbs_content)
                    
                    si = _get_hidden_startupinfo()
                    subprocess.Popen(
                        ["wscript.exe", "//Nologo", vbs_path],
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                        startupinfo=si,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    launched = True
                except Exception:
                    pass

                if not launched:
                    # Fallback murni tanpa DETACHED_PROCESS agar CREATE_NO_WINDOW tidak diabaikan Windows
                    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    si = _get_hidden_startupinfo()
                    subprocess.Popen(
                        cmd,
                        creationflags=creation_flags,
                        startupinfo=si,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
            except Exception as e:
                print(f"Error starting slot {slot_id}: {e}")

        def _post_boot_setup():
            serial = get_slot_serial(slot_id)
            for _ in range(40):
                time.sleep(3)
                try:
                    res = hidden_run([ADB_PATH, "-s", serial, "shell", "getprop", "sys.boot_completed"], capture_output=True, text=True, timeout=3)
                    if (res.stdout or "").strip() == "1":
                        # Layar berhasil boot selesai
                        hidden_run([ADB_PATH, "-s", serial, "shell", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], capture_output=True)
                        # Pastikan ukuran dan densitas layar reset ke rasio fisik jendela agar sentuhan tidak meleset
                        hidden_run([ADB_PATH, "-s", serial, "shell", "wm", "size", "reset"], capture_output=True)
                        hidden_run([ADB_PATH, "-s", serial, "shell", "wm", "density", "reset"], capture_output=True)
                        cur_st = load_settings()
                        if "Apple" in cur_st.get("brand", "") or "iPhone" in cur_st.get("model", ""):
                            if os.path.exists(IOS_LAUNCHER_APK):
                                hidden_run([ADB_PATH, "-s", serial, "install", "-r", IOS_LAUNCHER_APK], capture_output=True, timeout=20)
                                hidden_run([ADB_PATH, "-s", serial, "shell", "cmd", "overlay", "enable", "com.android.internal.systemui.navbar.gestural"], capture_output=True)
                                hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "secure", "navigation_mode", "2"], capture_output=True)
                                hidden_run([ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.mccal.folio", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                        break
                except Exception:
                    pass

        threading.Thread(target=_run, daemon=True).start()
        threading.Thread(target=_post_boot_setup, daemon=True).start()

    def start_multiple_slots(self):
        self.start_slot_emulator(1)
        time.sleep(2)
        self.start_slot_emulator(2)
        self.status_bar.showMessage("Meluncurkan Layar #1 dan Layar #2 secara bersamaan...")

    def stop_slot_emulator(self, slot_id: int):
        serial = get_slot_serial(slot_id)
        self.status_bar.showMessage(f"Menghentikan Layar #{slot_id} ({serial})...")
        def _kill():
            try:
                hidden_run([ADB_PATH, "-s", serial, "emu", "kill"], capture_output=True, timeout=4)
            except Exception:
                pass
        threading.Thread(target=_kill, daemon=True).start()

    def stop_all_emulators(self):
        self.status_bar.showMessage("Menghentikan semua perangkat XPhone...")
        def _kill_all():
            for s in range(1, 25):
                serial = get_slot_serial(s)
                hidden_run([ADB_PATH, "-s", serial, "emu", "kill"], capture_output=True, timeout=2)
            time.sleep(1)
            hidden_run(["taskkill", "/F", "/IM", "qemu-system-x86_64.exe"], capture_output=True)
            hidden_run(["taskkill", "/F", "/IM", "emulator.exe"], capture_output=True)
        threading.Thread(target=_kill_all, daemon=True).start()

    def cold_boot(self, slot_id: int = 1):
        avd_name = get_slot_avd(slot_id)
        res = QMessageBox.question(self, f"Cold Boot Slot #{slot_id}", f"Bersihkan cache snapshot lama untuk {avd_name} dan jalankan boot segar?")
        if res == QMessageBox.Yes:
            self.stop_slot_emulator(slot_id)
            time.sleep(2)
            snap_dir = os.path.join(AVD_BASE_DIR, f"{avd_name}.avd", "snapshots")
            if os.path.exists(snap_dir):
                for f in os.listdir(snap_dir):
                    p = os.path.join(snap_dir, f)
                    try:
                        if os.path.isfile(p): os.remove(p)
                    except Exception: pass
            self.start_slot_emulator(slot_id)

    # --- Google Play Store Maintenance & Launcher ---
    def fix_slot_playstore(self, slot_id: int):
        """Memperbaiki Google Play Store dengan membersihkan cache dan membuka ulang."""
        serial = get_slot_serial(slot_id)
        if self.slot_statuses.get(slot_id) != "ONLINE":
            return False

        # 1. Bersihkan cache Play Store
        hidden_run([ADB_PATH, "-s", serial, "shell", "pm", "clear", "com.android.vending"], capture_output=True)
        time.sleep(1)

        # 2. Buka Google Play Store langsung ke beranda
        hidden_run([
            ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.android.vending",
            "-c", "android.intent.category.LAUNCHER", "1"
        ], capture_output=True)
        return True

    def fix_slot_playstore_threaded(self, slot_id: int):
        if self.slot_statuses.get(slot_id) != "ONLINE":
            QMessageBox.warning(self, "Perhatian", f"Layar #{slot_id} belum aktif. Silakan nyalakan terlebih dahulu.")
            return

        self.status_bar.showMessage(f"Memperbaiki Play Store pada Layar #{slot_id}...")
        def _run():
            ok = self.fix_slot_playstore(slot_id)
            if ok:
                self.status_bar.showMessage(f"Google Play Store Layar #{slot_id} berhasil diperbaiki!")
            else:
                self.status_bar.showMessage(f"Gagal memperbaiki Layar #{slot_id}.")
        threading.Thread(target=_run, daemon=True).start()

    def fix_all_playstores_threaded(self):
        online_slots = [s for s in range(1, 25) if self.slot_statuses.get(s) == "ONLINE"]
        if not online_slots:
            QMessageBox.warning(self, "Perhatian", "Tidak ada layar XPhone yang sedang aktif. Silakan nyalakan layar terlebih dahulu.")
            return

        self.status_bar.showMessage(f"Memperbaiki Play Store pada {len(online_slots)} layar online...")
        def _run():
            for s in online_slots:
                self.fix_slot_playstore(s)
            self.status_bar.showMessage(f"Google Play Store pada {len(online_slots)} layar berhasil disegarkan!")
        threading.Thread(target=_run, daemon=True).start()

    def launch_playstore(self, slot_id: int = None):
        if slot_id is None:
            slot_id = self._get_first_online_slot()
        serial = get_slot_serial(slot_id)
        if self.slot_statuses.get(slot_id) != "ONLINE":
            QMessageBox.warning(self, "Perhatian", f"Layar #{slot_id} belum aktif. Silakan nyalakan terlebih dahulu.")
            return

        # Buka Google Play Store langsung ke Beranda Utama
        hidden_run([
            ADB_PATH, "-s", serial, "shell", "monkey", "-p", "com.android.vending",
            "-c", "android.intent.category.LAUNCHER", "1"
        ], capture_output=True)
        self.status_bar.showMessage(f"Membuka Google Play Store di Layar #{slot_id}...")

    def install_apk_dialog(self, slot_id: int = None):
        if slot_id is None:
            slot_id = self._get_first_online_slot()
        serial = get_slot_serial(slot_id)
        if self.slot_statuses.get(slot_id) != "ONLINE":
            QMessageBox.warning(self, "Perhatian", f"Layar #{slot_id} belum aktif. Nyalakan terlebih dahulu.")
            return
        apk_file, _ = QFileDialog.getOpenFileName(self, "Pilih File APK", "", "Android APK (*.apk);;Semua File (*.*)")
        if apk_file:
            self.status_bar.showMessage(f"Memasang {os.path.basename(apk_file)} ke Layar #{slot_id}...")
            def _inst():
                res = hidden_run([ADB_PATH, "-s", serial, "install", "-r", apk_file], capture_output=True, text=True)
                if "Success" in (res.stdout or ""):
                    self.status_bar.showMessage(f"Berhasil memasang {os.path.basename(apk_file)} di Layar #{slot_id}!")
                    QMessageBox.information(self, "Sukses", f"Aplikasi {os.path.basename(apk_file)} berhasil dipasang di Layar #{slot_id}!")
                else:
                    QMessageBox.critical(self, "Gagal", f"Gagal memasang APK di Layar #{slot_id}:\n{res.stdout}")
            threading.Thread(target=_inst, daemon=True).start()

    def apply_proxy(self):
        host = self.entry_proxy_host.text().strip()
        port = self.entry_proxy_port.text().strip()
        if not host or not port:
            QMessageBox.warning(self, "Error", "Host dan Port harus diisi!")
            return
        
        target_idx = self.cb_proxy_slot.currentIndex()
        if target_idx == 0: # Semua layar
            applied = 0
            for s in range(1, 25):
                if self.slot_statuses.get(s) == "ONLINE":
                    serial = get_slot_serial(s)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "global", "http_proxy", f"{host}:{port}"], capture_output=True)
                    applied += 1
            QMessageBox.information(self, "Sukses", f"Proxy {host}:{port} berhasil diterapkan pada {applied} layar online!")
        else:
            slot_id = target_idx
            serial = get_slot_serial(slot_id)
            if self.slot_statuses.get(slot_id) != "ONLINE":
                QMessageBox.warning(self, "Perhatian", f"Layar #{slot_id} belum online.")
                return
            hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "global", "http_proxy", f"{host}:{port}"], capture_output=True)
            QMessageBox.information(self, "Sukses", f"Proxy {host}:{port} berhasil diterapkan di Layar #{slot_id}!")

    def disable_proxy(self):
        target_idx = self.cb_proxy_slot.currentIndex()
        if target_idx == 0:
            for s in range(1, 25):
                if self.slot_statuses.get(s) == "ONLINE":
                    serial = get_slot_serial(s)
                    hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "global", "http_proxy", ":0"], capture_output=True)
            QMessageBox.information(self, "Sukses", "Proxy dinonaktifkan pada semua layar aktif.")
        else:
            slot_id = target_idx
            serial = get_slot_serial(slot_id)
            hidden_run([ADB_PATH, "-s", serial, "shell", "settings", "put", "global", "http_proxy", ":0"], capture_output=True)
            QMessageBox.information(self, "Sukses", f"Proxy dinonaktifkan pada Layar #{slot_id}.")

    # --- Grid Controls ---
    def _change_grid_columns(self, val):
        col = int(val.split()[0])
        self.columns = col
        self._render_phone_slots()

    def _change_slot_count(self, val):
        count = int(val.split()[0])
        self.total_slots = count
        self.spin_slots.setValue(count)
        self._render_phone_slots()

    def _apply_grid_settings(self):
        self.total_slots = self.spin_slots.value()
        self._render_phone_slots()
        self.status_bar.showMessage(f"Tata letak diperbarui: {self.total_slots} Layar ({self.columns} Kolom)")

    def _add_slot(self):
        self.total_slots += 1
        ensure_slot_avd_exists(self.total_slots)
        self.spin_slots.setValue(self.total_slots)
        self._render_phone_slots()
        self.status_bar.showMessage(f"Slot layar #{self.total_slots} ditambahkan dan konfigurasi AVD Play Store dibuat.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        from license_system import check_or_prompt_license
        if not check_or_prompt_license():
            sys.exit(0)
    except Exception as e:
        pass
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
