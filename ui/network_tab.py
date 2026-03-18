"""
네트워크 자동화 탭
"""
import os
import socket

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit,
    QCheckBox, QRadioButton, QPushButton, QButtonGroup, QComboBox,
    QProgressBar, QMessageBox, QFrame, QDialog, QDesktopWidget, QSizePolicy,
    QFileDialog, QScrollBar,
)
try:
    from serial.tools import list_ports as _serial_list_ports
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPainter, QBrush, QLinearGradient, QPen, QTextCharFormat
import datetime
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal

from core.workers import NetworkWorker
from core.i18n import tr


# ── SerialReaderThread ────────────────────────────────────────────────────────
class SerialReaderThread(QThread):
    data_received = pyqtSignal(str)
    connection_lost = pyqtSignal(str)

    def __init__(self, ser):
        super().__init__()
        self._ser = ser
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                if self._ser and self._ser.is_open and self._ser.in_waiting:
                    raw = self._ser.read(self._ser.in_waiting)
                    text = raw.decode('utf-8', errors='replace')
                    self.data_received.emit(text)
                else:
                    self.msleep(30)
            except Exception as e:
                self.connection_lost.emit(str(e))
                break


# ── SerialTerminalDialog ──────────────────────────────────────────────────────
class SerialTerminalDialog(QDialog):
    def __init__(self, com_port, baud_rate, parent=None):
        super().__init__(parent)
        self.com_port = com_port
        self.baud_rate = baud_rate
        self._ser = None
        self._reader = None
        self.setWindowTitle(f'시리얼 콘솔  —  {com_port}  @  {baud_rate} bps')
        self.resize(720, 480)
        self._build_ui()
        self._connect()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)

        # 상태 표시줄
        self._status_lbl = QLabel(f'{tr("연결 중...")}  {self.com_port}')
        self._status_lbl.setFont(QFont('맑은 고딕', 8))
        self._status_lbl.setStyleSheet('color:#64748b')
        v.addWidget(self._status_lbl)

        # 출력 영역
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont('Consolas', 10))
        self._output.setStyleSheet(
            'QTextEdit{background:#0f172a;color:#e2e8f0;border:none;border-radius:6px;padding:8px}'
        )
        v.addWidget(self._output)

        # 입력 영역
        input_row = QHBoxLayout(); input_row.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText(tr('명령어 입력 후 Enter 또는 전송'))
        self._input.setFont(QFont('Consolas', 10))
        self._input.setFixedHeight(34)
        self._input.setStyleSheet(
            'QLineEdit{background:#1e293b;color:#f1f5f9;border:1px solid #334155;'
            '  border-radius:6px;padding:0 8px}'
            'QLineEdit:focus{border:1.5px solid #3b82f6}'
        )
        self._input.returnPressed.connect(self._send)
        input_row.addWidget(self._input)

        send_btn = QPushButton(tr('전송'))
        send_btn.setFixedSize(64, 34)
        send_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        send_btn.setStyleSheet(
            'QPushButton{background:#2563eb;color:#fff;border:none;border-radius:6px}'
            'QPushButton:hover{background:#1d4ed8}'
            'QPushButton:disabled{background:#475569;color:#94a3b8}'
        )
        send_btn.clicked.connect(self._send)
        self._send_btn = send_btn
        input_row.addWidget(send_btn)

        clear_btn = QPushButton(tr('지우기'))
        clear_btn.setFixedSize(64, 34)
        clear_btn.setFont(QFont('맑은 고딕', 9))
        clear_btn.setStyleSheet(
            'QPushButton{background:#334155;color:#cbd5e1;border:none;border-radius:6px}'
            'QPushButton:hover{background:#475569}'
        )
        clear_btn.clicked.connect(self._output.clear)
        input_row.addWidget(clear_btn)
        v.addLayout(input_row)

        # 하단 버튼
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self._disconnect_btn = QPushButton(tr('연결 해제'))
        self._disconnect_btn.setFixedHeight(32)
        self._disconnect_btn.setFont(QFont('맑은 고딕', 9))
        self._disconnect_btn.setStyleSheet(
            'QPushButton{background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;border-radius:6px;padding:0 14px}'
            'QPushButton:hover{background:#fecaca}'
        )
        self._disconnect_btn.clicked.connect(self.close)
        bottom_row.addWidget(self._disconnect_btn)
        v.addLayout(bottom_row)

    def _connect(self):
        if not _SERIAL_AVAILABLE:
            self._append_text(tr('[오류] pyserial 라이브러리가 없습니다.') + '\n')
            return
        try:
            import serial
            self._ser = serial.Serial(
                port=self.com_port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            self._status_lbl.setText(f'● {tr("활성화됨")}  —  {self.com_port}  @  {self.baud_rate} bps')
            self._status_lbl.setStyleSheet('color:#16a34a;font-weight:600')
            self._append_text(f'[연결됨]  {self.com_port}  @  {self.baud_rate} bps\r\n')
            self._reader = SerialReaderThread(self._ser)
            self._reader.data_received.connect(self._on_data)
            self._reader.connection_lost.connect(self._on_connection_lost)
            self._reader.start()
            self._input.setEnabled(True)
            self._send_btn.setEnabled(True)
        except Exception as e:
            self._status_lbl.setText(f'● {tr("연결 실패")}  —  {e}')
            self._status_lbl.setStyleSheet('color:#dc2626;font-weight:600')
            self._append_text(f'[연결 실패]  {e}\r\n')
            self._input.setEnabled(False)
            self._send_btn.setEnabled(False)

    def _send(self):
        if not self._ser or not self._ser.is_open:
            return
        text = self._input.text()
        self._input.clear()
        try:
            self._ser.write((text + '\r\n').encode('utf-8', errors='replace'))
        except Exception as e:
            self._append_text(f'[전송 오류]  {e}\r\n')

    def _on_data(self, text: str):
        self._append_text(text)

    def _on_connection_lost(self, msg: str):
        self._status_lbl.setText(f'● {tr("연결 끊김")}  —  {msg}')
        self._status_lbl.setStyleSheet('color:#dc2626;font-weight:600')
        self._append_text(f'\r\n[연결 끊김]  {msg}\r\n')
        self._input.setEnabled(False)
        self._send_btn.setEnabled(False)

    def _append_text(self, text: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._output.setTextCursor(cursor)
        self._output.insertPlainText(text)
        self._output.ensureCursorVisible()

    def closeEvent(self, event):
        if self._reader:
            self._reader.stop()
            self._reader.wait(1000)
        if self._ser and self._ser.is_open:
            self._ser.close()
        super().closeEvent(event)


# ── SerialTerminalDemoDialog (데모 모드 — 실제 포트 없이 UI 미리보기) ─────────
class SerialTerminalDemoDialog(QDialog):
    """실제 COM 포트 없이 콘솔 UI + Cisco 시뮬레이션을 보여주는 데모 창"""

    # 시뮬레이션 응답 테이블 {입력 키워드: 출력}
    _RESPONSES = {
        '':              '\r\n',
        'en':            'Password: ',
        'enable':        'Password: ',
        'cisco':         '\r\nRouter#',
        '?':             '\r\nExec commands:\r\n  enable   Turn on privileged commands\r\n  exit     Exit from the EXEC\r\n  ping     Send echo messages\r\n  show     Show running system information\r\n\r\nRouter>',
        'show version':  (
            '\r\nCisco IOS Software, Version 15.6(1)T, RELEASE SOFTWARE\r\n'
            'Technical Support: http://www.cisco.com/techsupport\r\n'
            'ROM: Bootstrap program is IOSv\r\n\r\n'
            'Router uptime is 3 days, 2 hours, 14 minutes\r\n'
            'System image file is "flash0:/vios-adventerprisek9-m"\r\n\r\n'
            'cisco IOSv (revision 1.0) with 460033K/62464K bytes of memory.\r\n'
            'Processor board ID 9YMAOGVH6WTUCQKIQAKMN\r\n'
            '1 Gigabit Ethernet interface\r\n'
            'DRAM configuration is 72 bits wide with parity disabled.\r\n'
            '256K bytes of non-volatile configuration memory.\r\n'
            '2097152K bytes of ATA System CompactFlash 0\r\n\r\nRouter#'
        ),
        'show ip int br': (
            '\r\nInterface              IP-Address      OK? Method Status                Protocol\r\n'
            'GigabitEthernet0/0     192.168.0.1     YES NVRAM  up                    up\r\n'
            'GigabitEthernet0/1     10.0.0.1        YES NVRAM  up                    up\r\n'
            'Loopback0              1.1.1.1         YES NVRAM  up                    up\r\n\r\nRouter#'
        ),
        'show ip interface brief': (
            '\r\nInterface              IP-Address      OK? Method Status                Protocol\r\n'
            'GigabitEthernet0/0     192.168.0.1     YES NVRAM  up                    up\r\n'
            'GigabitEthernet0/1     10.0.0.1        YES NVRAM  up                    up\r\n'
            'Loopback0              1.1.1.1         YES NVRAM  up                    up\r\n\r\nRouter#'
        ),
        'show run': (
            '\r\nBuilding configuration...\r\n\r\n'
            'Current configuration : 1842 bytes\r\n!\r\n'
            'version 15.6\r\nservice timestamps debug datetime msec\r\n'
            'service timestamps log datetime msec\r\n!\r\n'
            'hostname Router\r\n!\r\nboot-start-marker\r\nboot-end-marker\r\n!\r\n'
            'no aaa new-model\r\n!\r\nip cef\r\nno ip domain lookup\r\n!\r\n'
            'interface GigabitEthernet0/0\r\n ip address 192.168.0.1 255.255.255.0\r\n'
            ' duplex auto\r\n speed auto\r\n media-type rj45\r\n!\r\n'
            'interface GigabitEthernet0/1\r\n ip address 10.0.0.1 255.255.255.0\r\n!\r\n'
            'ip route 0.0.0.0 0.0.0.0 192.168.0.254\r\n!\r\nend\r\n\r\nRouter#'
        ),
        'show running-config': '__same__show run',
        'ping 8.8.8.8': (
            '\r\nType escape sequence to abort.\r\n'
            'Sending 5, 100-byte ICMP Echos to 8.8.8.8, timeout is 2 seconds:\r\n'
            '!!!!!\r\n'
            'Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/3 ms\r\n\r\nRouter#'
        ),
        'exit':          '\r\nRouter con0 is now available\r\n\r\nPress RETURN to get started.\r\n',
        'show clock':    '\r\n*08:43:21.123 UTC Wed Mar 18 2026\r\n\r\nRouter#',
        'show users':    '\r\n    Line       User       Host(s)              Idle       Location\r\n*  0 con 0                idle                 00:00:00\r\n\r\nRouter#',
    }

    _BOOT_MSG = (
        '\r\n'
        '          Restricted to authorized users only.\r\n'
        '          All activities may be monitored and reported.\r\n\r\n'
        'Cisco IOS Software, Version 15.6(1)T\r\n'
        'Copyright (c) 1986-2026 by Cisco Systems, Inc.\r\n\r\n'
        '████████████████████ 100%\r\n\r\n'
        'Router con0 is now available\r\n\r\n'
        'Press RETURN to get started.\r\n\r\n'
        'Router>'
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🧪  콘솔 UI 데모  —  DEMO MODE (COM1 @ 9600 bps)')
        self.resize(760, 520)
        self._prompt = 'Router>'
        self._authed = False
        self._build_ui()
        # 부팅 메시지 타이머 출력
        self._boot_lines = self._BOOT_MSG.split('\n')
        self._boot_idx = 0
        self._boot_timer = QTimer(self)
        self._boot_timer.timeout.connect(self._boot_tick)
        self._boot_timer.start(60)

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 타이틀바 (데모 배지)
        title_bar = QFrame()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet('background:#1e1b4b;border-bottom:1px solid #3730a3')
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(12, 0, 12, 0)

        dot_row = QHBoxLayout(); dot_row.setSpacing(6)
        for color in ('#ff5f57', '#ffbd2e', '#28c840'):
            d = QLabel('●')
            d.setStyleSheet(f'color:{color};font-size:10px;background:transparent;border:none')
            dot_row.addWidget(d)
        tb.addLayout(dot_row)
        tb.addSpacing(10)

        title_lbl = QLabel('콘솔 터미널  —  COM1 @ 9600 bps')
        title_lbl.setStyleSheet('color:#a5b4fc;font-family:맑은 고딕;font-size:10pt;font-weight:bold;background:transparent;border:none')
        tb.addWidget(title_lbl)
        tb.addStretch()

        demo_badge = QLabel('  🧪 DEMO MODE  ')
        demo_badge.setStyleSheet(
            'background:#7c3aed;color:#fff;font-size:8pt;font-weight:bold;'
            'border-radius:4px;padding:2px 6px;border:none'
        )
        tb.addWidget(demo_badge)
        v.addWidget(title_bar)

        # 상태바
        self._status_lbl = QLabel('● 연결됨  —  COM1  @  9600 bps  (시뮬레이션)')
        self._status_lbl.setFixedHeight(26)
        self._status_lbl.setStyleSheet(
            'color:#22c55e;font-family:맑은 고딕;font-size:8pt;font-weight:600;'
            'background:#0a1628;padding:0 12px;border-bottom:1px solid #1e293b'
        )
        v.addWidget(self._status_lbl)

        # 출력 영역
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont('Consolas', 10))
        self._output.setStyleSheet(
            'QTextEdit{background:#0d1117;color:#e6edf3;border:none;padding:8px}'
            'QScrollBar:vertical{background:#161b22;width:10px;border-radius:5px}'
            'QScrollBar::handle:vertical{background:#30363d;border-radius:5px;min-height:20px}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}'
        )
        v.addWidget(self._output, 1)

        # 입력 영역
        input_frame = QFrame()
        input_frame.setFixedHeight(50)
        input_frame.setStyleSheet('background:#0f172a;border-top:1px solid #1e293b')
        ih = QHBoxLayout(input_frame)
        ih.setContentsMargins(10, 8, 10, 8)
        ih.setSpacing(6)

        prompt_lbl = QLabel('>')
        prompt_lbl.setStyleSheet('color:#22c55e;font-family:Consolas;font-size:11pt;background:transparent;border:none')
        ih.addWidget(prompt_lbl)

        self._input = QLineEdit()
        self._input.setPlaceholderText('명령어 입력 후 Enter  (예: show version, show ip int br, ping 8.8.8.8)')
        self._input.setFont(QFont('Consolas', 10))
        self._input.setStyleSheet(
            'QLineEdit{background:#1e293b;color:#f1f5f9;border:1px solid #334155;'
            'border-radius:6px;padding:0 8px}'
            'QLineEdit:focus{border:1.5px solid #6366f1}'
        )
        self._input.returnPressed.connect(self._send)
        ih.addWidget(self._input, 1)

        send_btn = QPushButton('전송')
        send_btn.setFixedSize(60, 32)
        send_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        send_btn.setStyleSheet(
            'QPushButton{background:#4f46e5;color:#fff;border:none;border-radius:6px}'
            'QPushButton:hover{background:#4338ca}'
        )
        send_btn.clicked.connect(self._send)
        ih.addWidget(send_btn)

        clear_btn = QPushButton('지우기')
        clear_btn.setFixedSize(60, 32)
        clear_btn.setFont(QFont('맑은 고딕', 9))
        clear_btn.setStyleSheet(
            'QPushButton{background:#1e293b;color:#94a3b8;border:1px solid #334155;border-radius:6px}'
            'QPushButton:hover{background:#334155}'
        )
        clear_btn.clicked.connect(self._output.clear)
        ih.addWidget(clear_btn)
        v.addWidget(input_frame)

        # 하단 힌트 + 닫기
        bottom = QFrame()
        bottom.setFixedHeight(36)
        bottom.setStyleSheet('background:#0a0f1a;border-top:1px solid #1e293b')
        bh = QHBoxLayout(bottom)
        bh.setContentsMargins(12, 0, 12, 0)

        hint = QLabel('💡  show version  |  show ip int br  |  show run  |  ping 8.8.8.8  |  show clock  |  enable → cisco')
        hint.setStyleSheet('color:#374151;font-family:Consolas;font-size:8pt;background:transparent;border:none')
        bh.addWidget(hint, 1)

        close_btn = QPushButton('✕ 닫기')
        close_btn.setFixedSize(72, 26)
        close_btn.setStyleSheet(
            'QPushButton{background:#2a0000;color:#ff7070;border:1px solid #7f1d1d;'
            'border-radius:4px;font-size:9pt}'
            'QPushButton:hover{background:#450a0a}'
        )
        close_btn.clicked.connect(self.close)
        bh.addWidget(close_btn)
        v.addWidget(bottom)

    def _boot_tick(self):
        if self._boot_idx < len(self._boot_lines):
            self._append(self._boot_lines[self._boot_idx] + '\n')
            self._boot_idx += 1
        else:
            self._boot_timer.stop()
            self._input.setFocus()

    def _send(self):
        cmd = self._input.text().strip()
        self._input.clear()

        # 에코
        self._append(f'{cmd}\r\n', color='#86efac')

        # 응답 조회
        key = cmd.lower().strip()
        response = None
        for k, v in self._RESPONSES.items():
            if k and key == k.lower():
                response = v
                break

        # __same__ 리디렉션 처리
        if response and response.startswith('__same__'):
            alias = response[8:]
            response = self._RESPONSES.get(alias, '')

        if response is None:
            # 모르는 명령어
            response = f'\r\n% Unknown command or computer name, or unable to find computer address\r\n\r\n{self._prompt}'
        elif response == '\r\n':
            response = f'\r\n{self._prompt}'

        # enable 처리
        if key in ('en', 'enable'):
            self._append(response)
            return
        if key == 'cisco' and not self._authed:
            self._authed = True
            self._prompt = 'Router#'
            self._append('\r\nRouter#\r\n')
            return

        self._append(response + '\r\n')

    def _append(self, text: str, color: str = '#e6edf3'):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text.replace('\r\n', '\n').replace('\r', '\n'))
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()


# ── QuickCheckWorker ─────────────────────────────────────────────────────────
class QuickCheckWorker(QThread):
    progress_update = pyqtSignal(str)
    result_update   = pyqtSignal(list, list)

    def __init__(self, ip_list):
        super().__init__()
        self.ip_list = ip_list

    def run(self):
        success_ips, failed_ips = [], []
        for i, ip in enumerate(self.ip_list, 1):
            self.progress_update.emit(f'체크 중... ({i}/{len(self.ip_list)})  {ip}')
            reachable = False
            for port in [22, 23]:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.settimeout(2)
                    if s.connect_ex((ip, port)) == 0:
                        reachable = True
                except Exception:
                    pass
                finally:
                    s.close()
                if reachable:
                    break
            (success_ips if reachable else failed_ips).append(ip)
        self.result_update.emit(success_ips, failed_ips)


# ── SimpleLogViewer ──────────────────────────────────────────────────────────
class SimpleLogViewer(QDialog):
    """전문가용 SSH 세션 로그 뷰어 — 색상 코딩, 검색, 통계, 내보내기 지원"""

    # 로그 태그별 색상 정의 (전경색, 배경색)
    _LEVEL_COLORS = {
        '[ERROR]':    ('#ff5f5f', '#2a0000'),
        '[WARN]':     ('#ffb347', '#1e1400'),
        '[SUCCESS]':  ('#5fff87', '#001e0a'),
        '[INFO]':     ('#c8d0e0', None),
        '[DEBUG]':    ('#6b7280', None),
        '[CONNECT]':  ('#38bdf8', None),
        '[AUTH]':     ('#f0abfc', None),
        '[CMD]':      ('#86efac', None),
        '[HOSTNAME]': ('#fde68a', None),
        '[TACACS]':   ('#67e8f9', None),
        '[TELNET':    ('#93c5fd', None),
        '[SSH]':      ('#6ee7b7', None),
        '[SERIAL]':   ('#d8b4fe', None),
        '===':        ('#64748b', None),
    }

    def __init__(self, title=None):
        super().__init__(None)
        self.setWindowTitle(title or 'SSH 로그 뷰어')
        self.resize(860, 560)
        self.setMinimumSize(640, 400)
        self._auto_scroll = True
        self._total_lines = 0
        self._error_count = 0
        self._warn_count = 0
        self._session_start = datetime.datetime.now()
        self._host = title or ''

        # 화면 우하단 배치
        screen = QDesktopWidget().availableGeometry()
        self.move(screen.width() - 880, screen.height() - 600)

        self._build_ui()
        self._add_session_header()

    # ── UI 구성 ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 타이틀바 ──
        title_bar = QFrame()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet('background:#0f172a;border-bottom:1px solid #1e3a5f')
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(14, 0, 10, 0)

        dot_row = QHBoxLayout()
        dot_row.setSpacing(6)
        for color in ('#ff5f57', '#ffbd2e', '#28c840'):
            d = QLabel('●')
            d.setStyleSheet(f'color:{color};font-size:10px;background:transparent;border:none')
            dot_row.addWidget(d)
        tb.addLayout(dot_row)

        self._title_label = QLabel(self._host or 'SSH 로그 뷰어')
        self._title_label.setStyleSheet(
            'color:#94a3b8;font-family:맑은 고딕;font-size:10pt;'
            'font-weight:bold;background:transparent;border:none'
        )
        tb.addSpacing(10)
        tb.addWidget(self._title_label)
        tb.addStretch()

        self._status_dot = QLabel('●')
        self._status_dot.setStyleSheet('color:#22c55e;font-size:11px;background:transparent;border:none')
        self._status_label = QLabel('연결 중')
        self._status_label.setStyleSheet('color:#64748b;font-size:9pt;background:transparent;border:none')
        tb.addWidget(self._status_dot)
        tb.addSpacing(4)
        tb.addWidget(self._status_label)
        root.addWidget(title_bar)

        # ── 검색 바 ──
        search_bar = QFrame()
        search_bar.setFixedHeight(36)
        search_bar.setStyleSheet('background:#1e293b;border-bottom:1px solid #334155')
        sb = QHBoxLayout(search_bar)
        sb.setContentsMargins(10, 4, 10, 4)
        sb.setSpacing(6)

        lbl = QLabel('🔍')
        lbl.setStyleSheet('background:transparent;border:none;color:#64748b')
        sb.addWidget(lbl)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText('로그 검색... (Enter)')
        self._search_box.setStyleSheet(
            'QLineEdit{background:#0f172a;border:1px solid #334155;border-radius:4px;'
            'color:#e2e8f0;padding:2px 8px;font-family:Consolas;font-size:9pt}'
            'QLineEdit:focus{border:1px solid #3b82f6}'
        )
        self._search_box.setFixedHeight(24)
        self._search_box.returnPressed.connect(self._search)
        sb.addWidget(self._search_box, 1)

        # 필터 콤보
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(['전체', 'ERROR', 'WARN', 'INFO', 'AUTH', 'CMD'])
        self._filter_combo.setStyleSheet(
            'QComboBox{background:#0f172a;border:1px solid #334155;border-radius:4px;'
            'color:#94a3b8;padding:1px 6px;font-size:9pt;min-width:70px}'
            'QComboBox::drop-down{border:none}'
            'QComboBox QAbstractItemView{background:#1e293b;color:#e2e8f0;border:1px solid #334155}'
        )
        self._filter_combo.setFixedHeight(24)
        self._filter_combo.currentTextChanged.connect(self._apply_filter)
        sb.addWidget(self._filter_combo)

        root.addWidget(search_bar)

        # ── 로그 본문 ──
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Consolas', 9))
        self.log_text.setStyleSheet(
            'QTextEdit{background:#0d1117;color:#c9d1d9;border:none;'
            'padding:8px;line-height:1.4}'
            'QScrollBar:vertical{background:#161b22;width:10px;border-radius:5px}'
            'QScrollBar::handle:vertical{background:#30363d;border-radius:5px;min-height:20px}'
            'QScrollBar::handle:vertical:hover{background:#484f58}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}'
        )
        root.addWidget(self.log_text, 1)

        # ── 통계 바 ──
        stat_bar = QFrame()
        stat_bar.setFixedHeight(30)
        stat_bar.setStyleSheet('background:#161b22;border-top:1px solid #21262d')
        stb = QHBoxLayout(stat_bar)
        stb.setContentsMargins(12, 0, 12, 0)
        stb.setSpacing(16)

        def _stat(color, prefix):
            l = QLabel(prefix + '0')
            l.setStyleSheet(f'color:{color};font-family:Consolas;font-size:8pt;background:transparent;border:none')
            return l

        self._stat_total  = _stat('#94a3b8', 'TOTAL ')
        self._stat_error  = _stat('#ff5f5f', 'ERR ')
        self._stat_warn   = _stat('#ffb347', 'WARN ')
        self._stat_time   = _stat('#64748b', '')
        stb.addWidget(self._stat_total)
        stb.addWidget(self._stat_error)
        stb.addWidget(self._stat_warn)
        stb.addStretch()
        stb.addWidget(self._stat_time)
        root.addWidget(stat_bar)

        # ── 버튼 바 ──
        btn_bar = QFrame()
        btn_bar.setFixedHeight(38)
        btn_bar.setStyleSheet('background:#0f172a;border-top:1px solid #1e293b')
        bb = QHBoxLayout(btn_bar)
        bb.setContentsMargins(10, 4, 10, 4)
        bb.setSpacing(6)

        def _btn(text, color='#334155', fg='#94a3b8'):
            b = QPushButton(text)
            b.setFixedHeight(26)
            b.setStyleSheet(
                f'QPushButton{{background:{color};color:{fg};border:1px solid #475569;'
                f'border-radius:4px;padding:0 10px;font-size:9pt}}'
                f'QPushButton:hover{{background:#475569;color:#f1f5f9}}'
            )
            return b

        self._auto_scroll_btn = QPushButton('⬇ 자동 스크롤 ON')
        self._auto_scroll_btn.setCheckable(True)
        self._auto_scroll_btn.setChecked(True)
        self._auto_scroll_btn.setFixedHeight(26)
        self._auto_scroll_btn.setStyleSheet(
            'QPushButton{background:#1e3a5f;color:#38bdf8;border:1px solid #1e3a5f;'
            'border-radius:4px;padding:0 10px;font-size:9pt}'
            'QPushButton:!checked{background:#1e293b;color:#64748b;border:1px solid #334155}'
            'QPushButton:hover{background:#2e4a6f;color:#7dd3fc}'
        )
        self._auto_scroll_btn.toggled.connect(self._on_autoscroll_toggle)

        clear_btn  = _btn('🗑 지우기')
        copy_btn   = _btn('📋 복사')
        export_btn = _btn('💾 저장', '#1a2e1a', '#86efac')
        close_btn  = _btn('✕ 닫기', '#2a0000', '#ff7070')

        clear_btn.clicked.connect(self._clear)
        copy_btn.clicked.connect(self._copy)
        export_btn.clicked.connect(self._export)
        close_btn.clicked.connect(self.hide)

        bb.addWidget(self._auto_scroll_btn)
        bb.addWidget(clear_btn)
        bb.addWidget(copy_btn)
        bb.addStretch()
        bb.addWidget(export_btn)
        bb.addWidget(close_btn)
        root.addWidget(btn_bar)

        # 경과 시간 타이머
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start(1000)

    # ── 세션 헤더 출력 ─────────────────────────────────────────────────────────
    def _add_session_header(self):
        now = self._session_start.strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            '┌─────────────────────────────────────────────────────────────┐',
            f'│  SSH SESSION LOG                         {now}  │',
            f'│  Host: {self._host:<54}│',
            '└─────────────────────────────────────────────────────────────┘',
        ]
        for line in lines:
            self._append_raw(line, '#334155', '#0d1117')

    # ── 로그 추가 (외부 인터페이스) ────────────────────────────────────────────
    def add_log(self, message):
        message = str(message)
        ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:12]

        # 연결 상태 감지
        if any(k in message for k in ('연결 완료', 'Authentication (password) successful', 'Connected')):
            self._set_status('연결됨', '#22c55e')
        elif any(k in message for k in ('오류', 'ERROR', '실패', 'failed', 'error')):
            self._set_status('오류', '#ef4444')
            self._error_count += 1
        elif any(k in message for k in ('WARN', '경고')):
            self._warn_count += 1
        elif '완료' in message or 'SUCCESS' in message:
            self._set_status('완료', '#22c55e')

        # 색상 결정
        fg, bg = '#c9d1d9', None
        for keyword, (kfg, kbg) in self._LEVEL_COLORS.items():
            if keyword in message:
                fg, bg = kfg, kbg
                break

        # 타임스탬프 + 메시지 조합
        self._append_colored(ts, '#3b4d63', None)
        self._append_colored('  ' + message + '\n', fg, bg)

        self._total_lines += 1
        self._update_stats()

        if self._auto_scroll:
            self.log_text.moveCursor(QTextCursor.End)

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────
    def _append_colored(self, text, fg, bg=None):
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(fg))
        if bg:
            fmt.setBackground(QColor(bg))
        else:
            fmt.setBackground(QColor('#0d1117'))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

    def _append_raw(self, text, fg='#334155', bg='#0d1117'):
        self._append_colored(text + '\n', fg, bg)

    def _set_status(self, text, color):
        self._status_dot.setStyleSheet(f'color:{color};font-size:11px;background:transparent;border:none')
        self._status_label.setStyleSheet(f'color:{color};font-size:9pt;background:transparent;border:none')
        self._status_label.setText(text)

    def _update_stats(self):
        self._stat_total.setText(f'TOTAL {self._total_lines}')
        self._stat_error.setText(f'ERR {self._error_count}')
        self._stat_warn.setText(f'WARN {self._warn_count}')

    def _update_elapsed(self):
        delta = datetime.datetime.now() - self._session_start
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        self._stat_time.setText(f'경과 {h:02d}:{m:02d}:{s:02d}')

    def _on_autoscroll_toggle(self, checked):
        self._auto_scroll = checked
        self._auto_scroll_btn.setText('⬇ 자동 스크롤 ON' if checked else '⏸ 자동 스크롤 OFF')

    def _search(self):
        keyword = self._search_box.text().strip()
        if not keyword:
            return
        found = self.log_text.find(keyword)
        if not found:
            # 처음부터 다시 검색
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.log_text.setTextCursor(cursor)
            self.log_text.find(keyword)

    def _apply_filter(self, level):
        # 필터는 검색창에 키워드 자동 입력
        if level == '전체':
            self._search_box.clear()
        else:
            self._search_box.setText(f'[{level}]')

    def _clear(self):
        self.log_text.clear()
        self._total_lines = 0
        self._error_count = 0
        self._warn_count = 0
        self._session_start = datetime.datetime.now()
        self._update_stats()
        self._add_session_header()

    def _copy(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_text.toPlainText())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, '로그 저장', f'ssh_log_{self._host.replace(".", "_")}.txt',
            'Text Files (*.txt);;All Files (*)'
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        self._host = title
        if hasattr(self, '_title_label'):
            self._title_label.setText(title)

    def closeEvent(self, e):
        e.ignore()
        self.hide()


# ── 헤더 위젯 ─────────────────────────────────────────────────────────────────
class _Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor('#0f172a'))
        g.setColorAt(1.0, QColor('#1d4ed8'))
        p.fillRect(self.rect(), QBrush(g))
        p.setOpacity(0.07)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 80, -30, 160, 160)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor('#f8fafc')))
        p.setFont(QFont('맑은 고딕', 16, QFont.Bold))
        p.drawText(28, 32, '네트워크 자동화')
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(30, 52, 'SSH / Telnet 다중 접속 · 명령어 일괄 실행 · 설정 수집')
        p.end()


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────
def _card():
    f = QFrame()
    f.setStyleSheet(
        'QFrame{background:#ffffff;border-radius:10px;border:1px solid #e2e8f0}'
    )
    return f


def _sec(text):
    l = QLabel(text)
    l.setFont(QFont('맑은 고딕', 8, QFont.Bold))
    l.setStyleSheet(
        'color:#94a3b8;background:transparent;border:none;'
        'letter-spacing:1px;padding-bottom:2px'
    )
    return l


def _flabel(text, width=72):
    l = QLabel(text)
    l.setFont(QFont('맑은 고딕', 9))
    l.setStyleSheet('color:#475569;background:transparent;border:none')
    l.setFixedWidth(width)
    return l


_SS_INPUT = (
    'QLineEdit{background:#f8fafc;border:1px solid #e2e8f0;'
    'border-radius:6px;padding:3px 8px;color:#1e293b}'
    'QLineEdit:focus{border:1px solid #3b82f6}'
    'QLineEdit:disabled{background:#f1f5f9;color:#94a3b8}'
)
_SS_TEXT = (
    'QTextEdit{background:#f8fafc;border:1px solid #e2e8f0;'
    'border-radius:6px;padding:6px;color:#1e293b}'
    'QTextEdit:focus{border:1px solid #3b82f6}'
)
_SS_RADIO = 'QRadioButton{color:#1e293b;background:transparent;border:none}'
_SS_CHECK = 'QCheckBox{color:#475569;background:transparent;border:none}'

_SS_SEP = 'QFrame{background:#f1f5f9;border:none;max-height:1px}'


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(_SS_SEP)
    return f


# ── 보안 안내 다이얼로그 ──────────────────────────────────────────────────────
class _SecurityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('보안 안내'))
        self.setFixedWidth(500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet('QDialog{background:#f8fafc}')
        self._build()

    def _build(self):
        from PyQt5.QtWidgets import QScrollArea
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 헤더 (그라데이션) ──────────────────────────────────────
        hdr = _SecHeader()
        hdr.setFixedHeight(88)
        root.addWidget(hdr)

        # ── 스크롤 가능한 본문 ────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea{background:#f8fafc;border:none}')

        body = QWidget()
        body.setObjectName('secBody')
        body.setStyleSheet('#secBody{background:#f8fafc}')
        bv = QVBoxLayout(body)
        bv.setContentsMargins(24, 20, 24, 8)
        bv.setSpacing(10)

        _items = [
            ('🌐', '외부 서버 통신 없음',
             '모든 네트워크 연결은 사용자가 입력한 장비 IP로만 이루어집니다. '
             '수집된 데이터는 외부로 전송되지 않습니다.',
             '#2563eb', '#eff6ff'),
            ('🔑', '비밀번호 미저장',
             '입력한 사용자명 · 비밀번호 · Enable 비밀번호는 실행 중 메모리에만 존재합니다. '
             '파일, 레지스트리, 데이터베이스 어디에도 저장하지 않습니다.',
             '#059669', '#f0fdf4'),
            ('🛡️', 'SSH 접속 시 호스트 키 자동 수락',
             'SSH로 처음 접속하는 장비의 신원(호스트 키)을 자동으로 수락합니다. '
             '내부 관리망 전용 도구이므로 외부 인터넷 환경에서는 사용하지 마세요.',
             '#d97706', '#fffbeb'),
            ('💾', '결과 파일 저장 경로',
             '명령어 실행 결과는 사용자가 지정한 로컬 폴더에만 저장됩니다. '
             '경로를 지정하지 않으면 파일이 생성되지 않습니다.',
             '#7c3aed', '#f5f3ff'),
            ('🔌', '사용 포트',
             'SSH: TCP 22 (변경 가능)  ·  Telnet: TCP 23\n'
             '빠른 체크는 위 포트의 연결 가능 여부만 확인합니다.',
             '#475569', '#f1f5f9'),
        ]

        for emoji, ttl, desc, accent, bg in _items:
            card = QFrame()
            card.setObjectName('secCard')
            card.setStyleSheet(
                f'QFrame#secCard{{'
                f'background:{bg};'
                f'border-radius:10px;'
                f'border:1px solid {accent}22}}'
            )
            cv = QHBoxLayout(card)
            cv.setContentsMargins(0, 0, 0, 0)
            cv.setSpacing(0)

            # 왼쪽 컬러 바
            bar = QFrame()
            bar.setFixedWidth(4)
            bar.setStyleSheet(
                f'QFrame{{background:{accent};border-radius:2px;'
                f'border-top-right-radius:0;border-bottom-right-radius:0}}'
            )
            cv.addWidget(bar)

            # 내용
            inner = QVBoxLayout()
            inner.setContentsMargins(14, 12, 14, 12)
            inner.setSpacing(4)

            row_h = QHBoxLayout()
            row_h.setSpacing(6)
            em_lbl = QLabel(emoji)
            em_lbl.setFont(QFont('맑은 고딕', 13))
            em_lbl.setStyleSheet('background:transparent;border:none')
            ttl_lbl = QLabel(ttl)
            ttl_lbl.setFont(QFont('맑은 고딕', 10, QFont.Bold))
            ttl_lbl.setStyleSheet(
                f'color:{accent};background:transparent;border:none')
            row_h.addWidget(em_lbl)
            row_h.addWidget(ttl_lbl)
            row_h.addStretch()

            desc_lbl = QLabel(desc)
            desc_lbl.setFont(QFont('맑은 고딕', 9))
            desc_lbl.setStyleSheet('color:#475569;background:transparent;border:none')
            desc_lbl.setWordWrap(True)

            inner.addLayout(row_h)
            inner.addWidget(desc_lbl)
            cv.addLayout(inner)
            bv.addWidget(card)

        bv.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # ── 하단 버튼 영역 ────────────────────────────────────────
        footer = QWidget()
        footer.setStyleSheet('background:#f1f5f9;border-top:1px solid #e2e8f0')
        fh = QHBoxLayout(footer)
        fh.setContentsMargins(24, 12, 24, 12)

        notice = QLabel('내부 관리 네트워크 전용 프로그램입니다.')
        notice.setFont(QFont('맑은 고딕', 8))
        notice.setStyleSheet('color:#94a3b8;background:transparent')

        close_btn = QPushButton(tr('확인'))
        close_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        close_btn.setFixedSize(88, 34)
        close_btn.setStyleSheet(
            'QPushButton{background:#1e293b;color:#ffffff;border:none;border-radius:7px}'
            'QPushButton:hover{background:#334155}'
            'QPushButton:pressed{background:#0f172a}'
        )
        close_btn.clicked.connect(self.accept)

        fh.addWidget(notice)
        fh.addStretch()
        fh.addWidget(close_btn)
        root.addWidget(footer)
        self.setMinimumHeight(460)
        self.setMaximumHeight(600)


class _SecHeader(QWidget):
    """보안 안내 다이얼로그 그라데이션 헤더"""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor('#0f172a'))
        g.setColorAt(1.0, QColor('#1e3a5f'))
        p.fillRect(self.rect(), QBrush(g))
        # 우측 장식 원
        p.setOpacity(0.07)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 80, -30, 140, 140)
        p.drawEllipse(self.width() - 160, 20, 80, 80)
        p.setOpacity(1.0)
        # 아이콘
        p.setPen(QPen(QColor('#ffffff')))
        p.setFont(QFont('맑은 고딕', 22))
        p.drawText(24, 52, '🔒')
        # 제목
        p.setFont(QFont('맑은 고딕', 15, QFont.Bold))
        p.drawText(60, 48, tr('보안 안내'))
        # 부제
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(61, 68, tr('이 프로그램의 보안 정책 안내입니다.'))
        p.end()


# ── 보안 배지 (클릭 가능) ─────────────────────────────────────────────────────
class _SecurityBadge(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self._hov = False
        self._apply_style()

        h = QHBoxLayout(self)
        h.setContentsMargins(14, 0, 14, 0)
        h.setSpacing(10)

        lock = QLabel('🔒')
        lock.setFont(QFont('맑은 고딕', 14))
        lock.setStyleSheet('background:transparent;border:none')

        tv = QVBoxLayout()
        tv.setSpacing(1)
        t1 = QLabel(tr('보안 안내'))
        t1.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        t1.setStyleSheet('color:#1e293b;background:transparent;border:none')
        t2 = QLabel(tr('이 프로그램의 보안 동작 확인'))
        t2.setFont(QFont('맑은 고딕', 8))
        t2.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        tv.addWidget(t1)
        tv.addWidget(t2)

        arr = QLabel('→')
        arr.setFont(QFont('맑은 고딕', 12, QFont.Bold))
        arr.setStyleSheet('color:#94a3b8;background:transparent;border:none')

        h.addWidget(lock)
        h.addLayout(tv)
        h.addStretch()
        h.addWidget(arr)

    def _apply_style(self):
        if self._hov:
            self.setStyleSheet(
                'QFrame{background:#f0f9ff;border-radius:8px;'
                'border:1px solid #7dd3fc}'
            )
        else:
            self.setStyleSheet(
                'QFrame{background:#f8fafc;border-radius:8px;'
                'border:1px solid #e2e8f0}'
            )

    def enterEvent(self, e):
        self._hov = True;  self._apply_style()

    def leaveEvent(self, e):
        self._hov = False; self._apply_style()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            dlg = _SecurityDialog(self)
            dlg.exec_()


# ── 메인 탭 ───────────────────────────────────────────────────────────────────
class NetworkTab(QWidget):
    def __init__(self, parent, license_manager=None):
        super().__init__(parent)
        self.parent = parent
        self._lm = license_manager
        self._log_viewers = []
        self.check_worker = None
        self.init_ui()

    def translate(self, text):
        if self.parent and hasattr(self.parent, 'translate'):
            return self.parent.translate(text)
        return text

    # ── SSH 로그 ──────────────────────────────────────────────────────────────
    def start_ssh_debug_dialog(self, worker):
        try:
            title = f'SSH 세션 로그 — {worker.ip}'
            if not self._log_viewers:
                viewer = SimpleLogViewer(title)
                self._log_viewers.append(viewer)
                if hasattr(self, 'ssh_log_btn') and self.ssh_log_btn.isChecked():
                    viewer.show()
                else:
                    viewer.hide()
            else:
                viewer = self._log_viewers[-1]
                viewer.setWindowTitle(title)
                # 새 장비 세션 구분선
                viewer.add_log(f'')
                viewer.add_log(f'┄┄┄┄┄  새 세션 시작: {worker.ip}  ┄┄┄┄┄')
                if hasattr(self, 'ssh_log_btn') and self.ssh_log_btn.isChecked():
                    viewer.show()
            worker.debug_log.connect(viewer.add_log)
        except Exception as e:
            worker.debug_log.connect(lambda msg: print(f'SSH 디버그: {msg}'))

    def toggle_ssh_log(self):
        if self.ssh_log_btn.isChecked():
            self.show_ssh_logs()
            self.ssh_log_btn.setText(tr('SSH 로그 닫기'))
        else:
            self.hide_ssh_logs()
            self.ssh_log_btn.setText(tr('SSH 로그 보기'))

    def show_ssh_logs(self):
        if self._log_viewers:
            for v in self._log_viewers:
                if v.isHidden():
                    v.show()
        else:
            viewer = SimpleLogViewer('SSH 로그 뷰어')
            self._log_viewers.append(viewer)
            viewer.show()
            viewer.add_log('SSH 로그 뷰어가 활성화되었습니다.')

    def hide_ssh_logs(self):
        for v in self._log_viewers:
            v.hide()

    # ── 빠른 체크 ─────────────────────────────────────────────────────────────
    def start_quick_check(self):
        ip_list = [l.strip() for l in self.ip_list_text.toPlainText().splitlines() if l.strip()]
        if not ip_list:
            self._set_check_ui('error', 'IP 리스트가 비어있습니다')
            return
        self.quick_check_btn.setEnabled(False)
        self._set_check_ui('info', f'체크 중... (0/{len(ip_list)})')
        self.check_worker = QuickCheckWorker(ip_list)
        self.check_worker.progress_update.connect(self.on_check_progress)
        self.check_worker.result_update.connect(self.on_check_complete)
        self.check_worker.start()

    def on_check_progress(self, message):
        self._set_check_ui('info', message)

    def on_check_complete(self, success_ips, failed_ips):
        text = f'연결 가능 {len(success_ips)}개  /  실패 {len(failed_ips)}개'
        self._set_check_ui('ok' if success_ips else 'error', text)
        if self.auto_exclude_failed.isChecked() and failed_ips:
            self.ip_list_text.setPlainText('\n'.join(success_ips))
        self.quick_check_btn.setEnabled(True)

    def _set_check_ui(self, kind, text):
        # bg / border / icon문자 / 텍스트색
        _map = {
            'ok':    ('#f0fdf4', '#86efac', '✓', '#15803d'),
            'error': ('#fef2f2', '#fca5a5', '✕', '#dc2626'),
            'info':  ('#f8fafc', '#cbd5e1', '…', '#64748b'),
        }
        bg, border, icon, fg = _map.get(kind, ('#f8fafc', '#e2e8f0', '—', '#94a3b8'))
        self._check_frame.setStyleSheet(
            f'QFrame{{background:{bg};border-radius:8px;border:1.5px solid {border}}}'
        )
        self._check_dot.setText(icon)
        self._check_dot.setStyleSheet(
            f'background:transparent;border:none;color:{fg};font-weight:700'
        )
        self.check_result_label.setText(text)
        self.check_result_label.setStyleSheet(
            f'background:transparent;border:none;color:{fg};font-size:9pt'
        )

    # ── UI 구성 ───────────────────────────────────────────────────────────────
    def init_ui(self):
        self.setObjectName('networkTabWidget')
        self.setStyleSheet('#networkTabWidget { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header())

        body = QWidget()
        body.setObjectName('networkBody')
        body.setStyleSheet('#networkBody { background: transparent; }')
        bv = QHBoxLayout(body)
        bv.setContentsMargins(18, 16, 18, 16)
        bv.setSpacing(12)

        bv.addWidget(self._build_left(),   2)
        bv.addWidget(self._build_center(), 2)
        bv.addWidget(self._build_right(),  3)

        root.addWidget(body, 1)
        self.setObjectName('NetworkTab')

    # ── 좌측: IP 리스트 + 빠른 체크 + 상태 ───────────────────────────────────
    def _build_left(self):
        card = _card()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        v.addWidget(_sec(tr('장비 IP 리스트')))
        self.ip_list_text = QTextEdit()
        self.ip_list_text.setPlaceholderText(tr('IP 주소를 각 줄에\n하나씩 입력하세요'))
        self.ip_list_text.setFont(QFont('맑은 고딕', 10))
        self.ip_list_text.setStyleSheet(_SS_TEXT)
        self.ip_list_text.setMinimumHeight(130)
        v.addWidget(self.ip_list_text)

        v.addWidget(_sep())
        v.addWidget(_sec(tr('빠른 연결 체크')))

        self.quick_check_btn = QPushButton(tr('연결 체크 시작'))
        self.quick_check_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self.quick_check_btn.setFixedHeight(32)
        self.quick_check_btn.setStyleSheet(
            'QPushButton{background:#10b981;color:#fff;border:none;border-radius:7px}'
            'QPushButton:hover{background:#059669}'
            'QPushButton:disabled{background:#a7f3d0}'
        )
        self.quick_check_btn.clicked.connect(self.start_quick_check)
        v.addWidget(self.quick_check_btn)

        # 체크 결과 — 도트 + 텍스트 배지
        self._check_frame = QFrame()
        self._check_frame.setFixedHeight(44)
        self._check_frame.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0}'
        )
        cf = QHBoxLayout(self._check_frame)
        cf.setContentsMargins(10, 0, 10, 0)
        cf.setSpacing(8)

        self._check_dot = QLabel('—')
        self._check_dot.setFont(QFont('맑은 고딕', 13, QFont.Bold))
        self._check_dot.setFixedWidth(22)
        self._check_dot.setAlignment(Qt.AlignCenter)
        self._check_dot.setStyleSheet('background:transparent;border:none;color:#cbd5e1;font-weight:700')

        self.check_result_label = QLabel(tr('체크 대기 중...'))
        self.check_result_label.setFont(QFont('맑은 고딕', 9))
        self.check_result_label.setWordWrap(True)
        self.check_result_label.setStyleSheet('background:transparent;border:none;color:#94a3b8')

        cf.addWidget(self._check_dot)
        cf.addWidget(self.check_result_label, 1)
        v.addWidget(self._check_frame)

        self.auto_exclude_failed = QCheckBox(tr('실패한 IP 자동 제외'))
        self.auto_exclude_failed.setChecked(True)
        self.auto_exclude_failed.setFont(QFont('맑은 고딕', 9))
        self.auto_exclude_failed.setStyleSheet(_SS_CHECK)
        v.addWidget(self.auto_exclude_failed)

        v.addWidget(_sep())
        v.addWidget(_sec(tr('실행 상태')))

        self.execution_status_label = QTextEdit()
        self.execution_status_label.setReadOnly(True)
        self.execution_status_label.setPlainText(tr('대기 중...'))
        self.execution_status_label.setFont(QFont('맑은 고딕', 9))
        self.execution_status_label.setStyleSheet(_SS_TEXT)
        v.addWidget(self.execution_status_label, 1)

        return card

    # ── 중앙: 명령어 입력 + 실행 제어 ─────────────────────────────────────────
    def _build_center(self):
        card = _card()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        v.addWidget(_sec(tr('명령어 입력')))
        self.command_input = QTextEdit()
        self.command_input.setPlaceholderText(
            tr('예시:') + '\nshow version\nshow running-config\nshow ip interface brief'
        )
        self.command_input.setFont(QFont('맑은 고딕', 10))
        self.command_input.setStyleSheet(_SS_TEXT)
        self.command_input.setMinimumHeight(80)
        self.command_input.setMaximumHeight(160)
        v.addWidget(self.command_input)

        # 템플릿 + SSH 로그
        tpl_row = QHBoxLayout()
        tpl_row.setSpacing(8)
        tpl_lbl = QLabel(tr('템플릿'))
        tpl_lbl.setFont(QFont('맑은 고딕', 9))
        tpl_lbl.setStyleSheet('color:#475569;background:transparent;border:none')

        self.command_template = QComboBox()
        self.command_template.addItems([
            tr('선택하세요...'), tr('기본 정보 수집'), tr('인터페이스 정보'), tr('라우팅 정보'), tr('보안 설정 확인')
        ])
        self.command_template.setFont(QFont('맑은 고딕', 9))
        self.command_template.setFixedWidth(150)
        self.command_template.setFixedHeight(28)
        self.command_template.setStyleSheet(
            'QComboBox{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
            '  padding:2px 8px;color:#1e293b}'
            'QComboBox::drop-down{border:none;width:20px}'
        )
        self.command_template.currentIndexChanged.connect(self.apply_template)

        self.ssh_log_btn = QPushButton(tr('SSH 로그 보기'))
        self.ssh_log_btn.setFont(QFont('맑은 고딕', 9))
        self.ssh_log_btn.setFixedHeight(28)
        self.ssh_log_btn.setFixedWidth(110)
        self.ssh_log_btn.setCheckable(True)
        self.ssh_log_btn.setStyleSheet(
            'QPushButton{background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;'
            '  border-radius:6px;padding:2px 8px}'
            'QPushButton:checked{background:#eff6ff;color:#2563eb;border-color:#bfdbfe}'
            'QPushButton:hover{background:#e2e8f0}'
        )
        self.ssh_log_btn.clicked.connect(self.toggle_ssh_log)

        tpl_row.addWidget(tpl_lbl)
        tpl_row.addWidget(self.command_template)
        tpl_row.addStretch()
        tpl_row.addWidget(self.ssh_log_btn)
        v.addLayout(tpl_row)

        v.addWidget(_sep())

        # ── 실행 제어 컨테이너 ──────────────────────────────────────────────
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0}'
        )
        ctrl_v = QVBoxLayout(ctrl_frame)
        ctrl_v.setContentsMargins(10, 10, 10, 10)
        ctrl_v.setSpacing(8)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.execute_btn = QPushButton(tr('▶  실행'))
        self.execute_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        self.execute_btn.setFixedHeight(38)
        self.execute_btn.setStyleSheet(
            'QPushButton{background:#2563eb;color:#fff;border:none;'
            '  border-radius:8px;padding:0 22px}'
            'QPushButton:hover{background:#1d4ed8}'
            'QPushButton:pressed{background:#1e40af}'
        )
        self.execute_btn.clicked.connect(self.parent.start_execution)

        self.stop_btn = QPushButton(tr('⏹  중지'))
        self.stop_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        self.stop_btn.setFixedHeight(38)
        self.stop_btn.setStyleSheet(
            'QPushButton{background:#fff;color:#ef4444;border:1.5px solid #fca5a5;'
            '  border-radius:8px;padding:0 18px}'
            'QPushButton:hover{background:#fef2f2;border-color:#ef4444}'
            'QPushButton:pressed{background:#fee2e2}'
        )
        self.stop_btn.clicked.connect(self.parent.stop_execution)

        clear_btn = QPushButton(tr('↺  초기화'))
        clear_btn.setFont(QFont('맑은 고딕', 9))
        clear_btn.setFixedHeight(38)
        clear_btn.setStyleSheet(
            'QPushButton{background:#fff;color:#64748b;border:1.5px solid #e2e8f0;'
            '  border-radius:8px;padding:0 14px}'
            'QPushButton:hover{background:#f1f5f9;border-color:#94a3b8}'
        )
        clear_btn.clicked.connect(self.clear_inputs)

        btn_row.addWidget(self.execute_btn, 3)
        btn_row.addWidget(self.stop_btn, 2)
        btn_row.addWidget(clear_btn, 2)
        ctrl_v.addLayout(btn_row)

        # ── 카운터 패널 ───────────────────────────────────────────────────────
        self._elapsed_secs = 0
        self._exec_timer = QTimer()
        self._exec_timer.setInterval(1000)
        self._exec_timer.timeout.connect(self._tick_timer)

        counter_row = QHBoxLayout()
        counter_row.setSpacing(0)
        counter_row.setContentsMargins(0, 6, 0, 2)

        # 완료 / 전체
        done_wrap = QVBoxLayout()
        done_wrap.setSpacing(2)
        done_wrap.setAlignment(Qt.AlignCenter)
        self._stat_done = QLabel('— / —')
        self._stat_done.setFont(QFont('맑은 고딕', 18, QFont.Bold))
        self._stat_done.setAlignment(Qt.AlignCenter)
        self._stat_done.setStyleSheet('color:#1e293b;background:transparent;border:none')
        _done_sub = QLabel(tr('완료 / 전체'))
        _done_sub.setFont(QFont('맑은 고딕', 8))
        _done_sub.setAlignment(Qt.AlignCenter)
        _done_sub.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        done_wrap.addWidget(self._stat_done)
        done_wrap.addWidget(_done_sub)

        # 실패
        fail_wrap = QVBoxLayout()
        fail_wrap.setSpacing(2)
        fail_wrap.setAlignment(Qt.AlignCenter)
        self._stat_fail = QLabel('—')
        self._stat_fail.setFont(QFont('맑은 고딕', 18, QFont.Bold))
        self._stat_fail.setAlignment(Qt.AlignCenter)
        self._stat_fail.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        _fail_sub = QLabel(tr('실패'))
        _fail_sub.setFont(QFont('맑은 고딕', 8))
        _fail_sub.setAlignment(Qt.AlignCenter)
        _fail_sub.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        fail_wrap.addWidget(self._stat_fail)
        fail_wrap.addWidget(_fail_sub)

        # 경과 시간
        time_wrap = QVBoxLayout()
        time_wrap.setSpacing(2)
        time_wrap.setAlignment(Qt.AlignCenter)
        self._stat_time = QLabel('00:00')
        self._stat_time.setFont(QFont('Consolas', 17, QFont.Bold))
        self._stat_time.setAlignment(Qt.AlignCenter)
        self._stat_time.setStyleSheet('color:#1e293b;background:transparent;border:none')
        _time_sub = QLabel(tr('경과'))
        _time_sub.setFont(QFont('맑은 고딕', 8))
        _time_sub.setAlignment(Qt.AlignCenter)
        _time_sub.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        time_wrap.addWidget(self._stat_time)
        time_wrap.addWidget(_time_sub)

        def _vdiv():
            d = QFrame()
            d.setFrameShape(QFrame.VLine)
            d.setStyleSheet('QFrame{color:#e2e8f0}')
            return d

        counter_row.addLayout(done_wrap, 3)
        counter_row.addWidget(_vdiv())
        counter_row.addLayout(fail_wrap, 2)
        counter_row.addWidget(_vdiv())
        counter_row.addLayout(time_wrap, 2)
        ctrl_v.addLayout(counter_row)

        # 얇은 진행 바 (보조)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet(
            'QProgressBar{background:#e2e8f0;border-radius:2px;border:none}'
            'QProgressBar::chunk{background:qlineargradient('
            '  x1:0,y1:0,x2:1,y2:0,stop:0 #3b82f6,stop:1 #2563eb);'
            '  border-radius:2px}'
        )
        ctrl_v.addWidget(self.progress_bar)

        # ── 실패 IP 목록 ──────────────────────────────────────────────────────
        self._failed_ips_label = QLabel(tr('실패한 IP  ·  클릭하면 복사'))
        self._failed_ips_label.setFont(QFont('맑은 고딕', 8))
        self._failed_ips_label.setStyleSheet('color:#94a3b8;background:transparent;border:none;margin-top:4px')
        self._failed_ips_label.hide()

        self._failed_ips_box = QTextEdit()
        self._failed_ips_box.setReadOnly(True)
        self._failed_ips_box.setFixedHeight(64)
        self._failed_ips_box.setFont(QFont('Consolas', 9))
        self._failed_ips_box.setStyleSheet(
            'QTextEdit{'
            '  background:#fff5f5;border:1px solid #fca5a5;border-radius:4px;'
            '  padding:4px;color:#dc2626}'
            'QTextEdit:hover{background:#fee2e2}'
        )
        self._failed_ips_copied = False
        self._failed_ips_box.mousePressEvent = self._copy_failed_ips
        self._failed_ips_box.hide()

        ctrl_v.addWidget(self._failed_ips_label)
        ctrl_v.addWidget(self._failed_ips_box)

        v.addWidget(ctrl_frame)
        v.addStretch()

        return card

    # ── 우측: 인증 + 접속 + 저장 ──────────────────────────────────────────────
    def _build_right(self):
        card = _card()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(6)

        # ── 인증 정보 ────────────────────────────────────────────────────────
        v.addWidget(_sec(tr('인증 정보')))

        for label_txt, attr, is_pw in [
            (tr('사용자명'), 'username_input', False),
            (tr('비밀번호'), 'password_input', True),
        ]:
            row = QHBoxLayout(); row.setSpacing(8)
            row.addWidget(_flabel(label_txt))
            edit = QLineEdit()
            edit.setFont(QFont('맑은 고딕', 10))
            edit.setFixedHeight(30)
            edit.setStyleSheet(_SS_INPUT)
            if is_pw:
                edit.setEchoMode(QLineEdit.Password)
            setattr(self, attr, edit)
            row.addWidget(edit)
            v.addLayout(row)

        en_row = QHBoxLayout(); en_row.setSpacing(8)
        en_row.addWidget(_flabel(tr('Enable PW')))
        self.enable_checkbox = QCheckBox()
        self.enable_checkbox.setStyleSheet('background:transparent;border:none')
        self.enable_password_input = QLineEdit()
        self.enable_password_input.setEchoMode(QLineEdit.Password)
        self.enable_password_input.setEnabled(False)
        self.enable_password_input.setFont(QFont('맑은 고딕', 10))
        self.enable_password_input.setFixedHeight(30)
        self.enable_password_input.setStyleSheet(_SS_INPUT)
        self.enable_checkbox.toggled.connect(self.enable_password_input.setEnabled)
        en_row.addWidget(self.enable_checkbox)
        en_row.addWidget(self.enable_password_input, 1)
        v.addLayout(en_row)

        v.addWidget(_sep())

        # ── 접속 설정 ────────────────────────────────────────────────────────
        v.addWidget(_sec(tr('접속 설정')))

        ct_row = QHBoxLayout(); ct_row.setSpacing(8)
        ct_row.addWidget(_flabel(tr('접속 방식')))
        self.conn_type_group = QButtonGroup(self)
        self.ssh_radio    = QRadioButton('SSH')
        self.telnet_radio = QRadioButton('Telnet')
        self.serial_radio = QRadioButton(tr('시리얼 (COM)'))
        self.ssh_radio.setChecked(True)
        for r in (self.ssh_radio, self.telnet_radio, self.serial_radio):
            r.setFont(QFont('맑은 고딕', 9))
            r.setStyleSheet(_SS_RADIO)
            self.conn_type_group.addButton(r)
            ct_row.addWidget(r)
        ct_row.addStretch()
        v.addLayout(ct_row)

        # SSH 포트 행
        port_row = QHBoxLayout(); port_row.setSpacing(8)
        port_row.addWidget(_flabel(tr('SSH 포트')))
        self.ssh_port_input = QLineEdit('22')
        self.ssh_port_input.setFont(QFont('맑은 고딕', 10))
        self.ssh_port_input.setFixedWidth(60)
        self.ssh_port_input.setFixedHeight(30)
        self.ssh_port_input.setStyleSheet(_SS_INPUT)
        self.ssh_radio.toggled.connect(self.ssh_port_input.setEnabled)
        port_row.addWidget(self.ssh_port_input)
        port_row.addStretch()
        v.addLayout(port_row)

        # 시리얼 설정 패널 (시리얼 선택 시만 표시)
        self._serial_panel = QFrame()
        self._serial_panel.setStyleSheet(
            'QFrame{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:2px}'
        )
        sp_v = QVBoxLayout(self._serial_panel)
        sp_v.setContentsMargins(8, 6, 8, 6)
        sp_v.setSpacing(6)

        com_row = QHBoxLayout(); com_row.setSpacing(6)
        com_row.addWidget(_flabel(tr('COM 포트')))
        self.com_port_combo = QComboBox()
        self.com_port_combo.setFont(QFont('맑은 고딕', 9))
        self.com_port_combo.setFixedHeight(30)
        self.com_port_combo.setFixedWidth(110)
        self.com_port_combo.setStyleSheet(_SS_INPUT)
        self._refresh_com_ports()
        com_row.addWidget(self.com_port_combo)

        self._com_refresh_btn = QPushButton('↺')
        self._com_refresh_btn.setFixedSize(30, 30)
        self._com_refresh_btn.setFont(QFont('맑은 고딕', 11))
        self._com_refresh_btn.setToolTip(tr('포트 목록 새로고침'))
        self._com_refresh_btn.setStyleSheet(
            'QPushButton{background:#e2e8f0;border:none;border-radius:6px}'
            'QPushButton:hover{background:#cbd5e1}'
        )
        self._com_refresh_btn.clicked.connect(self._refresh_com_ports)
        com_row.addWidget(self._com_refresh_btn)
        com_row.addStretch()
        sp_v.addLayout(com_row)

        baud_row = QHBoxLayout(); baud_row.setSpacing(6)
        baud_row.addWidget(_flabel(tr('보드레이트')))
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.setFont(QFont('맑은 고딕', 9))
        self.baud_rate_combo.setFixedHeight(30)
        self.baud_rate_combo.setFixedWidth(110)
        self.baud_rate_combo.setStyleSheet(_SS_INPUT)
        for br in ('9600', '19200', '38400', '57600', '115200'):
            self.baud_rate_combo.addItem(br)
        self.baud_rate_combo.setCurrentText('9600')
        baud_row.addWidget(self.baud_rate_combo)
        baud_row.addStretch()
        sp_v.addLayout(baud_row)

        # 콘솔 연결 버튼
        console_row = QHBoxLayout()
        self._serial_connect_btn = QPushButton(tr('🖥  콘솔 연결'))
        self._serial_connect_btn.setFixedHeight(32)
        self._serial_connect_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self._serial_connect_btn.setStyleSheet(
            'QPushButton{background:#0f766e;color:#fff;border:none;border-radius:6px;padding:0 14px}'
            'QPushButton:hover{background:#0d9488}'
        )
        self._serial_connect_btn.clicked.connect(self._open_serial_console)
        console_row.addWidget(self._serial_connect_btn)

        # 데모 테스트 버튼
        demo_btn = QPushButton('🧪 테스트')
        demo_btn.setFixedHeight(32)
        demo_btn.setFont(QFont('맑은 고딕', 9))
        demo_btn.setToolTip('실제 포트 없이 콘솔 UI 미리보기')
        demo_btn.setStyleSheet(
            'QPushButton{background:#4c1d95;color:#c4b5fd;border:1px solid #6d28d9;'
            'border-radius:6px;padding:0 12px}'
            'QPushButton:hover{background:#5b21b6;color:#ddd6fe}'
        )
        demo_btn.clicked.connect(self._open_serial_demo)
        console_row.addWidget(demo_btn)
        console_row.addStretch()
        sp_v.addLayout(console_row)

        self._serial_panel.hide()
        v.addWidget(self._serial_panel)

        # 시리얼 선택 시 패널 토글
        self.serial_radio.toggled.connect(self._on_serial_toggled)

        ex_row = QHBoxLayout(); ex_row.setSpacing(8)
        ex_row.addWidget(_flabel(tr('실행 방식')))
        self.exec_type_group  = QButtonGroup(self)
        self.concurrent_radio = QRadioButton(tr('동시 실행'))
        self.sequential_radio = QRadioButton(tr('순차 실행'))
        self.concurrent_radio.setChecked(True)
        for r in (self.concurrent_radio, self.sequential_radio):
            r.setFont(QFont('맑은 고딕', 9))
            r.setStyleSheet(_SS_RADIO)
            self.exec_type_group.addButton(r)
            ex_row.addWidget(r)
        ex_row.addStretch()
        v.addLayout(ex_row)

        v.addWidget(_sep())

        # ── 출력 저장 ────────────────────────────────────────────────────────
        v.addWidget(_sec(tr('출력 저장')))

        path_row = QHBoxLayout(); path_row.setSpacing(6)
        _default_save_path = os.path.join(os.path.expanduser('~'), 'Documents', 'NetworkAutomation')
        self.save_path_input = QLineEdit(_default_save_path)
        self.save_path_input.setPlaceholderText(tr('결과 저장 경로'))
        self.save_path_input.setFont(QFont('맑은 고딕', 9))
        self.save_path_input.setFixedHeight(30)
        self.save_path_input.setStyleSheet(_SS_INPUT)

        _btn_ss = (
            'QPushButton{background:#64748b;color:#ffffff;border:none;'
            '  border-radius:6px;font-weight:600}'
            'QPushButton:hover{background:#475569}'
        )
        sel_btn = QPushButton(tr('경로'))
        sel_btn.setFixedSize(48, 30)
        sel_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        sel_btn.setStyleSheet(_btn_ss)
        sel_btn.clicked.connect(self.parent.select_save_path)

        open_btn = QPushButton(tr('열기'))
        open_btn.setFixedSize(48, 30)
        open_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        open_btn.setStyleSheet(_btn_ss)
        open_btn.clicked.connect(self.parent.open_save_folder)

        path_row.addWidget(self.save_path_input, 1)
        path_row.addWidget(sel_btn)
        path_row.addWidget(open_btn)
        v.addLayout(path_row)

        # 파일명 형식
        v.addWidget(_sec(tr('파일명 형식')))
        self.filename_group      = QButtonGroup(self)
        self.ip_only_radio       = QRadioButton(tr('IP만'))
        self.hostname_only_radio = QRadioButton(tr('Hostname만'))
        self.ip_hostname_radio   = QRadioButton(tr('IP + Hostname'))
        self.hostname_ip_radio   = QRadioButton(tr('Hostname + IP'))
        self.hostname_only_radio.setChecked(True)

        fn_row1 = QHBoxLayout(); fn_row1.setSpacing(4)
        fn_row2 = QHBoxLayout(); fn_row2.setSpacing(4)
        for r in (self.ip_only_radio, self.hostname_only_radio,
                  self.ip_hostname_radio, self.hostname_ip_radio):
            r.setFont(QFont('맑은 고딕', 9))
            r.setStyleSheet(_SS_RADIO)
            self.filename_group.addButton(r)

        fn_row1.addWidget(self.ip_only_radio)
        fn_row1.addWidget(self.hostname_only_radio)
        fn_row1.addStretch()
        fn_row2.addWidget(self.ip_hostname_radio)
        fn_row2.addWidget(self.hostname_ip_radio)
        fn_row2.addStretch()
        v.addLayout(fn_row1)
        v.addLayout(fn_row2)

        warn = QLabel(tr('※ Hostname 추출은 sh run 전체가 필요합니다'))
        warn.setFont(QFont('맑은 고딕', 8))
        warn.setStyleSheet('color:#f59e0b;background:transparent;border:none')
        warn.setWordWrap(True)
        v.addWidget(warn)

        v.addStretch()

        # 보안 안내 배지
        v.addWidget(_SecurityBadge())
        return card

    # ── 템플릿 ────────────────────────────────────────────────────────────────
    def apply_template(self, index):
        if index == 0:
            return
        templates = {
            1: ['terminal length 0', 'show version', 'show inventory',
                'show running-config', 'show ip interface brief',
                'show interfaces status', 'show environment all',
                'show processes cpu sorted', 'show memory statistics'],
            2: ['terminal length 0', 'show interfaces', 'show interfaces status',
                'show interfaces description', 'show ip interface brief',
                'show cdp neighbors detail', 'show lldp neighbors detail'],
            3: ['terminal length 0', 'show ip route', 'show ip protocols',
                'show ip ospf neighbor', 'show ip ospf database',
                'show ip bgp summary', 'show ip bgp'],
            4: ['terminal length 0', 'show access-lists', 'show ip access-lists',
                'show running-config | include access-list',
                'show crypto isakmp policy', 'show crypto ipsec sa',
                'show ip nat translations'],
        }
        if index in templates:
            current = self.command_input.toPlainText().strip()
            if current:
                existing = set(current.splitlines())
                new_cmds = [c for c in templates[index] if c not in existing]
                if new_cmds:
                    self.command_input.setPlainText(current + '\n' + '\n'.join(new_cmds))
            else:
                self.command_input.setPlainText('\n'.join(templates[index]))
        self.command_template.setCurrentIndex(0)

    # ── 카운터 패널 제어 ──────────────────────────────────────────────────────
    def _tick_timer(self):
        self._elapsed_secs += 1
        m, s = divmod(self._elapsed_secs, 60)
        self._stat_time.setText(f'{m:02d}:{s:02d}')

    def start_counter(self, total: int):
        self._elapsed_secs = 0
        self._failed_ip_list = []
        self._stat_done.setText(f'0 / {total}')
        self._stat_done.setStyleSheet('color:#1e293b;background:transparent;border:none')
        self._stat_fail.setText('0')
        self._stat_fail.setStyleSheet('color:#94a3b8;background:transparent;border:none')
        self._stat_time.setText('00:00')
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self._failed_ips_copied = False
        self._failed_ips_label.setText(tr('실패한 IP  ·  클릭하면 복사'))
        self._failed_ips_label.setStyleSheet('color:#94a3b8;background:transparent;border:none;margin-top:4px')
        self._failed_ips_box.setStyleSheet(
            'QTextEdit{'
            '  background:#fff5f5;border:1px solid #fca5a5;border-radius:4px;'
            '  padding:4px;color:#dc2626}'
            'QTextEdit:hover{background:#fee2e2}'
        )
        self._failed_ips_label.hide()
        self._failed_ips_box.hide()
        self._failed_ips_box.clear()
        self._exec_timer.start()

    def update_counter(self, done: int, total: int, failed: int, failed_ip: str = None):
        self._stat_done.setText(f'{done} / {total}')
        self.progress_bar.setValue(done)
        if failed_ip and failed_ip not in self._failed_ip_list:
            self._failed_ip_list.append(failed_ip)
            self._failed_ips_box.setPlainText('\n'.join(self._failed_ip_list))
            self._failed_ips_label.show()
            self._failed_ips_box.show()
        if failed > 0:
            self._stat_fail.setText(str(failed))
            self._stat_fail.setStyleSheet('color:#ef4444;background:transparent;border:none')

    def stop_counter(self):
        self._exec_timer.stop()
        self._stat_done.setStyleSheet('color:#16a34a;background:transparent;border:none')

    def _copy_failed_ips(self, event):
        from PyQt5.QtWidgets import QApplication
        text = self._failed_ips_box.toPlainText()
        if not text:
            return
        if self._failed_ips_copied:
            # 두 번째 클릭 → 표시 초기화
            self._failed_ips_copied = False
            self._failed_ips_label.setText(tr('실패한 IP  ·  클릭하면 복사'))
            self._failed_ips_label.setStyleSheet('color:#94a3b8;background:transparent;border:none;margin-top:4px')
            self._failed_ips_box.setStyleSheet(
                'QTextEdit{'
                '  background:#fff5f5;border:1px solid #fca5a5;border-radius:4px;'
                '  padding:4px;color:#dc2626}'
                'QTextEdit:hover{background:#fee2e2}'
            )
        else:
            # 첫 번째 클릭 → 복사 후 표시 유지
            QApplication.clipboard().setText(text)
            self._failed_ips_copied = True
            n = len(self._failed_ip_list)
            self._failed_ips_label.setText(f'✓ {n}개 IP 복사됨  ·  다시 클릭하면 닫기')
            self._failed_ips_label.setStyleSheet('color:#16a34a;background:transparent;border:none;margin-top:4px')
            self._failed_ips_box.setStyleSheet(
                'QTextEdit{'
                '  background:#f0fdf4;border:1.5px solid #86efac;border-radius:4px;'
                '  padding:4px;color:#15803d}'
                'QTextEdit:hover{background:#dcfce7}'
            )

    # ── 시리얼 포트 ───────────────────────────────────────────────────────────
    def _open_serial_demo(self):
        """콘솔 UI 데모 — 실제 포트 없이 Cisco 시뮬레이션"""
        dlg = SerialTerminalDemoDialog(parent=self)
        dlg.exec_()

    def _open_serial_console(self):
        com_port = self.com_port_combo.currentText()
        if not com_port or com_port == tr('(포트 없음)'):
            QMessageBox.warning(self, tr('포트 없음'), tr('연결할 COM 포트를 선택해주세요.'))
            return
        baud_rate = int(self.baud_rate_combo.currentText())
        dlg = SerialTerminalDialog(com_port, baud_rate, parent=self)
        dlg.exec_()

    def _refresh_com_ports(self):
        self.com_port_combo.clear()
        if _SERIAL_AVAILABLE:
            ports = [p.device for p in _serial_list_ports.comports()]
        else:
            ports = []
        if ports:
            for p in ports:
                self.com_port_combo.addItem(p)
        else:
            self.com_port_combo.addItem(tr('(포트 없음)'))

    def _on_serial_toggled(self, checked: bool):
        if checked:
            # 라이센스 확인
            if self._lm is None or not self._lm.is_licensed():
                from ui.premium_popup import PremiumPopup
                PremiumPopup(self, feature='시리얼 (COM) 콘솔 접속').exec_()
                # 라디오 버튼을 SSH로 되돌림 (시그널 블로킹)
                self.serial_radio.blockSignals(True)
                self.ssh_radio.setChecked(True)
                self.serial_radio.blockSignals(False)
                return

        self._serial_panel.setVisible(checked)
        # 시리얼 선택 시 SSH 포트 비활성화, 순차 실행 강제
        self.ssh_port_input.setEnabled(not checked and self.ssh_radio.isChecked())
        if checked:
            self.sequential_radio.setChecked(True)
            self.concurrent_radio.setEnabled(False)
            self.sequential_radio.setEnabled(False)
        else:
            self.concurrent_radio.setEnabled(True)
            self.sequential_radio.setEnabled(True)

    def get_serial_params(self) -> dict:
        """시리얼 파라미터 반환"""
        return {
            'com_port': self.com_port_combo.currentText(),
            'baud_rate': int(self.baud_rate_combo.currentText()),
        }

    # ── 파일명 형식 ───────────────────────────────────────────────────────────
    def get_filename_format(self) -> str:
        """UI에서 선택된 파일명 형식 반환"""
        if self.ip_only_radio.isChecked():
            return "ip_only"
        elif self.ip_hostname_radio.isChecked():
            return "ip_hostname"
        elif self.hostname_ip_radio.isChecked():
            return "hostname_ip"
        return "hostname_only"

    # ── 초기화 ────────────────────────────────────────────────────────────────
    def clear_inputs(self):
        reply = QMessageBox.question(
            self, tr('초기화 확인'), tr('모든 입력 필드를 초기화하시겠습니까?'),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.command_input.clear()
            self.command_template.setCurrentIndex(0)
            self.progress_bar.setValue(0)
