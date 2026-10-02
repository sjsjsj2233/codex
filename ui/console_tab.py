"""
콘솔 탭 — SSH / Telnet / Serial  (SecureCRT / PuTTY 스타일)
"""
import re
import os
import json
import time

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QTextEdit, QComboBox,
    QFrame, QListWidget, QListWidgetItem, QCheckBox,
    QMessageBox, QApplication, QMenu, QSplitter, QSizePolicy,
    QDialog, QFileDialog, QProgressBar, QScrollArea,
)
from PyQt5.QtGui import (
    QFont, QFontDatabase, QTextCursor, QColor, QTextCharFormat,
    QPalette,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent, QTimer

from core.i18n import tr


# ── 최적 모노스페이스 폰트 ────────────────────────────────────────────────────
def _mono_font(size: int = 10) -> QFont:
    preferred = [
        'Cascadia Mono', 'Cascadia Code', 'JetBrains Mono',
        'Consolas', 'Lucida Console', 'DejaVu Sans Mono', 'Courier New',
    ]
    families = set(QFontDatabase().families())
    for name in preferred:
        if name in families:
            f = QFont(name, size)
            f.setStyleHint(QFont.Monospace)
            f.setFixedPitch(True)
            return f
    f = QFont('Courier New', size)
    f.setStyleHint(QFont.Monospace)
    f.setFixedPitch(True)
    return f


# ── ANSI 컬러 ─────────────────────────────────────────────────────────────────
# PuTTY 기본 팔레트와 동일
_FG = {
    '30': '#000000', '31': '#BB0000', '32': '#00BB00', '33': '#BBBB00',
    '34': '#0000BB', '35': '#BB00BB', '36': '#00BBBB', '37': '#BBBBBB',
    '90': '#555555', '91': '#FF5555', '92': '#55FF55', '93': '#FFFF55',
    '94': '#5555FF', '95': '#FF55FF', '96': '#55FFFF', '97': '#FFFFFF',
}
_BG = {
    '40': '#000000', '41': '#BB0000', '42': '#00BB00', '43': '#BBBB00',
    '44': '#0000BB', '45': '#BB00BB', '46': '#00BBBB', '47': '#BBBBBB',
    '100': '#555555', '101': '#FF5555', '102': '#55FF55', '103': '#FFFF55',
    '104': '#5555FF', '105': '#FF55FF', '106': '#55FFFF', '107': '#FFFFFF',
}
_ANSI_RE = re.compile(r'\x1b\[([0-9;]*)([A-Za-z])')


# ── ConsoleWorker ─────────────────────────────────────────────────────────────
class ConsoleWorker(QThread):
    data_received = pyqtSignal(str)
    connected     = pyqtSignal()
    disconnected  = pyqtSignal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params      = params
        self._running    = True
        self._send_buf   = []

    def send(self, data: str):
        self._send_buf.append(data)

    def stop(self):
        self._running = False

    def run(self):
        proto = self.params.get('protocol', 'SSH')
        try:
            {'SSH': self._ssh, 'Telnet': self._telnet, 'Serial': self._serial}[proto]()
        except Exception as e:
            self.disconnected.emit(str(e))

    def _ssh(self):
        import paramiko
        p = self.params
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(hostname=p['host'], port=int(p.get('port', 22)),
                  username=p['username'], password=p['password'],
                  timeout=15, allow_agent=False, look_for_keys=False)
        sh = c.invoke_shell(term='xterm-256color', width=220, height=50)
        sh.settimeout(0.1)
        self.connected.emit()
        while self._running:
            for d in self._send_buf[:]: sh.send(d); self._send_buf.pop(0)
            try:
                chunk = sh.recv(8192).decode('utf-8', errors='replace')
                if chunk: self.data_received.emit(chunk)
            except Exception: pass
            self.msleep(15)
        sh.close(); c.close()
        self.disconnected.emit('연결 종료')

    def _telnet(self):
        import telnetlib
        p = self.params
        tn = telnetlib.Telnet(p['host'], int(p.get('port', 23)), timeout=15)
        self.connected.emit()
        while self._running:
            for d in self._send_buf[:]: tn.write(d.encode()); self._send_buf.pop(0)
            try:
                data = tn.read_very_eager()
                if data: self.data_received.emit(data.decode('utf-8', errors='replace'))
            except Exception: pass
            self.msleep(30)
        tn.close()
        self.disconnected.emit('연결 종료')

    def _serial(self):
        import serial
        p = self.params
        ser = serial.Serial(
            port      = p['host'],
            baudrate  = int(p.get('baud_rate', 9600)),
            bytesize  = serial.EIGHTBITS,
            parity    = serial.PARITY_NONE,
            stopbits  = serial.STOPBITS_ONE,
            xonxoff   = False,
            rtscts    = False,
            dsrdtr    = False,
            timeout   = 0.05,
        )
        self.connected.emit()
        # 초기 CR 전송 — 장비 프롬프트 유도
        self.msleep(300)
        ser.write(b'\r')
        while self._running:
            for d in self._send_buf[:]:
                ser.write(d.encode('utf-8', errors='replace'))
                self._send_buf.pop(0)
            try:
                waiting = ser.in_waiting
                if waiting:
                    data = ser.read(waiting)
                    self.data_received.emit(data.decode('utf-8', errors='replace'))
            except Exception:
                pass
            self.msleep(20)
        ser.close()
        self.disconnected.emit('연결 종료')


# ── TerminalDisplay ────────────────────────────────────────────────────────────
class TerminalDisplay(QTextEdit):
    """PuTTY처럼 키 입력을 즉시 장비로 전송하는 터미널 위젯"""
    char_sent = pyqtSignal(str)

    # 키 → 이스케이프 시퀀스 맵
    _KEY_MAP = {
        Qt.Key_Up:       '\x1b[A',
        Qt.Key_Down:     '\x1b[B',
        Qt.Key_Right:    '\x1b[C',
        Qt.Key_Left:     '\x1b[D',
        Qt.Key_Home:     '\x1b[H',
        Qt.Key_End:      '\x1b[F',
        Qt.Key_PageUp:   '\x1b[5~',
        Qt.Key_PageDown: '\x1b[6~',
        Qt.Key_Delete:   '\x1b[3~',
        Qt.Key_Insert:   '\x1b[2~',
        Qt.Key_F1:  '\x1bOP', Qt.Key_F2:  '\x1bOQ',
        Qt.Key_F3:  '\x1bOR', Qt.Key_F4:  '\x1bOS',
        Qt.Key_F5:  '\x1b[15~', Qt.Key_F6:  '\x1b[17~',
        Qt.Key_F7:  '\x1b[18~', Qt.Key_F8:  '\x1b[19~',
        Qt.Key_F9:  '\x1b[20~', Qt.Key_F10: '\x1b[21~',
        Qt.Key_F11: '\x1b[23~', Qt.Key_F12: '\x1b[24~',
    }

    # 테마 프리셋
    THEMES = {
        'PuTTY Black':   ('#000000', '#BBBBBB'),
        'One Dark':      ('#282C34', '#ABB2BF'),
        'Solarized Dark':('#002B36', '#839496'),
        'Monokai':       ('#272822', '#F8F8F2'),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFont(_mono_font(10))
        self.setLineWrapMode(QTextEdit.NoWrap)
        self._theme_bg = '#000000'
        self._theme_fg = '#BBBBBB'
        self.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #BBBBBB;
                border: none;
                padding: 4px 8px;
                selection-background-color: #1D3557;
                selection-color: #FFFFFF;
            }
            QScrollBar:vertical {
                background: #111; width: 12px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #444; border-radius: 4px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #666; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal {
                background: #111; height: 12px;
            }
            QScrollBar::handle:horizontal {
                background: #444; border-radius: 4px; min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover { background: #666; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)
        # 스크롤백 버퍼 (기본 10,000줄)
        self._max_lines  = 10000
        # 세션 로깅
        self._log_file   = None
        self._log_path   = ''

    # ── 로깅 ─────────────────────────────────────────────────────────────────
    def log_raw(self, text: str):
        """수신 데이터를 로그 파일에 기록"""
        if self._log_file:
            try:
                self._log_file.write(text)
                self._log_file.flush()
            except Exception:
                pass

    def start_log(self, path: str):
        self.stop_log()
        self._log_path = path
        self._log_file = open(path, 'a', encoding='utf-8', errors='replace')

    def stop_log(self):
        if self._log_file:
            try: self._log_file.close()
            except Exception: pass
            self._log_file = None

    def is_logging(self) -> bool:
        return self._log_file is not None

    # ── 테마 ─────────────────────────────────────────────────────────────────
    def set_theme(self, bg: str, fg: str):
        self._theme_bg = bg
        self._theme_fg = fg
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                color: {fg};
                border: none;
                padding: 4px 8px;
                selection-background-color: #1D3557;
                selection-color: #FFFFFF;
            }}
            QScrollBar:vertical {{
                background: #111; width: 12px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #444; border-radius: 4px; min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #666; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: #111; height: 12px;
            }}
            QScrollBar::handle:horizontal {{
                background: #444; border-radius: 4px; min-width: 24px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: #666; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """)
        # 기본 포맷 색상도 변경
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(fg))
        self._default_fmt_fg = fg

    # ── 스크롤백 트리밍 ───────────────────────────────────────────────────────
    def trim_scrollback(self):
        if self._max_lines <= 0:
            return
        doc = self.document()
        excess = doc.blockCount() - self._max_lines
        if excess > 0:
            cur = QTextCursor(doc)
            cur.movePosition(QTextCursor.Start)
            cur.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, excess)
            cur.removeSelectedText()

    # ── 우클릭 컨텍스트 메뉴 ─────────────────────────────────────────────────
    def contextMenuEvent(self, event):
        _M_SS = """
            QMenu { background:#1E2228; color:#ABB2BF; border:1px solid #2C313A;
                    font-family:'맑은 고딕'; font-size:9pt; }
            QMenu::item { padding:7px 22px; }
            QMenu::item:selected { background:#094771; color:#FFF; }
            QMenu::item:disabled { color:#444; }
            QMenu::separator { height:1px; background:#2C313A; margin:3px 0; }
            QMenu::indicator { width:14px; height:14px; }
        """
        menu = QMenu(self)
        menu.setStyleSheet(_M_SS)

        has_sel  = self.textCursor().hasSelection()
        clip_txt = QApplication.clipboard().text()

        copy_sel = menu.addAction('⎘  선택 복사\tCtrl+C')
        copy_sel.setEnabled(has_sel)
        copy_all = menu.addAction('⎘  전체 복사')
        paste_a  = menu.addAction('⎋  붙여넣기\tCtrl+V')
        paste_a.setEnabled(bool(clip_txt))
        menu.addSeparator()

        clear_a  = menu.addAction('⌫  화면 지우기')
        menu.addSeparator()

        # 로깅
        if self.is_logging():
            log_a = menu.addAction(f'■  로깅 중지  [{self._log_path}]')
        else:
            log_a = menu.addAction('●  로그 저장 시작...')
        menu.addSeparator()

        # 스크롤백 서브메뉴
        sb_menu = menu.addMenu('📜  스크롤백 버퍼')
        sb_menu.setStyleSheet(_M_SS)
        for lines, label in [(1000,'1,000줄'), (5000,'5,000줄'),
                              (10000,'10,000줄'), (50000,'50,000줄'), (0,'무제한')]:
            a = sb_menu.addAction(('✓  ' if self._max_lines == lines else '    ') + label)
            a.setData(lines)

        act = menu.exec_(event.globalPos())
        if act is None:
            return
        if act == copy_sel:
            self.copy()
        elif act == copy_all:
            QApplication.clipboard().setText(self.toPlainText())
        elif act == paste_a:
            self.char_sent.emit(clip_txt)
        elif act == clear_a:
            self.clear()
        elif act == log_a:
            if self.is_logging():
                self.stop_log()
            else:
                from PyQt5.QtWidgets import QFileDialog
                import datetime
                default = os.path.join(
                    os.path.expanduser('~'), 'Documents',
                    f'session_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                )
                path, _ = QFileDialog.getSaveFileName(
                    self, '로그 파일 저장', default,
                    'Log Files (*.log);;Text Files (*.txt);;All Files (*)'
                )
                if path:
                    self.start_log(path)
        elif act and act.data() is not None and act.parent() is sb_menu:
            self._max_lines = act.data()

    def event(self, ev):
        """Tab 키를 Qt 포커스 이동에 빼앗기지 않도록 먼저 가로채기"""
        if ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            self.keyPressEvent(ev)
            return True
        return super().event(ev)

    def keyPressEvent(self, event):
        key  = event.key()
        mod  = event.modifiers()
        text = event.text()

        # Ctrl+C: 선택 있으면 복사, 없으면 인터럽트 전송
        if key == Qt.Key_C and mod == Qt.ControlModifier:
            if self.textCursor().hasSelection():
                self.copy()
            else:
                self.char_sent.emit('\x03')
            return

        # Ctrl+V: 클립보드 붙여넣기 → 장비로 전송
        if key == Qt.Key_V and mod == Qt.ControlModifier:
            txt = QApplication.clipboard().text()
            if txt:
                self.char_sent.emit(txt)
            return

        # Enter / Return — CR만 전송 (Cisco 콘솔 호환)
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.char_sent.emit('\r')
            return

        # Backspace — BS 전송 (장비가 \x08로 에코 처리)
        if key == Qt.Key_Backspace:
            self.char_sent.emit('\x08')
            return

        # Tab
        if key == Qt.Key_Tab:
            self.char_sent.emit('\t')
            return

        # Escape
        if key == Qt.Key_Escape:
            self.char_sent.emit('\x1b')
            return

        # 스페이스 (--More-- 페이지 넘기기)
        if key == Qt.Key_Space:
            self.char_sent.emit(' ')
            return

        # 특수키 맵
        if key in self._KEY_MAP:
            self.char_sent.emit(self._KEY_MAP[key])
            return

        # Ctrl+A~Z
        if mod == Qt.ControlModifier and text and text.upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_':
            self.char_sent.emit(chr(ord(text.upper()) - 64))
            return

        # Alt+key → ESC + key
        if mod == Qt.AltModifier and text:
            self.char_sent.emit('\x1b' + text)
            return

        # 일반 문자
        if text:
            self.char_sent.emit(text)
            return

        # 나머지 (스크롤 등)
        super().keyPressEvent(event)


# ── TerminalWidget ─────────────────────────────────────────────────────────────
class TerminalWidget(QWidget):
    status_changed = pyqtSignal(str)

    def __init__(self, params: dict, parent=None):
        super().__init__(parent)
        self.params      = params
        self.worker      = None
        self._connected  = False
        self._conn_time  = None
        self._ansi_fmt   = None
        self._setup_ui()
        self._start_timer()
        self._connect_worker()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 터미널 디스플레이 (키 입력 직접 처리)
        self._display = TerminalDisplay()
        self._display.char_sent.connect(self._send_raw)
        v.addWidget(self._display, 1)

    def _start_timer(self):
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start(1000)

    def _update_elapsed(self):
        if self._connected and self._conn_time:
            elapsed = int(time.time() - self._conn_time)
            h, r = divmod(elapsed, 3600)
            m, s = divmod(r, 60)
            host  = self.params.get('host', '')
            proto = self.params.get('protocol', 'SSH')
            port  = self.params.get('port', '')
            self.status_changed.emit(f"● {proto}  {host}:{port}    {h:02d}:{m:02d}:{s:02d}")

    # ── 연결 ─────────────────────────────────────────────────────────────────
    def _connect_worker(self):
        proto = self.params.get('protocol', 'SSH')
        host  = self.params.get('host', '')
        port  = self.params.get('port', '')
        self._sys(f'Connecting to {host}:{port} ({proto})...')
        self.worker = ConsoleWorker(self.params)
        self.worker.data_received.connect(self._on_data)
        self.worker.connected.connect(self._on_connected)
        self.worker.disconnected.connect(self._on_disconnected)
        self.worker.start()

    def _on_connected(self):
        self._connected = True
        self._conn_time = time.time()
        host  = self.params.get('host', '')
        proto = self.params.get('protocol', 'SSH')
        self._sys(f'Connected to {host} ({proto})')
        self._display.setFocus()

    def _on_disconnected(self, reason: str):
        self._connected = False
        self._sys(f'Disconnected: {reason}')
        self.status_changed.emit(f'○ Disconnected  {self.params.get("host", "")}')

    def _on_data(self, text: str):
        self._display.log_raw(text)   # 로그 파일에 기록
        self._append_ansi(text)

    # ── 입력 전송 ─────────────────────────────────────────────────────────────
    def _send_raw(self, text: str):
        if self.worker and self._connected:
            self.worker.send(text)

    # ── 터미널 출력 ───────────────────────────────────────────────────────────
    def _sys(self, msg: str):
        cur = self._display.textCursor()
        cur.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor('#555555'))
        cur.insertText(f'\r\n{msg}\r\n', fmt)
        self._display.setTextCursor(cur)
        self._display.ensureCursorVisible()

    def _insert_plain(self, text: str, cur: QTextCursor, fmt: QTextCharFormat):
        """제어문자(BS/CR)를 올바르게 처리하며 텍스트 삽입"""
        buf = ''
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '\x07':                    # BEL — 무시
                pass
            elif ch in ('\x08', '\x7f'):        # Backspace / DEL
                if buf:
                    cur.insertText(buf, fmt); buf = ''
                if not cur.atBlockStart():
                    cur.deletePreviousChar()
            elif ch == '\r':
                nxt = text[i + 1] if i + 1 < len(text) else ''
                if nxt == '\n':                  # \r\n → 줄바꿈
                    if buf:
                        cur.insertText(buf, fmt); buf = ''
                    cur.insertText('\n', fmt)
                    i += 1
                else:                            # 단독 \r → 줄 처음으로
                    if buf:
                        cur.insertText(buf, fmt); buf = ''
                    cur.movePosition(QTextCursor.StartOfLine)
            elif ch == '\n':
                buf += '\n'
            else:
                buf += ch
            i += 1
        if buf:
            cur.insertText(buf, fmt)

    def _append_ansi(self, text: str):
        cur = self._display.textCursor()
        cur.movePosition(QTextCursor.End)

        if self._ansi_fmt is None:
            self._ansi_fmt = QTextCharFormat()
            self._ansi_fmt.setForeground(QColor(self._display._theme_fg))

        fmt = QTextCharFormat(self._ansi_fmt)
        pos = 0

        for m in _ANSI_RE.finditer(text):
            plain = text[pos:m.start()]
            if plain:
                self._insert_plain(plain, cur, fmt)
            pos = m.end()

            cmd    = m.group(2)
            params = m.group(1)

            if cmd == 'm':
                codes = params.split(';') if params else ['0']
                for code in codes:
                    if code in ('0', ''):
                        fmt = QTextCharFormat()
                        fmt.setForeground(QColor(self._display._theme_fg))
                    elif code == '1':
                        fmt.setFontWeight(QFont.Bold)
                    elif code == '22':
                        fmt.setFontWeight(QFont.Normal)
                    elif code == '3':
                        fmt.setFontItalic(True)
                    elif code == '4':
                        fmt.setFontUnderline(True)
                    elif code in _FG:
                        fmt.setForeground(QColor(_FG[code]))
                    elif code in _BG:
                        fmt.setBackground(QColor(_BG[code]))
            elif cmd == 'J' and params in ('2', '3', ''):
                self._display.clear()
                self._ansi_fmt = None
                cur = self._display.textCursor()
                cur.movePosition(QTextCursor.End)

            elif cmd == 'K':
                # 줄 지우기: 0=커서→끝, 1=처음→커서, 2=줄 전체
                n = int(params) if params.isdigit() else 0
                if n == 0:
                    cur.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                    cur.removeSelectedText()
                elif n == 1:
                    cur.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
                    cur.removeSelectedText()
                elif n == 2:
                    cur.movePosition(QTextCursor.StartOfLine)
                    cur.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                    cur.removeSelectedText()

            elif cmd in ('A', 'B', 'C', 'D'):
                # 커서 이동: A=위, B=아래, C=오른쪽, D=왼쪽
                n = int(params) if params.isdigit() else 1
                _mv = {'A': QTextCursor.Up, 'B': QTextCursor.Down,
                       'C': QTextCursor.Right, 'D': QTextCursor.Left}
                cur.movePosition(_mv[cmd], QTextCursor.MoveAnchor, n)

            elif cmd == 'G':
                # 커서를 열 위치로 이동
                col = max(0, (int(params) if params.isdigit() else 1) - 1)
                cur.movePosition(QTextCursor.StartOfLine)
                cur.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, col)

        self._ansi_fmt = QTextCharFormat(fmt)
        remaining = text[pos:]
        if remaining:
            self._insert_plain(remaining, cur, fmt)

        self._display.setTextCursor(cur)
        self._display.ensureCursorVisible()
        self._display.trim_scrollback()

    # ── 공개 메서드 ───────────────────────────────────────────────────────────
    def clear_display(self):
        self._display.clear()
        self._ansi_fmt = None

    def copy_all(self):
        QApplication.clipboard().setText(self._display.toPlainText())

    def set_font_size(self, size: int):
        self._display.setFont(_mono_font(size))

    def set_theme(self, bg: str, fg: str):
        self._display.set_theme(bg, fg)
        self._ansi_fmt = None  # 다음 출력 시 테마 색상으로 재초기화

    def disconnect(self):
        self._elapsed_timer.stop()
        if self.worker:
            self.worker.stop()
            self.worker.wait(2000)


# ── ConsoleTab ────────────────────────────────────────────────────────────────
class ConsoleTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions_file = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'NetworkAutomation', 'sessions.json'
        )
        self._saved_sessions = self._load_sessions()
        self._font_size = 10
        self._current_theme = ('#000000', '#BBBBBB')  # PuTTY Black
        self._setup_ui()

    # ─────────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 메인 영역 (사이드바 + 터미널)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet('QSplitter::handle{background:#2A2A2A;}')
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_terminal_area())
        splitter.setSizes([210, 9999])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        v.addWidget(splitter, 1)

        # 하단 상태바 (SecureCRT 스타일)
        v.addWidget(self._build_statusbar())

    # ── 사이드바 ──────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        w = QWidget()
        w.setFixedWidth(210)
        w.setStyleSheet('background:#1E2228;')
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 헤더
        hdr = QLabel('  Sessions')
        hdr.setFixedHeight(30)
        hdr.setAlignment(Qt.AlignVCenter)
        hdr.setFont(QFont('맑은 고딕', 8, QFont.Bold))
        hdr.setStyleSheet(
            'background:#252B36;color:#ABB2BF;'
            'letter-spacing:1px;border-bottom:1px solid #111;padding-left:8px'
        )
        v.addWidget(hdr)

        # 세션 목록
        self._sess_list = QListWidget()
        self._sess_list.setFont(QFont('맑은 고딕', 9))
        self._sess_list.setStyleSheet("""
            QListWidget {
                background:#1E2228; color:#ABB2BF;
                border:none; outline:none;
            }
            QListWidget::item {
                padding:7px 10px;
                border-bottom:1px solid #252B36;
            }
            QListWidget::item:selected {
                background:#2C313A; color:#61AFEF;
            }
            QListWidget::item:hover { background:#252B36; }
        """)
        self._sess_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._sess_list.customContextMenuRequested.connect(self._ctx_menu)
        self._sess_list.itemDoubleClicked.connect(self._open_saved)
        self._refresh_sess()
        v.addWidget(self._sess_list, 1)

        # Quick Connect 헤더
        qhdr = QLabel('  Quick Connect')
        qhdr.setFixedHeight(28)
        qhdr.setAlignment(Qt.AlignVCenter)
        qhdr.setFont(QFont('맑은 고딕', 8, QFont.Bold))
        qhdr.setStyleSheet(
            'background:#252B36;color:#ABB2BF;'
            'letter-spacing:1px;border-top:1px solid #111;'
            'border-bottom:1px solid #111;padding-left:8px'
        )
        v.addWidget(qhdr)

        # 폼
        form = QWidget()
        form.setStyleSheet('background:#1E2228;')
        fv = QVBoxLayout(form)
        fv.setContentsMargins(8, 8, 8, 10)
        fv.setSpacing(4)

        _L = 'color:#5C6370;font-size:8pt;background:transparent;'
        _I = ('QLineEdit{background:#252B36;color:#ABB2BF;'
              'border:1px solid #2C313A;border-radius:2px;'
              'padding:4px 6px;font-size:9pt}'
              'QLineEdit:focus{border-color:#61AFEF;color:#E5C07B}')
        _C = ('QComboBox{background:#252B36;color:#ABB2BF;'
              'border:1px solid #2C313A;border-radius:2px;'
              'padding:4px 6px;font-size:9pt}'
              'QComboBox::drop-down{border:none;width:18px}'
              'QComboBox QAbstractItemView{background:#252B36;color:#ABB2BF;'
              'selection-background-color:#2C313A;border:1px solid #444}')

        fv.addWidget(self._fl('Protocol', _L))
        self._proto = QComboBox()
        self._proto.addItems(['SSH', 'Telnet', 'Serial'])
        self._proto.setStyleSheet(_C)
        self._proto.currentTextChanged.connect(self._proto_changed)
        fv.addWidget(self._proto)

        # Host (SSH/Telnet)
        self._host_lbl = self._fl('Host / IP', _L)
        fv.addWidget(self._host_lbl)
        self._host = QLineEdit()
        self._host.setPlaceholderText('192.168.1.1')
        self._host.setStyleSheet(_I)
        fv.addWidget(self._host)

        # COM Port 콤보 (Serial 전용 — 평소엔 숨김)
        self._com_lbl = self._fl('COM Port', _L)
        fv.addWidget(self._com_lbl)
        com_row = QHBoxLayout()
        com_row.setSpacing(4)
        self._com_combo = QComboBox()
        self._com_combo.setStyleSheet(_C)
        com_row.addWidget(self._com_combo, 1)
        self._com_refresh = QPushButton('↺')
        self._com_refresh.setFixedSize(28, 26)
        self._com_refresh.setToolTip('COM 포트 새로고침')
        self._com_refresh.setStyleSheet(
            'QPushButton{background:#252B36;color:#ABB2BF;border:1px solid #2C313A;'
            'border-radius:2px;font-size:10pt}'
            'QPushButton:hover{background:#2C313A;color:#61AFEF}'
        )
        self._com_refresh.clicked.connect(self._refresh_com_ports)
        com_row.addWidget(self._com_refresh)
        self._com_row_widget = QWidget()
        self._com_row_widget.setStyleSheet('background:transparent')
        self._com_row_widget.setLayout(com_row)
        fv.addWidget(self._com_row_widget)
        self._com_lbl.hide()
        self._com_row_widget.hide()

        self._port_lbl = self._fl('Port', _L)
        fv.addWidget(self._port_lbl)
        self._port = QLineEdit('22')
        self._port.setStyleSheet(_I)
        fv.addWidget(self._port)

        # Baud Rate 콤보 (Serial 전용 — 평소엔 숨김)
        self._baud_lbl = self._fl('Baud Rate', _L)
        fv.addWidget(self._baud_lbl)
        self._baud_combo = QComboBox()
        self._baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self._baud_combo.setStyleSheet(_C)
        fv.addWidget(self._baud_combo)
        self._baud_lbl.hide()
        self._baud_combo.hide()

        self._user_lbl = self._fl('Username', _L)
        fv.addWidget(self._user_lbl)
        self._user = QLineEdit()
        self._user.setPlaceholderText('admin')
        self._user.setStyleSheet(_I)
        fv.addWidget(self._user)

        fv.addWidget(self._fl('Password', _L))
        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.Password)
        self._pw.setStyleSheet(_I)
        self._pw.returnPressed.connect(self._quick_connect)
        fv.addWidget(self._pw)

        self._save_chk = QCheckBox('세션 저장')
        self._save_chk.setStyleSheet('color:#5C6370;font-size:8pt;background:transparent;')
        fv.addWidget(self._save_chk)
        self._sess_name = QLineEdit()
        self._sess_name.setPlaceholderText('세션 이름')
        self._sess_name.setStyleSheet(_I)
        fv.addWidget(self._sess_name)

        conn_btn = QPushButton('Connect')
        conn_btn.setFixedHeight(30)
        conn_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        conn_btn.setStyleSheet("""
            QPushButton {
                background:#3D8B3D; color:#FFFFFF;
                border:none; border-radius:2px; letter-spacing:0.5px;
            }
            QPushButton:hover   { background:#4CAF4C; }
            QPushButton:pressed { background:#2E6B2E; }
        """)
        conn_btn.clicked.connect(self._quick_connect)
        fv.addWidget(conn_btn)

        v.addWidget(form)
        return w

    # ── 터미널 영역 ───────────────────────────────────────────────────────────
    def _build_terminal_area(self):
        w = QWidget()
        w.setStyleSheet('background:#000000;')
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── 툴바 ─────────────────────────────────────────────────────────────
        tb = QWidget()
        tb.setFixedHeight(34)
        tb.setStyleSheet('background:#252B36;border-bottom:1px solid #111;')
        tbh = QHBoxLayout(tb)
        tbh.setContentsMargins(8, 0, 8, 0)
        tbh.setSpacing(4)

        _BTN = ('QPushButton{{background:#1E2228;color:{c};border:1px solid #2C313A;'
                'border-radius:2px;font-size:8pt;padding:0 10px;font-family:"맑은 고딕"}}'
                'QPushButton:hover{{background:#2C313A;border-color:#61AFEF}}'
                'QPushButton:pressed{{background:#094771}}')

        for label, attr, slot, color in [
            ('✕ Disconnect', '_btn_disc',     '_disconnect_cur',  '#FF5F5F'),
            ('↺ Reconnect',  '_btn_reconn',   '_reconnect_cur',   '#4EC9B0'),
            ('＋ New Tab',   '_btn_new',      '_focus_host',      '#9CDCFE'),
            ('⌫ Clear',      '_btn_clear',    '_clear_cur',       '#ABB2BF'),
            ('⎘ Copy All',   '_btn_copy',     '_copy_cur',        '#CE9178'),
            ('● Log',        '_btn_log',      '_toggle_log_cur',  '#E5C07B'),
            ('🔍 점검',      '_btn_inspect',  '_open_inspection', '#C678DD'),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setStyleSheet(_BTN.format(c=color))
            btn.clicked.connect(getattr(self, slot))
            setattr(self, attr, btn)
            tbh.addWidget(btn)

        tbh.addStretch()
        self._status_lbl = QLabel('Not connected')
        self._status_lbl.setFont(QFont('맑은 고딕', 8))
        self._status_lbl.setStyleSheet('color:#5C6370;background:transparent;')
        tbh.addWidget(self._status_lbl)

        # 로그 상태 표시
        self._log_indicator = QLabel('')
        self._log_indicator.setFont(QFont('맑은 고딕', 8))
        self._log_indicator.setStyleSheet('color:#E5C07B;background:transparent;')
        tbh.addWidget(self._log_indicator)

        v.addWidget(tb)

        # 탭 위젯 (SecureCRT 스타일)
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #000000;
            }
            QTabBar {
                background: #1E2228;
            }
            QTabBar::tab {
                background: #1E2228;
                color: #5C6370;
                padding: 7px 20px 7px 14px;
                border: none;
                border-right: 1px solid #111;
                font-size: 9pt;
                font-family: '맑은 고딕';
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: #000000;
                color: #ABB2BF;
                border-top: 2px solid #61AFEF;
            }
            QTabBar::tab:hover:!selected {
                background: #252B36;
                color: #ABB2BF;
            }
            QTabBar::close-button {
                subcontrol-position: right;
            }
        """)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._tab_changed)
        v.addWidget(self._tabs, 1)

        # 빈 화면
        self._empty = QWidget()
        self._empty.setStyleSheet('background:#000000;')
        ev = QVBoxLayout(self._empty)
        ev.setAlignment(Qt.AlignCenter)
        em_lbl = QLabel(
            'No active sessions\n\n'
            'Use Quick Connect on the left\n'
            'or double-click a saved session'
        )
        em_lbl.setFont(_mono_font(10))
        em_lbl.setAlignment(Qt.AlignCenter)
        em_lbl.setStyleSheet('color:#2C313A;')
        ev.addWidget(em_lbl)
        v.addWidget(self._empty)

        self._sync_empty()
        return w

    # ── 하단 상태바 ───────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = QWidget()
        bar.setFixedHeight(22)
        bar.setStyleSheet('background:#1E2228;border-top:1px solid #111;')
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(16)

        # 스크롤백 표시
        self._sb_lbl = QLabel('Scrollback: 10,000')
        self._sb_lbl.setFont(QFont('맑은 고딕', 8))
        self._sb_lbl.setStyleSheet('color:#5C6370;background:transparent;')
        h.addWidget(self._sb_lbl)
        h.addStretch()

        # 테마 선택
        _C_SS = ('QComboBox{background:#252B36;color:#5C6370;border:1px solid #2C313A;'
                 'border-radius:2px;font-size:7pt;padding:1px 4px;min-width:90px}'
                 'QComboBox:hover{color:#ABB2BF;border-color:#5C6370}'
                 'QComboBox::drop-down{border:none;width:14px}'
                 'QComboBox QAbstractItemView{background:#252B36;color:#ABB2BF;'
                 'selection-background-color:#2C313A;border:1px solid #444}')
        self._theme_combo = QComboBox()
        self._theme_combo.setFixedHeight(18)
        self._theme_combo.setStyleSheet(_C_SS)
        for name in TerminalDisplay.THEMES:
            self._theme_combo.addItem(name)
        self._theme_combo.setCurrentText('PuTTY Black')
        self._theme_combo.currentTextChanged.connect(self._apply_theme)
        h.addWidget(self._theme_combo)

        # 폰트 크기 조절
        _fs_ss = ('QPushButton{background:#252B36;color:#5C6370;border:none;'
                  'border-radius:2px;font-size:8pt;padding:0 4px}'
                  'QPushButton:hover{color:#ABB2BF}')
        for symbol, delta in [('A−', -1), ('A+', +1)]:
            btn = QPushButton(symbol)
            btn.setFixedHeight(18)
            btn.setFont(QFont('맑은 고딕', 7))
            btn.setStyleSheet(_fs_ss)
            d = delta
            btn.clicked.connect(lambda _, d=d: self._change_font_size(d))
            h.addWidget(btn)

        return bar

    # ── 헬퍼 ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _fl(text, style):
        l = QLabel(text)
        l.setFont(QFont('맑은 고딕', 8))
        l.setStyleSheet(style)
        return l

    def _proto_changed(self, proto):
        serial = proto == 'Serial'
        # Host / COM 전환
        self._host_lbl.setVisible(not serial)
        self._host.setVisible(not serial)
        self._com_lbl.setVisible(serial)
        self._com_row_widget.setVisible(serial)
        # Port / Baud 전환
        self._port_lbl.setVisible(not serial)
        self._port.setVisible(not serial)
        self._baud_lbl.setVisible(serial)
        self._baud_combo.setVisible(serial)
        # Username/Password 숨김
        self._user_lbl.setVisible(not serial)
        self._user.setVisible(not serial)
        # 포트 기본값
        if not serial:
            self._port.setText('23' if proto == 'Telnet' else '22')
        # Serial 선택 시 COM 포트 자동 스캔
        if serial:
            self._refresh_com_ports()

    def _refresh_com_ports(self):
        self._com_combo.clear()
        try:
            from serial.tools import list_ports
            ports = list_ports.comports()
            if ports:
                for p in sorted(ports, key=lambda x: x.device):
                    desc = p.description or p.device
                    self._com_combo.addItem(f"{p.device}  —  {desc}", p.device)
            else:
                self._com_combo.addItem('(감지된 COM 포트 없음)', '')
        except Exception:
            self._com_combo.addItem('(pyserial 오류)', '')

    def _quick_connect(self):
        proto = self._proto.currentText()
        user  = self._user.text().strip()
        pw    = self._pw.text()

        if proto == 'Serial':
            host = self._com_combo.currentData() or self._com_combo.currentText().split()[0]
            baud = self._baud_combo.currentText()
            port = baud
            if not host or host.startswith('('):
                QMessageBox.warning(self, 'Connect', '연결할 COM 포트를 선택하세요.')
                return
        else:
            host = self._host.text().strip()
            port = self._port.text().strip()
            baud = '9600'
            if not host:
                QMessageBox.warning(self, 'Connect', 'Host / IP를 입력하세요.')
                return
            if not user:
                QMessageBox.warning(self, 'Connect', '사용자 이름을 입력하세요.')
                return

        params = {'protocol': proto, 'host': host, 'port': port,
                  'username': user, 'password': pw, 'baud_rate': baud}

        if self._save_chk.isChecked():
            name = self._sess_name.text().strip() or host
            self._persist(name, params)

        self._open_session(params)

    def _open_session(self, params: dict):
        proto = params.get('protocol', 'SSH')
        host  = params.get('host', '')
        icons = {'SSH': '🔐', 'Telnet': '🔌', 'Serial': '🔗'}
        label = f"{icons.get(proto, '')} {host}"

        term = TerminalWidget(params)
        term.set_font_size(self._font_size)
        # 현재 테마 적용
        if hasattr(self, '_current_theme'):
            term.set_theme(*self._current_theme)
        term.status_changed.connect(self._on_status)
        idx = self._tabs.addTab(term, label)
        self._tabs.setCurrentIndex(idx)
        self._sync_empty()

    def _open_saved(self, item: QListWidgetItem):
        d = item.data(Qt.UserRole)
        if d:
            self._open_session(dict(d))

    def _close_tab(self, idx: int):
        w = self._tabs.widget(idx)
        if isinstance(w, TerminalWidget):
            w.disconnect()
        self._tabs.removeTab(idx)
        self._sync_empty()
        if self._tabs.count() == 0:
            self._status_lbl.setText('Not connected')
            self._log_indicator.setText('')

    def _tab_changed(self, idx: int):
        w = self._tabs.widget(idx)
        if isinstance(w, TerminalWidget) and w._connected:
            host  = w.params.get('host', '')
            proto = w.params.get('protocol', 'SSH')
            self._status_lbl.setText(f'● {proto}  {host}')

    def _on_status(self, msg: str):
        self._status_lbl.setText(msg)

    def _sync_empty(self):
        has = self._tabs.count() > 0
        self._tabs.setVisible(has)
        self._empty.setVisible(not has)

    def _change_font_size(self, delta: int):
        self._font_size = max(7, min(20, self._font_size + delta))
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, TerminalWidget):
                w.set_font_size(self._font_size)

    def _apply_theme(self, name: str):
        bg, fg = TerminalDisplay.THEMES.get(name, ('#000000', '#BBBBBB'))
        self._current_theme = (bg, fg)
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, TerminalWidget):
                w.set_theme(bg, fg)

    def _cur_term(self):
        w = self._tabs.currentWidget()
        return w if isinstance(w, TerminalWidget) else None

    def _disconnect_cur(self):
        w = self._cur_term()
        if w: w.disconnect()

    def _reconnect_cur(self):
        idx = self._tabs.currentIndex()
        w = self._cur_term()
        if not w: return
        params = dict(w.params)
        w.disconnect()
        self._tabs.removeTab(idx)
        self._open_session(params)

    def _focus_host(self):
        self._host.setFocus(); self._host.selectAll()

    def _clear_cur(self):
        w = self._cur_term()
        if w: w.clear_display()

    def _copy_cur(self):
        w = self._cur_term()
        if w: w.copy_all()

    def _toggle_log_cur(self):
        w = self._cur_term()
        if not w: return
        disp = w._display
        if disp.is_logging():
            disp.stop_log()
            self._btn_log.setText('● Log')
            self._log_indicator.setText('')
        else:
            from PyQt5.QtWidgets import QFileDialog
            import datetime
            default = os.path.join(
                os.path.expanduser('~'), 'Documents',
                f'session_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            path, _ = QFileDialog.getSaveFileName(
                self, '로그 파일 저장', default,
                'Log Files (*.log);;Text Files (*.txt);;All Files (*)'
            )
            if path:
                disp.start_log(path)
                self._btn_log.setText('■ Stop Log')
                self._log_indicator.setText(f'● REC  {os.path.basename(path)}')

    # ── 세션 저장 ─────────────────────────────────────────────────────────────
    def _load_sessions(self) -> list:
        try:
            if os.path.exists(self._sessions_file):
                with open(self._sessions_file, encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_file(self):
        try:
            os.makedirs(os.path.dirname(self._sessions_file), exist_ok=True)
            with open(self._sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self._saved_sessions, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _persist(self, name: str, params: dict):
        self._saved_sessions = [s for s in self._saved_sessions if s.get('name') != name]
        self._saved_sessions.insert(0, {'name': name, **params})
        self._save_file()
        self._refresh_sess()

    def _refresh_sess(self):
        self._sess_list.clear()
        icons = {'SSH': '🔐', 'Telnet': '🔌', 'Serial': '🔗'}
        for s in self._saved_sessions:
            icon = icons.get(s.get('protocol', 'SSH'), '🖥')
            item = QListWidgetItem(f"  {icon}  {s['name']}")
            item.setData(Qt.UserRole, s)
            self._sess_list.addItem(item)

    def _ctx_menu(self, pos):
        item = self._sess_list.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        menu.setFont(QFont('맑은 고딕', 9))
        menu.setStyleSheet("""
            QMenu { background:#252B36; color:#ABB2BF; border:1px solid #2C313A; }
            QMenu::item { padding:6px 20px; }
            QMenu::item:selected { background:#2C313A; color:#61AFEF; }
        """)
        open_a = menu.addAction('🔗   Connect')
        del_a  = menu.addAction('🗑   Delete')
        act = menu.exec_(self._sess_list.mapToGlobal(pos))
        if act == open_a:
            self._open_saved(item)
        elif act == del_a:
            d = item.data(Qt.UserRole)
            self._saved_sessions = [s for s in self._saved_sessions if s.get('name') != d.get('name')]
            self._save_file()
            self._refresh_sess()

    def _open_inspection(self):
        w = self._cur_term()
        params = dict(w.params) if w else {}
        dlg = DeviceInspectionDialog(params, self)
        dlg.exec_()


# ── 장비 종합 점검 Worker ────────────────────────────────────────────────────
_INSPECT_CMDS = [
    ('terminal length 0',          '페이지 해제'),
    ('show version',               '버전 정보'),
    ('show running-config',        '실행 설정'),
    ('show interfaces status',     '인터페이스 상태'),
    ('show ip interface brief',    'IP 인터페이스'),
    ('show environment all',       '환경 센서'),
    ('show processes cpu',         'CPU 프로세스'),
    ('show processes cpu history', 'CPU 히스토리'),
    ('show processes memory sorted','메모리 프로세스'),
    ('show memory statistics',     '메모리 통계'),
    ('show logging',               '시스템 로그'),
]

_PROMPT_RE = re.compile(r'[A-Za-z0-9\-_()./]+[#>]\s*$')


class DeviceInspectionWorker(QThread):
    progress   = pyqtSignal(str)
    cmd_result = pyqtSignal(str, str)
    finished   = pyqtSignal(dict)
    error      = pyqtSignal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params   = params
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            if self.params.get('protocol') == 'Serial':
                self._serial_inspect()
            else:
                self._ssh_inspect()
        except Exception as e:
            self.error.emit(str(e))

    # ── SSH 점검 ──────────────────────────────────────────────────────────────
    def _ssh_inspect(self):
        import paramiko
        p = self.params
        self.progress.emit('🔌  SSH 접속 중...')
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(
            hostname=p['host'], port=int(p.get('port', 22)),
            username=p['username'], password=p['password'],
            timeout=15, allow_agent=False, look_for_keys=False,
        )
        sh = c.invoke_shell(term='vt100', width=200, height=50)
        sh.settimeout(0.2)
        self.progress.emit('✅  접속 완료. 초기화 중...')
        time.sleep(1.0)
        self._ssh_drain(sh)

        results = self._run_cmds_ssh(sh)
        sh.close(); c.close()
        self.progress.emit('✅  점검 완료!')
        self.finished.emit(results)

    def _run_cmds_ssh(self, sh) -> dict:
        results = {}
        for cmd, desc in _INSPECT_CMDS:
            if not self._running:
                break
            self.progress.emit(f'▶  {desc}  ({cmd})')
            sh.send(cmd + '\r')
            out   = self._ssh_recv_prompt(sh)
            clean = self._strip_cmd_echo(out, cmd)
            results[cmd] = clean
            self.cmd_result.emit(cmd, clean)
        return results

    def _ssh_drain(self, sh):
        try:
            while True: sh.recv(4096)
        except Exception:
            pass

    def _ssh_recv_prompt(self, sh, timeout: float = 30.0) -> str:
        buf = ''
        t0  = time.time()
        while self._running and (time.time() - t0) < timeout:
            try:
                chunk = sh.recv(4096).decode('utf-8', errors='replace')
                buf  += chunk
                clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', buf)
                clean = re.sub(r'\x1b\][^\x07]*\x07', '', clean)
                clean = clean.replace('\r', '')
                if _PROMPT_RE.search(clean.strip()):
                    return clean
            except Exception:
                time.sleep(0.05)
        return buf

    # ── Serial 점검 ───────────────────────────────────────────────────────────
    def _serial_inspect(self):
        import serial as _serial
        p    = self.params
        com  = p.get('com_port', '')
        baud = int(p.get('baud_rate', 9600))

        self.progress.emit(f'🔌  시리얼 접속 중...  ({com} / {baud}bps)')
        ser = _serial.Serial(
            port=com, baudrate=baud,
            bytesize=8, parity='N', stopbits=1,
            timeout=0.1, xonxoff=False, rtscts=False, dsrdtr=False,
        )
        self.progress.emit('✅  포트 열림. 로그인 대기 중...')

        # 장비 깨우기
        ser.write(b'\r')
        time.sleep(0.8)

        buf = self._serial_recv_until(ser,
            [r'[Uu]sername\s*:', r'[Ll]ogin\s*:', r'[Pp]assword\s*:', r'[#>]\s*$'],
            timeout=12)

        # Username 프롬프트
        if re.search(r'[Uu]sername\s*:|[Ll]ogin\s*:', buf):
            self.progress.emit('📝  Username 입력 중...')
            ser.write((p.get('username', '') + '\r').encode())
            buf = self._serial_recv_until(ser,
                [r'[Pp]assword\s*:', r'[#>]\s*$'], timeout=10)

        # Password 프롬프트
        if re.search(r'[Pp]assword\s*:', buf):
            self.progress.emit('🔑  Password 입력 중...')
            ser.write((p.get('password', '') + '\r').encode())
            buf = self._serial_recv_until(ser, [r'[#>]\s*$'], timeout=15)

        # 프롬프트 확인
        clean_buf = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', buf).replace('\r', '')
        if not _PROMPT_RE.search(clean_buf.strip()):
            ser.close()
            self.error.emit('로그인 실패 — 장비 프롬프트를 찾을 수 없습니다.\n'
                            '계정 정보 또는 COM 포트를 확인하세요.')
            return

        self.progress.emit('✅  로그인 완료!')
        results = self._run_cmds_serial(ser)
        ser.close()
        self.progress.emit('✅  점검 완료!')
        self.finished.emit(results)

    def _run_cmds_serial(self, ser) -> dict:
        results = {}
        for cmd, desc in _INSPECT_CMDS:
            if not self._running:
                break
            self.progress.emit(f'▶  {desc}  ({cmd})')
            ser.write((cmd + '\r').encode())
            out   = self._serial_recv_until(ser, [r'[#>]\s*$'], timeout=45)
            clean = self._strip_cmd_echo(
                re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', out)
                  .replace('\r\n', '\n').replace('\r', '\n'),
                cmd
            )
            results[cmd] = clean
            self.cmd_result.emit(cmd, clean)
        return results

    def _serial_recv_until(self, ser, patterns, timeout: float = 30.0) -> str:
        buf      = ''
        t0       = time.time()
        compiled = [re.compile(p) for p in patterns]
        while self._running and (time.time() - t0) < timeout:
            waiting = ser.in_waiting
            if waiting:
                chunk = ser.read(waiting).decode('utf-8', errors='replace')
                buf  += chunk
                clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', buf).replace('\r', '')
                for pat in compiled:
                    if pat.search(clean):
                        return clean
            else:
                time.sleep(0.05)
        return buf

    # ── 공통 ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _strip_cmd_echo(text: str, cmd: str) -> str:
        lines = text.splitlines()
        if lines and cmd.strip() in lines[0]:
            lines = lines[1:]
        return '\n'.join(lines).strip()


# ── 장비 종합 점검 Dialog ────────────────────────────────────────────────────
class DeviceInspectionDialog(QDialog):
    def __init__(self, params: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle('장비 종합 점검')
        self.resize(900, 640)
        self.setModal(True)
        self._params  = params
        self._results = {}
        self._worker  = None
        self._setup_ui()
        self._prefill(params)

    def _setup_ui(self):
        self.setStyleSheet('background:#1E2228;color:#ABB2BF;font-family:"맑은 고딕";')
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(10)

        _I = ('QLineEdit{background:#252B36;color:#E5C07B;border:1px solid #2C313A;'
              'border-radius:2px;padding:4px 8px;font-size:9pt}'
              'QLineEdit:focus{border-color:#61AFEF}')
        _C = ('QComboBox{background:#252B36;color:#E5C07B;border:1px solid #2C313A;'
              'border-radius:2px;padding:3px 6px;font-size:9pt}'
              'QComboBox::drop-down{border:none;width:16px}'
              'QComboBox QAbstractItemView{background:#252B36;color:#ABB2BF;'
              'selection-background-color:#2C313A;border:1px solid #444}')

        # ── 접속 정보 행 ────────────────────────────────────────────────────
        info_row = QHBoxLayout()
        info_row.setSpacing(8)

        # Protocol 콤보
        info_row.addWidget(self._lbl('Protocol'))
        self._e_proto = QComboBox()
        self._e_proto.addItems(['SSH', 'Telnet', 'Serial'])
        self._e_proto.setFixedWidth(80)
        self._e_proto.setStyleSheet(_C)
        self._e_proto.currentTextChanged.connect(self._proto_changed)
        info_row.addWidget(self._e_proto)

        # SSH/Telnet 전용
        self._lbl_host = self._lbl('Host')
        info_row.addWidget(self._lbl_host)
        self._e_host = QLineEdit(); self._e_host.setPlaceholderText('192.168.1.1')
        self._e_host.setFixedWidth(150); self._e_host.setStyleSheet(_I)
        info_row.addWidget(self._e_host)

        self._lbl_port = self._lbl('Port')
        info_row.addWidget(self._lbl_port)
        self._e_port = QLineEdit('22'); self._e_port.setFixedWidth(48)
        self._e_port.setStyleSheet(_I)
        info_row.addWidget(self._e_port)

        # Serial 전용 — 초기엔 숨김
        self._lbl_com = self._lbl('COM Port')
        info_row.addWidget(self._lbl_com)
        self._e_com = QComboBox(); self._e_com.setFixedWidth(160)
        self._e_com.setStyleSheet(_C)
        info_row.addWidget(self._e_com)

        self._lbl_baud = self._lbl('Baud')
        info_row.addWidget(self._lbl_baud)
        self._e_baud = QComboBox()
        self._e_baud.addItems(['9600', '19200', '38400', '57600', '115200'])
        self._e_baud.setFixedWidth(80); self._e_baud.setStyleSheet(_C)
        info_row.addWidget(self._e_baud)

        self._lbl_com.hide(); self._e_com.hide()
        self._lbl_baud.hide(); self._e_baud.hide()

        # User / Pass (공통)
        for lbl, attr, ph, w, echo in [
            ('User', '_e_user', 'admin', 100, False),
            ('Pass', '_e_pass', '',      100, True),
        ]:
            info_row.addWidget(self._lbl(lbl))
            e = QLineEdit(); e.setPlaceholderText(ph)
            e.setFixedWidth(w); e.setStyleSheet(_I)
            if echo: e.setEchoMode(QLineEdit.Password)
            setattr(self, attr, e)
            info_row.addWidget(e)

        info_row.addStretch()

        _BTN = ('QPushButton{background:%s;color:#fff;border:none;'
                'border-radius:3px;padding:5px 18px;font-size:9pt;font-weight:bold}'
                'QPushButton:hover{opacity:0.85}'
                'QPushButton:disabled{background:#2C313A;color:#5C6370}')
        self._btn_start = QPushButton('▶  점검 시작')
        self._btn_start.setStyleSheet(_BTN % '#3D8B3D')
        self._btn_start.clicked.connect(self._start)
        info_row.addWidget(self._btn_start)

        self._btn_save = QPushButton('💾  보고서 저장')
        self._btn_save.setStyleSheet(_BTN % '#0e639c')
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._save_report)
        info_row.addWidget(self._btn_save)

        root.addLayout(info_row)

        # ── 진행 바 ──────────────────────────────────────────────────────────
        self._prog = QProgressBar()
        self._prog.setRange(0, len(_INSPECT_CMDS))
        self._prog.setValue(0)
        self._prog.setFixedHeight(6)
        self._prog.setTextVisible(False)
        self._prog.setStyleSheet(
            'QProgressBar{background:#252B36;border:none;border-radius:3px}'
            'QProgressBar::chunk{background:#61AFEF;border-radius:3px}'
        )
        root.addWidget(self._prog)

        # ── 본문 (왼쪽: 진행로그 / 오른쪽: 출력) ────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet('QSplitter::handle{background:#111}')

        # 진행 로그
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(_mono_font(9))
        self._log.setStyleSheet(
            'QTextEdit{background:#141414;color:#98C379;border:none;padding:6px}'
        )
        self._log.setFixedWidth(260)
        splitter.addWidget(self._log)

        # 출력
        self._out = QTextEdit()
        self._out.setReadOnly(True)
        self._out.setFont(_mono_font(9))
        self._out.setStyleSheet(
            'QTextEdit{background:#0D1117;color:#ABB2BF;border:none;padding:8px}'
        )
        splitter.addWidget(self._out)
        splitter.setSizes([260, 9999])
        root.addWidget(splitter, 1)

        # 상태 레이블
        self._status = QLabel('접속 정보를 입력 후 점검을 시작하세요.')
        self._status.setFont(QFont('맑은 고딕', 8))
        self._status.setStyleSheet('color:#5C6370;background:transparent')
        root.addWidget(self._status)

    @staticmethod
    def _lbl(text):
        l = QLabel(text)
        l.setFont(QFont('맑은 고딕', 8))
        l.setStyleSheet('color:#5C6370;background:transparent')
        return l

    def _proto_changed(self, proto: str):
        serial = proto == 'Serial'
        self._lbl_host.setVisible(not serial); self._e_host.setVisible(not serial)
        self._lbl_port.setVisible(not serial); self._e_port.setVisible(not serial)
        self._lbl_com.setVisible(serial);      self._e_com.setVisible(serial)
        self._lbl_baud.setVisible(serial);     self._e_baud.setVisible(serial)
        if serial:
            self._refresh_com_ports()
        else:
            self._e_port.setText('23' if proto == 'Telnet' else '22')

    def _refresh_com_ports(self):
        self._e_com.clear()
        try:
            from serial.tools import list_ports
            ports = list_ports.comports()
            if ports:
                for p in sorted(ports, key=lambda x: x.device):
                    self._e_com.addItem(f"{p.device}  —  {p.description or p.device}", p.device)
            else:
                self._e_com.addItem('(감지된 COM 포트 없음)', '')
        except Exception:
            self._e_com.addItem('(pyserial 오류)', '')

    def _prefill(self, p: dict):
        proto = p.get('protocol', 'SSH')
        self._e_proto.setCurrentText(proto)
        self._e_user.setText(p.get('username', ''))
        self._e_pass.setText(p.get('password', ''))
        if proto == 'Serial':
            # COM 목록 로드 후 저장된 포트 선택
            self._refresh_com_ports()
            com = p.get('host', '')  # Serial은 host 필드에 COM 포트 저장됨
            for i in range(self._e_com.count()):
                if self._e_com.itemData(i) == com:
                    self._e_com.setCurrentIndex(i)
                    break
            baud = p.get('baud_rate', '9600')
            idx = self._e_baud.findText(str(baud))
            if idx >= 0: self._e_baud.setCurrentIndex(idx)
        else:
            self._e_host.setText(p.get('host', ''))
            self._e_port.setText(str(p.get('port', '22')))

    def _start(self):
        proto = self._e_proto.currentText()
        user  = self._e_user.text().strip()
        pw    = self._e_pass.text()

        if proto == 'Serial':
            com = self._e_com.currentData() or self._e_com.currentText().split()[0]
            if not com or com.startswith('('):
                QMessageBox.warning(self, '입력 오류', 'COM 포트를 선택하세요.')
                return
            params = {
                'protocol': 'Serial',
                'com_port': com,
                'baud_rate': self._e_baud.currentText(),
                'username': user,
                'password': pw,
            }
        else:
            host = self._e_host.text().strip()
            port = self._e_port.text().strip() or '22'
            if not host or not user:
                QMessageBox.warning(self, '입력 오류', 'Host와 User를 입력하세요.')
                return
            params = {
                'protocol': proto,
                'host': host, 'port': port,
                'username': user, 'password': pw,
            }

        self._log.clear()
        self._out.clear()
        self._results = {}
        self._prog.setValue(0)
        self._btn_start.setEnabled(False)
        self._btn_save.setEnabled(False)
        self._status.setText('점검 진행 중...')

        self._worker = DeviceInspectionWorker(params)
        self._worker.progress.connect(self._on_progress)
        self._worker.cmd_result.connect(self._on_cmd)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, msg: str):
        self._log.append(msg)
        # ▶ 로 시작하면 진행바 증가
        if msg.startswith('▶'):
            self._prog.setValue(self._prog.value() + 1)

    def _on_cmd(self, cmd: str, output: str):
        self._results[cmd] = output
        self._out.append(
            f'\n{"─"*60}\n'
            f'# {cmd}\n'
            f'{"─"*60}\n'
            f'{output}\n'
        )

    def _on_done(self, results: dict):
        self._results = results
        self._btn_start.setEnabled(True)
        self._btn_save.setEnabled(True)
        self._prog.setValue(self._prog.maximum())
        self._status.setText(f'✅  점검 완료 — 명령어 {len(results)}개 수집')

    def _on_error(self, msg: str):
        self._log.append(f'❌  오류: {msg}')
        self._btn_start.setEnabled(True)
        self._status.setText(f'오류: {msg}')

    def _save_report(self):
        import datetime
        if self._e_proto.currentText() == 'Serial':
            host = self._e_com.currentData() or 'serial'
        else:
            host = self._e_host.text().strip() or 'device'
        default = os.path.join(
            os.path.expanduser('~'), 'Documents',
            f'inspection_{host}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        )
        path, _ = QFileDialog.getSaveFileName(
            self, '점검 보고서 저장', default,
            'HTML (*.html);;All Files (*)'
        )
        if path:
            html = self._make_html(host)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            QMessageBox.information(self, '저장 완료', f'보고서가 저장되었습니다:\n{path}')

    def _make_html(self, host: str) -> str:
        import datetime
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 섹션별 HTML 생성
        sections_html = ''
        for cmd, desc in _INSPECT_CMDS:
            if cmd == 'terminal length 0':
                continue
            output = self._results.get(cmd, '(데이터 없음)')
            safe   = output.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            sections_html += f'''
            <div class="section">
              <div class="sec-title">
                <span class="sec-cmd">{cmd}</span>
                <span class="sec-desc">{desc}</span>
              </div>
              <pre class="output">{safe}</pre>
            </div>'''

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>장비 점검 보고서 — {host}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: "Segoe UI", "맑은 고딕", sans-serif; padding: 32px; }}
  h1 {{ font-size: 22px; color: #58a6ff; margin-bottom: 4px; }}
  .meta {{ color: #8b949e; font-size: 12px; margin-bottom: 28px; }}
  .section {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 18px; overflow: hidden; }}
  .sec-title {{ background: #21262d; padding: 10px 16px; border-bottom: 1px solid #30363d; display: flex; align-items: center; gap: 12px; }}
  .sec-cmd {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 13px; color: #79c0ff; font-weight: bold; }}
  .sec-desc {{ font-size: 11px; color: #8b949e; }}
  .output {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; line-height: 1.55; padding: 14px 16px; white-space: pre-wrap; word-break: break-all; color: #e6edf3; }}
  .output:empty::after {{ content: "(출력 없음)"; color: #484f58; }}
</style>
</head>
<body>
  <h1>🖥  장비 종합 점검 보고서</h1>
  <div class="meta">
    Host: <strong style="color:#e6edf3">{host}</strong> &nbsp;|&nbsp;
    점검 일시: <strong style="color:#e6edf3">{now}</strong> &nbsp;|&nbsp;
    수집 항목: <strong style="color:#e6edf3">{len(self._results)}</strong>개
  </div>
  {sections_html}
</body>
</html>'''

    def closeEvent(self, e):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        super().closeEvent(e)
