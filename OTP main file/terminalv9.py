#!/usr/bin/env python3
"""
fsociety_terminal_full.py
All-in-one: Login (hashed), theme, per-tab interactive shells, per-tab colors,
banner (big F), run/start helpers, run menuScanner/consoleScanner with foreground stdin,
Turkish encoding fallbacks, config save/load, GitHub/IG credits.

Contact / credit shown in banner/footer:
instagram-@yigitermozdamar  |  github-@yigit545
"""

import sys, os, platform, signal, hashlib, json, html, random
from PyQt5 import QtCore, QtWidgets, QtGui

# --------------------------- META & CONFIG ---------------------------
APP_VERSION = "2.0.0"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".edex_config.json")

# Banner: big 'F' letter (as requested)
BANNER = r"""


  OOOOO   TTTTTTTT  PPPPPP 
 O     O     TT     P     P
 O     O     TT     P     P
 O     O     TT     PPPPPP
 O     O     TT     P
  OOOOO      TT     P

  
"""

CREDIT_LINE = "credit: instagram-@yigitermozdamar | github-@yigit545"

# default colors
DEFAULT_FG = "#00ff9e"
DEFAULT_BG = "#0d0d0d"
DEFAULT_BANNER_COLOR = "#00ff9e"
DEFAULT_HIGHLIGHTS = {"error": "#ff4d4d", "success": "#39ff14", "fsociety": "#00ffd1"}

# avoid zombies on unix
if platform.system() != "Windows":
    try:
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    except Exception:
        pass

# --------------------------- Helpers ---------------------------
def load_config():
    cfg = {}
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def get_app_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def platform_open(target: str):
    """Open file/url with default app depending on OS."""
    try:
        if platform.system().lower().startswith("win"):
            # Use start via cmd
            os.system(f'start "" "{target}"')
        elif platform.system().lower().startswith("linux"):
            os.system(f'xdg-open "{target}" &')
        elif platform.system().lower().startswith("darwin"):
            os.system(f'open "{target}" &')
        else:
            return False
        return True
    except Exception:
        return False

# --------------------------- Login Dialog ---------------------------
class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("fsociety Terminal — Login")
        self.setFixedSize(420, 260)
        layout = QtWidgets.QVBoxLayout(self)
        self.cfg = load_config()

        layout.addWidget(QtWidgets.QLabel("Kullanıcı adı:"))
        self.username = QtWidgets.QLineEdit()
        layout.addWidget(self.username)

        layout.addWidget(QtWidgets.QLabel("Şifre:"))
        pw_row = QtWidgets.QHBoxLayout()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        pw_row.addWidget(self.password)
        self.toggle_pw = QtWidgets.QPushButton("Göster")
        self.toggle_pw.setCheckable(True)
        self.toggle_pw.setFixedWidth(80)
        self.toggle_pw.clicked.connect(self.on_toggle_pw)
        pw_row.addWidget(self.toggle_pw)
        layout.addLayout(pw_row)

        # theme selection
        theme_row = QtWidgets.QHBoxLayout()
        theme_row.addWidget(QtWidgets.QLabel("Tema:"))
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["Koyu", "Açık"])
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        self.status = QtWidgets.QLabel("")
        layout.addWidget(self.status)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.login_btn = QtWidgets.QPushButton("Giriş / Kaydet")
        self.login_btn.clicked.connect(self.on_login)
        btn_row.addWidget(self.login_btn)
        layout.addLayout(btn_row)

        # populate if exists
        if isinstance(self.cfg, dict):
            u = self.cfg.get("username")
            theme = self.cfg.get("theme", "dark")
            if u:
                self.username.setText(u)
            if theme == "light":
                self.theme_combo.setCurrentText("Açık")
            else:
                self.theme_combo.setCurrentText("Koyu")

    def on_toggle_pw(self):
        if self.toggle_pw.isChecked():
            self.password.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.toggle_pw.setText("Gizle")
        else:
            self.password.setEchoMode(QtWidgets.QLineEdit.Password)
            self.toggle_pw.setText("Göster")

    def on_login(self):
        user = self.username.text().strip()
        pw = self.password.text()
        if not user or not pw:
            self.status.setText("Kullanıcı adı ve şifre boş olamaz!")
            return

        cfg = self.cfg or {}
        pwhash = hash_password(pw)
        # if config has username+password -> validate
        if cfg.get("username") and cfg.get("password"):
            if user == cfg.get("username") and pwhash == cfg.get("password"):
                # update theme if changed
                cfg["theme"] = "light" if self.theme_combo.currentText() == "Açık" else "dark"
                save_config(cfg)
                self.accept()
                return
            else:
                self.status.setText("Hatalı kullanıcı adı veya şifre!")
                return
        else:
            # first-time save
            cfg["username"] = user
            cfg["password"] = pwhash
            cfg["theme"] = "light" if self.theme_combo.currentText() == "Açık" else "dark"
            cfg["fg"] = cfg.get("fg", DEFAULT_FG)
            cfg["bg"] = cfg.get("bg", DEFAULT_BG)
            cfg["banner_color"] = cfg.get("banner_color", DEFAULT_BANNER_COLOR)
            cfg["highlights"] = cfg.get("highlights", DEFAULT_HIGHLIGHTS)
            save_config(cfg)
            self.accept()
            return

# --------------------------- Terminal Tab (per-tab) ---------------------------
class TerminalTab(QtWidgets.QWidget):
    def __init__(self, name: str, username: str, cfg: dict):
        super().__init__()
        self.name = name
        self.username = username
        self.cfg = cfg or {}
        self.cwd = os.getcwd()
        self.history = []
        self.hist_pos = -1

        # colors
        self.fg = self.cfg.get("fg", DEFAULT_FG)
        self.bg = self.cfg.get("bg", DEFAULT_BG)
        self.banner_color = self.cfg.get("banner_color", DEFAULT_BANNER_COLOR)
        self.highlights = self.cfg.get("highlights", DEFAULT_HIGHLIGHTS.copy()).copy()

        # processes
        self.shell_proc = None            # interactive persistent shell for this tab
        self.foreground_proc = None       # if a "run" script is foreground, forward stdin to it
        self.child_procs = []             # background child processes list

        self._build_ui()
        self._start_shell()
        self.show_welcome()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # output: QTextEdit (we will insert HTML for highlights)
        self.output = QtWidgets.QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QtGui.QFont("Courier", 11))
        self.output.setStyleSheet(f"background-color: {self.bg}; color: {self.fg}; border:none; padding:6px;")
        layout.addWidget(self.output)

        # input row
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.prompt = QtWidgets.QLabel(f"{self.username}@fsociety:$")
        self.prompt.setStyleSheet(f"color: {self.fg}; font-weight: bold;")
        row.addWidget(self.prompt)

        self.input = QtWidgets.QLineEdit()
        self.input.setStyleSheet(f"background-color:#1a1a1a; color:{self.fg}; border:1px solid {self.fg}; padding:4px;")
        self.input.returnPressed.connect(self.on_enter)
        row.addWidget(self.input, 1)
        layout.addLayout(row)

        # allow up/down history
        self.input.installEventFilter(self)

    # ------------------ shell process ------------------
    def _start_shell(self):
        from PyQt5.QtCore import QProcess
        # start persistent shell which we will write commands to
        try:
            if self.shell_proc:
                try:
                    self.shell_proc.kill()
                except:
                    pass
                self.shell_proc = None
            self.shell_proc = QProcess(self)
            self.shell_proc.setProcessChannelMode(QProcess.MergedChannels)
            self.shell_proc.readyReadStandardOutput.connect(lambda p=self.shell_proc: self._on_proc_output(p))
            self.shell_proc.finished.connect(lambda code, status, p=self.shell_proc: self._on_proc_finished(p, code, status))
            try:
                self.shell_proc.setWorkingDirectory(self.cwd)
            except:
                pass

            if platform.system().lower().startswith("win"):
                prog = "powershell"
                args = ["-NoLogo", "-NoExit"]
            else:
                prog = "/bin/bash"
                args = ["-i"]
            self.shell_proc.start(prog, args)
            started = self.shell_proc.waitForStarted(1000)
            if not started:
                self._append_html("[error] Shell başlatılamadı.\n", kind="error")
        except Exception as e:
            self._append_html(f"[error] Shell başlatma hatası: {e}\n", kind="error")

    def _on_proc_output(self, proc):
        # pipe output of any child process (shell_proc or child_procs)
        try:
            raw = proc.readAllStandardOutput()
            # decoding with fallback for Windows (utf-8 -> cp850 -> latin1)
            if platform.system().lower().startswith("win"):
                try:
                    data = bytes(raw).decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        data = bytes(raw).decode("cp850")
                    except Exception:
                        data = bytes(raw).decode("latin1", errors="replace")
            else:
                data = bytes(raw).decode("utf-8", errors="replace")
        except Exception as e:
            data = f"[output decode error: {e}]\n"
        # append colored/highlighted
        self._append_html(data)

    def _on_proc_finished(self, proc, code, status):
        # called for any proc that connects to finished -> we'll handle via mapping
        # Try to remove from child_procs; if it was foreground_proc, clear that
        try:
            if proc in self.child_procs:
                self.child_procs.remove(proc)
        except Exception:
            pass
        if proc is self.foreground_proc:
            self.foreground_proc = None
            self._append_html(f"\n[foreground process exited: {code}]\n", kind="success")
        else:
            self._append_html(f"\n[process exited: {code}]\n", kind="success")

    # ------------------ UI helpers ------------------
    def _append_html(self, text: str, kind: str = None):
        """Insert text into QTextEdit with basic highlighting for keywords."""
        # escape html
        escaped = html.escape(text)
        # simple highlight mapping
        mapping = {
            "fsociety": self.highlights.get("fsociety", DEFAULT_HIGHLIGHTS["fsociety"]),
            "error": self.highlights.get("error", DEFAULT_HIGHLIGHTS["error"]),
            "success": self.highlights.get("success", DEFAULT_HIGHLIGHTS["success"]),
        }
        # do a simple case-insensitive tokenized replacement
        lower = escaped.lower()
        i = 0
        out = ""
        kws = sorted(mapping.keys(), key=lambda x: -len(x))
        while i < len(escaped):
            matched = False
            for kw in kws:
                L = len(kw)
                if lower.startswith(kw, i):
                    color = mapping[kw]
                    piece = escaped[i:i+L]
                    out += f'<span style="color:{color}; font-weight:700;">{piece}</span>'
                    i += L
                    matched = True
                    break
            if not matched:
                out += escaped[i]
                i += 1
        # wrap in pre to preserve formatting
        pre = f'<pre style="font-family:Courier, monospace; margin:0; color:{self.fg};">{out}</pre>'
        cursor = self.output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertHtml(pre)
        self.output.ensureCursorVisible()

    def show_welcome(self):
        # Welcome message using username
        welcome = f"Merhaba {self.username}! fsociety terminaline hoşgeldin.\nVersiyon: {APP_VERSION} (App)\n"
        self._append_html(welcome, kind="success")
        # banner colored
        banner_html = f'<pre style="font-family:Courier, monospace; margin:0; color:{self.banner_color};">{html.escape(BANNER)}</pre>'
        cursor = self.output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertHtml(banner_html + "<br/>")
        cursor.insertHtml(f'<div style="color:{self.fg};">{html.escape(CREDIT_LINE)}</div><br/>')
        self.output.ensureCursorVisible()

    # ------------------ input & command handling ------------------
    def on_enter(self):
        text = self.input.text()
        if text is None:
            return
        cmdline = text.rstrip("\n")
        # If a foreground interactive child is running, forward stdin to it
        if self.foreground_proc and self.foreground_proc.state() == QtCore.QProcess.Running:
            try:
                self.foreground_proc.write((cmdline + "\n").encode("utf-8"))
                self.foreground_proc.waitForBytesWritten(100)
            except Exception as e:
                self._append_html(f"[error] foreground stdin yazılamadı: {e}\n", kind="error")
            # echo locally
            self._append_html(f"{self.username}@fsociety:$ {html.escape(cmdline)}\n")
            self.input.clear()
            return

        # No foreground -> interpret builtins or send to shell_proc
        self._append_html(f"{self.username}@fsociety:$ {html.escape(cmdline)}\n")
        self.history.append(cmdline)
        self.hist_pos = len(self.history)
        self.input.clear()

        cmd = cmdline.strip()
        if not cmd:
            return

        # builtins
        if cmd.lower() == "clear":
            self.output.clear()
            self.show_welcome()
            return

        if cmd.lower() == "help":
            self._append_html("Builtin: help clear exit sysinfo cd color color-change start run\n")
            return

        # EXIT: if foreground exists -> send exit to child; else close app
        if cmd.lower() == "exit":
            if self.foreground_proc and self.foreground_proc.state() == QtCore.QProcess.Running:
                try:
                    self.foreground_proc.write(b"exit\n")
                    self.foreground_proc.waitForBytesWritten(100)
                    self._append_html("[info] Foreground process'a 'exit' gönderildi.\n")
                except Exception as e:
                    self._append_html(f"[error] Foreground'a exit gönderilemedi: {e}\n", kind="error")
                return
            # no foreground -> close app
            QtWidgets.qApp.quit()
            return

        if cmd.lower() == "sysinfo":
            try:
                import psutil
                info = f"Platform: {platform.platform()}\nCPU count: {psutil.cpu_count(logical=True)}\nMemory: {round(psutil.virtual_memory().total/1024/1024)} MB\n"
            except Exception:
                info = f"Platform: {platform.platform()}\nCPU count: {os.cpu_count()}\n"
            self._append_html(info)
            return

        if cmd.lower().startswith("cd "):
            try:
                tgt = cmd[3:].strip()
                newdir = os.path.abspath(os.path.join(self.cwd, tgt))
                os.chdir(newdir)
                self.cwd = newdir
                # set shell proc working dir too
                try:
                    self.shell_proc.setWorkingDirectory(self.cwd)
                except Exception:
                    pass
                self._append_html(f"Klasör değiştirildi: {self.cwd}\n", kind="success")
            except Exception as e:
                self._append_html(f"Hata: {e}\n", kind="error")
            return

        if cmd.lower().startswith("color "):
            color = cmd[6:].strip()
            # allow color names or hex; user responsibility
            self.fg = color
            # apply to UI
            self.output.setStyleSheet(f"background-color: {self.bg}; color: {self.fg}; border:none; padding:6px;")
            self.prompt.setStyleSheet(f"color: {self.fg}; font-weight:bold;")
            self.input.setStyleSheet(f"background-color:#1a1a1a; color:{self.fg}; border:1px solid {self.fg}; padding:4px;")
            # save preference
            self.cfg["fg"] = self.fg
            save_config(self.cfg)
            return

        if cmd.lower() == "color-change":
            self.open_color_dialog()
            return

        if cmd.lower().startswith("start "):
            target = cmd[6:].strip()
            ok = platform_open(target)
            if ok:
                self._append_html(f"[opened] {html.escape(target)}\n", kind="success")
            else:
                self._append_html(f"[error] Açılamadı: {html.escape(target)}\n", kind="error")
            return

        if cmd.lower().startswith("run "):
            kw = cmd[4:].strip()
            self.run_script(kw, foreground=True)
            return

        # default: send to shell_proc (persistent interactive shell)
        try:
            if self.shell_proc and self.shell_proc.state() == QtCore.QProcess.Running:
                # write command + newline
                self.shell_proc.write((cmd + "\n").encode("utf-8"))
                self.shell_proc.waitForBytesWritten(100)
            else:
                # fallback: spawn short-lived process
                self._spawn_short(proc_cmd=cmd)
        except Exception as e:
            self._append_html(f"[error] Shell write hatası: {e}\n", kind="error")

    def _spawn_short(self, proc_cmd):
        """Spawn a short lived process (used as fallback)."""
        from PyQt5.QtCore import QProcess
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.readyReadStandardOutput.connect(lambda p=p: self._on_proc_output(p))
        p.finished.connect(lambda code, status, p=p: self._on_proc_finished(p, code, status))
        if platform.system().lower().startswith("win"):
            p.start("cmd", ["/c", proc_cmd])
        else:
            p.start("/bin/sh", ["-c", proc_cmd])
        self.child_procs.append(p)

    # ------------------ run script handling ------------------
    def run_script(self, keyword: str, foreground: bool = False):
        # map keywords to filenames (search flexible)
        mapping = {
            "menu": "menuScanner.py",
            "menuscan": "menuScanner.py",
            "menuscanner": "menuScanner.py",
            "console": "consoleScanner.py",
            "consolescan": "consoleScanner.py",
            "consolescanner": "consoleScanner.py",
        }
        script_file = None
        for k, v in mapping.items():
            if k in keyword.lower():
                script_file = v
                break
        if not script_file:
            script_file = keyword  # allow direct filename

        # resolve path: first check bundled app dir (for exe), then cwd
        app_dir = get_app_dir()
        candidates = [
            os.path.join(app_dir, script_file),
            os.path.join(self.cwd, script_file),
            os.path.join(os.getcwd(), script_file),
        ]
        script_path = None
        for c in candidates:
            if os.path.isfile(c):
                script_path = c
                break
        if not script_path:
            self._append_html(f"[error] Script bulunamadı: {html.escape(script_file)}\n", kind="error")
            return

        # start script as separate QProcess
        from PyQt5.QtCore import QProcess
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.readyReadStandardOutput.connect(lambda p=p: self._on_proc_output(p))
        p.finished.connect(lambda code, status, p=p: self._on_proc_finished(p, code, status))
        try:
            p.setWorkingDirectory(os.path.dirname(script_path))
        except Exception:
            pass

        # Use sys.executable so packaged exe calls embedded interpreter when available
        p.start(sys.executable, [script_path])
        started = p.waitForStarted(1000)
        if not started:
            self._append_html(f"[error] Script başlatılamadı: {html.escape(script_path)}\n", kind="error")
            return

        self.child_procs.append(p)
        if foreground:
            self.foreground_proc = p
            self._append_html(f"[running foreground] {html.escape(script_path)} (pid: {p.processId()})\n", kind="success")
        else:
            self._append_html(f"[running] {html.escape(script_path)}\n", kind="success")

    # ------------------ color / banner / highlight dialogs ------------------
    def open_color_dialog(self):
        fg = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.fg), self, "Yazı Rengi Seç")
        if not fg.isValid():
            return
        bg = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.bg), self, "Arka Plan Rengi Seç")
        if not bg.isValid():
            return
        self.fg = fg.name()
        self.bg = bg.name()
        self._apply_colors_and_save()

    def _apply_colors_and_save(self):
        self.output.setStyleSheet(f"background-color: {self.bg}; color: {self.fg}; border:none; padding:6px;")
        self.prompt.setStyleSheet(f"color: {self.fg}; font-weight:bold;")
        self.input.setStyleSheet(f"background-color:#1a1a1a; color:{self.fg}; border:1px solid {self.fg}; padding:4px;")
        # persist to config
        self.cfg["fg"] = self.fg
        self.cfg["bg"] = self.bg
        save_config(self.cfg)

    def open_banner_color_dialog(self):
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.banner_color), self, "Banner Rengi Seç")
        if not c.isValid():
            return
        self.banner_color = c.name()
        self.cfg["banner_color"] = self.banner_color
        save_config(self.cfg)
        # redraw banner at end
        cursor = self.output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        banner_html = f'<pre style="font-family:Courier, monospace; margin:0; color:{self.banner_color};">{html.escape(BANNER)}</pre>'
        cursor.insertHtml(banner_html + "<br/>")
        self.output.ensureCursorVisible()

    def open_highlight_dialog(self):
        err = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.highlights.get("error")), self, "Error rengi")
        if err.isValid():
            self.highlights["error"] = err.name()
        suc = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.highlights.get("success")), self, "Success rengi")
        if suc.isValid():
            self.highlights["success"] = suc.name()
        fso = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.highlights.get("fsociety")), self, "fsociety rengi")
        if fso.isValid():
            self.highlights["fsociety"] = fso.name()
        self.cfg["highlights"] = self.highlights
        save_config(self.cfg)

    # ------------------ history nav ------------------
    def eventFilter(self, source, event):
        if source is self.input and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Up:
                if self.history and self.hist_pos > 0:
                    self.hist_pos -= 1
                    self.input.setText(self.history[self.hist_pos])
                elif self.history and self.hist_pos == -1:
                    self.hist_pos = len(self.history) - 1
                    self.input.setText(self.history[self.hist_pos])
                return True
            elif event.key() == QtCore.Qt.Key_Down:
                if self.history and self.hist_pos < len(self.history) - 1:
                    self.hist_pos += 1
                    self.input.setText(self.history[self.hist_pos])
                else:
                    self.hist_pos = -1
                    self.input.clear()
                return True
        return super().eventFilter(source, event)

    # ------------------ cleanup ------------------
    def close(self):
        try:
            # terminate child processes
            if self.foreground_proc:
                try:
                    self.foreground_proc.terminate()
                except:
                    pass
                self.foreground_proc = None
            for p in list(self.child_procs):
                try:
                    p.terminate()
                except:
                    pass
            # shell proc
            if self.shell_proc:
                try:
                    self.shell_proc.terminate()
                except:
                    pass
                self.shell_proc = None
        except Exception:
            pass
        super().close()

# --------------------------- Main Window ---------------------------
class FsocietyTerminal(QtWidgets.QMainWindow):
    def __init__(self, username: str, cfg: dict):
        super().__init__()
        self.username = username
        self.cfg = cfg or {}
        self.setWindowTitle(f"fsociety terminal — {self.username}")
        self.resize(1200, 780)
        # theme
        theme = self.cfg.get("theme", "dark")
        if theme == "light":
            self.setStyleSheet("background-color: #f6f6f6; color: #002b22;")
        else:
            self.setStyleSheet("background-color: #0d0d0d; color: #00ff9e;")

        main = QtWidgets.QWidget()
        self.setCentralWidget(main)
        layout = QtWidgets.QHBoxLayout(main)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setStyleSheet(
            'QTabBar::tab {background:#1a1a1a;color:#00ff9e;padding:8px;}'
            'QTabBar::tab:selected{background:#00ff9e;color:#0d0d0d;font-weight:bold;}'
        )
        layout.addWidget(self.tabs, 1)

        # corner add button
        add_btn = QtWidgets.QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.setStyleSheet("background:#1a1a1a; color:#00ff9e; font-weight:bold;")
        add_btn.clicked.connect(lambda: self.add_tab(f"Terminal {self.tabs.count()+1}"))
        self.tabs.setCornerWidget(add_btn, QtCore.Qt.TopRightCorner)

        # menu
        menu = self.menuBar()
        file_menu = menu.addMenu("Dosya")
        new_tab_action = QtWidgets.QAction("Yeni Sekme", self)
        new_tab_action.triggered.connect(lambda: self.add_tab(f"Terminal {self.tabs.count()+1}"))
        file_menu.addAction(new_tab_action)
        exit_action = QtWidgets.QAction("Çıkış", self)
        exit_action.triggered.connect(QtWidgets.qApp.quit)
        file_menu.addAction(exit_action)

        view_menu = menu.addMenu("Görünüm")
        color_action = QtWidgets.QAction("Renkleri Değiştir (Sekme)", self)
        color_action.triggered.connect(self.menu_color)
        view_menu.addAction(color_action)
        banner_action = QtWidgets.QAction("Banner Rengini Değiştir (Sekme)", self)
        banner_action.triggered.connect(self.menu_banner)
        view_menu.addAction(banner_action)
        hl_action = QtWidgets.QAction("Vurgu Renklerini Değiştir (Sekme)", self)
        hl_action.triggered.connect(self.menu_highlight)
        view_menu.addAction(hl_action)
        theme_action = QtWidgets.QAction("Temayı Değiştir", self)
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)

        # first tab
        self.add_tab("Terminal 1")

    def add_tab(self, title: str):
        tab = TerminalTab(title, self.username, self.cfg)
        idx = self.tabs.addTab(tab, title)
        self.tabs.setCurrentIndex(idx)
        # randomize banner color mildly
        tab.banner_color = random.choice([DEFAULT_BANNER_COLOR, "#00ffd1", "#39ff14", "#7afcff", "#b3ff66"])

    def close_tab(self, index: int):
        if self.tabs.count() > 1:
            w = self.tabs.widget(index)
            try:
                w.close()
            except:
                pass
            self.tabs.removeTab(index)
            w.deleteLater()

    # menu handlers
    def _current_tab(self):
        return self.tabs.currentWidget()

    def menu_color(self):
        tab = self._current_tab()
        if isinstance(tab, TerminalTab):
            tab.open_color_dialog()

    def menu_banner(self):
        tab = self._current_tab()
        if isinstance(tab, TerminalTab):
            tab.open_banner_color_dialog()

    def menu_highlight(self):
        tab = self._current_tab()
        if isinstance(tab, TerminalTab):
            tab.open_highlight_dialog()

    def toggle_theme(self):
        cur = self.cfg.get("theme", "dark")
        new = "light" if cur == "dark" else "dark"
        self.cfg["theme"] = new
        save_config(self.cfg)
        if new == "light":
            self.setStyleSheet("background-color: #f6f6f6; color: #002b22;")
        else:
            self.setStyleSheet("background-color: #0d0d0d; color: #00ff9e;")

# --------------------------- Entrypoint ---------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
        app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    cfg = load_config()
    dlg = LoginDialog()
    if dlg.exec_() != QtWidgets.QDialog.Accepted:
        sys.exit(0)

    username = dlg.username.text().strip()
    # store username in cfg (already saved on first run), ensure loaded config used
    cfg = load_config()
    w = FsocietyTerminal(username, cfg)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
