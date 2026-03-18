"""
네트워크 진단 탭 — Ping / TCPing 심플 버전
"""
import re
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QFrame, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QBrush, QLinearGradient, QPen,
)

from core.workers import PingThread, TCPingThread
from core.i18n import tr


# ── 컬러 상수 ─────────────────────────────────────────────────────────────────
_OK_BG   = QColor('#dcfce7')
_OK_FG   = QColor('#15803d')
_FAIL_BG = QColor('#fee2e2')
_FAIL_FG = QColor('#b91c1c')
_IDLE_BG = QColor('#f1f5f9')
_IDLE_FG = QColor('#94a3b8')


# ── 헤더 ─────────────────────────────────────────────────────────────────────
class _Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor('#0f172a'))
        g.setColorAt(1.0, QColor('#0d9488'))
        p.fillRect(self.rect(), QBrush(g))
        p.setOpacity(0.07)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 80, -30, 160, 160)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor('#f8fafc')))
        p.setFont(QFont('맑은 고딕', 16, QFont.Bold))
        p.drawText(28, 32, tr('네트워크 진단'))
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(30, 52, tr('Ping · TCP 포트 연결 상태 확인'))
        p.end()


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────
def _cell(text, fg=None, bg=None, center=True):
    it = QTableWidgetItem(text)
    it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    if fg:
        it.setForeground(QBrush(fg))
    if bg:
        it.setBackground(QBrush(bg))
    it.setTextAlignment(Qt.AlignCenter if center else (Qt.AlignVCenter | Qt.AlignLeft))
    return it


def _spin(lo, hi, val, parent=None):
    s = QSpinBox(parent)
    s.setRange(lo, hi)
    s.setValue(val)
    s.setFont(QFont('맑은 고딕', 10))
    s.setFixedHeight(34)
    s.setStyleSheet(
        'QSpinBox{background:#f8fafc;border:1px solid #e2e8f0;'
        'border-radius:7px;padding:2px 8px;color:#1e293b}'
        'QSpinBox::up-button,QSpinBox::down-button{width:18px}'
    )
    return s


def _label(text, size=9, bold=False, color='#475569'):
    l = QLabel(text)
    l.setFont(QFont('맑은 고딕', size, QFont.Bold if bold else QFont.Normal))
    l.setStyleSheet(f'color:{color};background:transparent')
    return l


# ── Ping 설정 패널 ────────────────────────────────────────────────────────────
class _PingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        v.addWidget(_label(tr('IP 목록'), bold=True))

        self.ip_edit = QTextEdit()
        self.ip_edit.setPlaceholderText('192.168.1.1\n192.168.1.2\n10.0.0.1')
        self.ip_edit.setFont(QFont('맑은 고딕', 10))
        self.ip_edit.setStyleSheet(
            'QTextEdit{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:8px;padding:6px;color:#1e293b}'
        )
        self.ip_edit.setMinimumHeight(120)
        v.addWidget(self.ip_edit)

        row = QHBoxLayout()
        row.setSpacing(10)
        c1 = QVBoxLayout(); c1.setSpacing(4)
        c1.addWidget(_label(tr('인터벌 (초)')))
        self.spin_interval = _spin(1, 60, 3)
        c1.addWidget(self.spin_interval)

        c2 = QVBoxLayout(); c2.setSpacing(4)
        c2.addWidget(_label(tr('타임아웃 (초)')))
        self.spin_timeout = _spin(1, 10, 2)
        c2.addWidget(self.spin_timeout)

        row.addLayout(c1)
        row.addLayout(c2)
        v.addLayout(row)
        v.addStretch()

    def get_ips(self):
        return [l.strip() for l in self.ip_edit.toPlainText().splitlines() if l.strip()]

    def get_interval(self): return self.spin_interval.value()
    def get_timeout(self):  return self.spin_timeout.value()


# ── TCPing 설정 패널 ──────────────────────────────────────────────────────────
class _TCPPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        v.addWidget(_label(tr('호스트'), bold=True))
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText('192.168.1.1')
        self.host_edit.setFont(QFont('맑은 고딕', 10))
        self.host_edit.setFixedHeight(34)
        self.host_edit.setStyleSheet(
            'QLineEdit{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:7px;padding:2px 10px;color:#1e293b}'
        )
        v.addWidget(self.host_edit)

        v.addWidget(_label(tr('포트 (쉼표 구분)'), bold=True))
        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText('22, 23, 80, 443')
        self.port_edit.setFont(QFont('맑은 고딕', 10))
        self.port_edit.setFixedHeight(34)
        self.port_edit.setStyleSheet(
            'QLineEdit{background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:7px;padding:2px 10px;color:#1e293b}'
        )
        v.addWidget(self.port_edit)

        row = QHBoxLayout()
        row.setSpacing(10)
        c1 = QVBoxLayout(); c1.setSpacing(4)
        c1.addWidget(_label(tr('인터벌 (초)')))
        self.spin_interval = _spin(1, 60, 3)
        c1.addWidget(self.spin_interval)

        c2 = QVBoxLayout(); c2.setSpacing(4)
        c2.addWidget(_label(tr('타임아웃 (초)')))
        self.spin_timeout = _spin(1, 10, 2)
        c2.addWidget(self.spin_timeout)

        row.addLayout(c1)
        row.addLayout(c2)
        v.addLayout(row)
        v.addStretch()

    def get_host(self):   return self.host_edit.text().strip()
    def get_ports(self):
        result = []
        for p in self.port_edit.text().split(','):
            try:
                result.append(int(p.strip()))
            except ValueError:
                pass
        return result

    def get_interval(self): return self.spin_interval.value()
    def get_timeout(self):  return self.spin_timeout.value()


# ── 결과 테이블 ───────────────────────────────────────────────────────────────
def _make_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setFont(QFont('맑은 고딕', 10))
    t.horizontalHeader().setFont(QFont('맑은 고딕', 9, QFont.Bold))
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for i in range(1, len(headers)):
        t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setShowGrid(False)
    t.setAlternatingRowColors(False)
    t.setStyleSheet(
        'QTableWidget{background:#ffffff;border:none;outline:none}'
        'QTableWidget::item{padding:5px 10px;border-bottom:1px solid #f1f5f9}'
        'QTableWidget::item:selected{background:#eff6ff;color:#1e293b}'
        'QHeaderView::section{background:#f8fafc;color:#64748b;padding:8px 10px;'
        '  border:none;border-bottom:1px solid #e2e8f0}'
    )
    return t


# ── 메인 탭 ───────────────────────────────────────────────────────────────────
class MonitoringTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ping_thread = None
        self._tcp_thread  = None
        self._ping_stats  = {}   # ip  -> {ok, fail, times, last}
        self._tcp_stats   = {}   # (host, port) -> {ok, fail, last_ms, last}
        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setObjectName('monitoringTab')
        self.setStyleSheet('#monitoringTab { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header())

        body = QWidget()
        body.setObjectName('monitoringBody')
        body.setStyleSheet('#monitoringBody { background: transparent; }')
        bv = QHBoxLayout(body)
        bv.setContentsMargins(20, 18, 20, 18)
        bv.setSpacing(16)

        # ── 좌측 설정 패널 ────────────────────────────────────────────────
        left = QFrame()
        left.setFixedWidth(256)
        left.setStyleSheet(
            'QFrame{background:#ffffff;border-radius:12px;border:1px solid #e2e8f0}'
        )
        lv = QVBoxLayout(left)
        lv.setContentsMargins(16, 14, 16, 14)
        lv.setSpacing(10)

        # 모드 토글 (Ping / TCPing)
        toggle = QHBoxLayout()
        toggle.setSpacing(0)
        self.btn_ping = QPushButton('Ping')
        self.btn_tcp  = QPushButton('TCPing')
        for btn in (self.btn_ping, self.btn_tcp):
            btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_ping.setChecked(True)
        self.btn_ping.clicked.connect(lambda: self._set_mode('ping'))
        self.btn_tcp.clicked.connect( lambda: self._set_mode('tcp'))
        toggle.addWidget(self.btn_ping)
        toggle.addWidget(self.btn_tcp)
        lv.addLayout(toggle)
        self._apply_toggle_style()

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('background:#f1f5f9;border:none;max-height:1px')
        lv.addWidget(sep)

        # 설정 스택
        self.stack = QStackedWidget()
        self._ping_panel = _PingPanel()
        self._tcp_panel  = _TCPPanel()
        self.stack.addWidget(self._ping_panel)
        self.stack.addWidget(self._tcp_panel)
        lv.addWidget(self.stack)

        # 버튼
        self.btn_start = QPushButton(tr('▶  시작'))
        self.btn_stop  = QPushButton(tr('■  중지'))
        self.btn_clear = QPushButton(tr('초기화'))
        self.btn_start.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        self.btn_stop.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        self.btn_clear.setFont(QFont('맑은 고딕', 9))
        self.btn_start.setFixedHeight(36)
        self.btn_stop.setFixedHeight(36)
        self.btn_clear.setFixedHeight(30)
        self.btn_start.setStyleSheet(
            'QPushButton{background:#0d9488;color:#fff;border:none;border-radius:8px}'
            'QPushButton:hover{background:#0f766e}'
        )
        self.btn_stop.setStyleSheet(
            'QPushButton{background:#ef4444;color:#fff;border:none;border-radius:8px}'
            'QPushButton:hover{background:#dc2626}'
            'QPushButton:disabled{background:#fca5a5;color:#fff}'
        )
        self.btn_clear.setStyleSheet(
            'QPushButton{background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0;border-radius:7px}'
            'QPushButton:hover{background:#e2e8f0}'
        )
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_clear.clicked.connect(self._clear)
        lv.addWidget(self.btn_start)
        lv.addWidget(self.btn_stop)
        lv.addWidget(self.btn_clear)

        bv.addWidget(left)

        # ── 우측 결과 패널 ────────────────────────────────────────────────
        right = QFrame()
        right.setStyleSheet(
            'QFrame{background:#ffffff;border-radius:12px;border:1px solid #e2e8f0}'
        )
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # 결과 상단 바
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:12px 12px 0 0;'
            'border-bottom:1px solid #e2e8f0}'
        )
        barv = QHBoxLayout(bar)
        barv.setContentsMargins(16, 0, 16, 0)
        self.lbl_mode = QLabel(tr('Ping 결과'))
        self.lbl_mode.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        self.lbl_mode.setStyleSheet('color:#1e293b;background:transparent;border:none')
        self.lbl_summary = QLabel('')
        self.lbl_summary.setFont(QFont('맑은 고딕', 9))
        self.lbl_summary.setStyleSheet('color:#64748b;background:transparent;border:none')
        barv.addWidget(self.lbl_mode)
        barv.addStretch()
        barv.addWidget(self.lbl_summary)
        rv.addWidget(bar)

        # 테이블 (Ping / TCP 스택)
        self.tbl_stack = QStackedWidget()
        self.ping_table = _make_table([tr('IP 주소'), tr('상태'), tr('응답시간'), tr('평균'), tr('성공'), tr('실패'), tr('마지막 확인')])
        self.tcp_table  = _make_table([tr('호스트'), tr('포트'), tr('상태'), tr('응답시간'), tr('성공'), tr('실패'), tr('마지막 확인')])
        self.tbl_stack.addWidget(self.ping_table)
        self.tbl_stack.addWidget(self.tcp_table)
        rv.addWidget(self.tbl_stack)

        bv.addWidget(right, 1)
        root.addWidget(body, 1)

    # ── 모드 전환 ─────────────────────────────────────────────────────────────
    def _set_mode(self, mode):
        self._stop()
        if mode == 'ping':
            self.btn_ping.setChecked(True)
            self.btn_tcp.setChecked(False)
            self.stack.setCurrentIndex(0)
            self.tbl_stack.setCurrentIndex(0)
            self.lbl_mode.setText(tr('Ping 결과'))
        else:
            self.btn_ping.setChecked(False)
            self.btn_tcp.setChecked(True)
            self.stack.setCurrentIndex(1)
            self.tbl_stack.setCurrentIndex(1)
            self.lbl_mode.setText(tr('TCPing 결과'))
        self._apply_toggle_style()
        self._refresh_summary()

    def _apply_toggle_style(self):
        active   = ('QPushButton{background:#0d9488;color:#fff;border:none;'
                    'border-radius:6px}')
        inactive = ('QPushButton{background:#f1f5f9;color:#64748b;'
                    'border:1px solid #e2e8f0;border-radius:6px}')
        self.btn_ping.setStyleSheet(active if self.btn_ping.isChecked() else inactive)
        self.btn_tcp.setStyleSheet( active if self.btn_tcp.isChecked()  else inactive)

    # ── 시작 ─────────────────────────────────────────────────────────────────
    def _start(self):
        if self.btn_ping.isChecked():
            self._start_ping()
        else:
            self._start_tcp()

    def _start_ping(self):
        ips = self._ping_panel.get_ips()
        if not ips:
            return
        self._stop_ping()
        for ip in ips:
            if ip not in self._ping_stats:
                self._ping_stats[ip] = {'ok': 0, 'fail': 0, 'times': [], 'last': '-'}
                self._add_ping_row(ip)
        self._ping_thread = PingThread(
            ips,
            self._ping_panel.get_interval(),
            self._ping_panel.get_timeout(),
            repeat=0, packet_size=32, check_tcp=False,
        )
        self._ping_thread.result_ready.connect(self._on_ping_result)
        self._ping_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _start_tcp(self):
        host  = self._tcp_panel.get_host()
        ports = self._tcp_panel.get_ports()
        if not host or not ports:
            return
        self._stop_tcp()
        for port in ports:
            key = (host, port)
            if key not in self._tcp_stats:
                self._tcp_stats[key] = {'ok': 0, 'fail': 0, 'last_ms': None, 'last': '-'}
                self._add_tcp_row(host, port)
        self._tcp_thread = TCPingThread(
            host, ports,
            self._tcp_panel.get_interval(),
            self._tcp_panel.get_timeout(),
            repeat=0,
        )
        self._tcp_thread.result_ready.connect(self._on_tcp_result)
        self._tcp_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    # ── 중지 ─────────────────────────────────────────────────────────────────
    def _stop(self):
        self._stop_ping()
        self._stop_tcp()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _stop_ping(self):
        if self._ping_thread and self._ping_thread.isRunning():
            self._ping_thread.stop()
            self._ping_thread.wait(2000)
            self._ping_thread = None

    def _stop_tcp(self):
        if self._tcp_thread and self._tcp_thread.isRunning():
            self._tcp_thread.stop()
            self._tcp_thread.wait(2000)
            self._tcp_thread = None

    # ── 초기화 ────────────────────────────────────────────────────────────────
    def _clear(self):
        self._stop()
        self._ping_stats.clear()
        self._tcp_stats.clear()
        self.ping_table.setRowCount(0)
        self.tcp_table.setRowCount(0)
        self.lbl_summary.setText('')

    # ── Ping 결과 처리 ────────────────────────────────────────────────────────
    def _on_ping_result(self, ip, result, color):
        if not ip:
            return
        st = self._ping_stats.get(ip)
        if st is None:
            return
        success = (color == 'green')
        m = re.search(r'Time=(\d+)ms', result, re.IGNORECASE)
        ms = int(m.group(1)) if m else None
        if success:
            st['ok'] += 1
            if ms is not None:
                st['times'] = (st['times'] + [ms])[-30:]
        else:
            st['fail'] += 1
        st['last'] = datetime.now().strftime('%H:%M:%S')

        row = self._find_row(self.ping_table, 0, ip)
        if row < 0:
            return
        avg = f"{sum(st['times']) // len(st['times'])} ms" if st['times'] else '-'
        self.ping_table.setItem(row, 1, _cell(tr('● 응답') if success else tr('● 실패'),
                                               _OK_FG if success else _FAIL_FG,
                                               _OK_BG if success else _FAIL_BG))
        self.ping_table.setItem(row, 2, _cell(f'{ms} ms' if ms is not None else '-'))
        self.ping_table.setItem(row, 3, _cell(avg))
        self.ping_table.setItem(row, 4, _cell(str(st['ok']),   _OK_FG))
        self.ping_table.setItem(row, 5, _cell(str(st['fail']), _FAIL_FG if st['fail'] else _IDLE_FG))
        self.ping_table.setItem(row, 6, _cell(st['last']))
        self._refresh_summary()

    def _add_ping_row(self, ip):
        r = self.ping_table.rowCount()
        self.ping_table.insertRow(r)
        self.ping_table.setRowHeight(r, 40)
        self.ping_table.setItem(r, 0, _cell(ip, center=False))
        self.ping_table.setItem(r, 1, _cell(tr('● 대기'), _IDLE_FG, _IDLE_BG))
        for c in range(2, 7):
            self.ping_table.setItem(r, c, _cell('-'))

    # ── TCP 결과 처리 ─────────────────────────────────────────────────────────
    def _on_tcp_result(self, host, port, result, color, resp_ms):
        if port is None:
            return
        key = (host, port)
        st  = self._tcp_stats.get(key)
        if st is None:
            return
        success = (color == 'green')
        if success:
            st['ok'] += 1
            st['last_ms'] = resp_ms
        else:
            st['fail'] += 1
        st['last'] = datetime.now().strftime('%H:%M:%S')

        row = self._find_row(self.tcp_table, 1, str(port),
                             extra_col=0, extra_val=host)
        if row < 0:
            return
        ms_str = f'{resp_ms} ms' if resp_ms is not None else '-'
        self.tcp_table.setItem(row, 2, _cell('● Open' if success else '● Closed',
                                              _OK_FG if success else _FAIL_FG,
                                              _OK_BG if success else _FAIL_BG))
        self.tcp_table.setItem(row, 3, _cell(ms_str))
        self.tcp_table.setItem(row, 4, _cell(str(st['ok']),   _OK_FG))
        self.tcp_table.setItem(row, 5, _cell(str(st['fail']), _FAIL_FG if st['fail'] else _IDLE_FG))
        self.tcp_table.setItem(row, 6, _cell(st['last']))
        self._refresh_summary()

    def _add_tcp_row(self, host, port):
        r = self.tcp_table.rowCount()
        self.tcp_table.insertRow(r)
        self.tcp_table.setRowHeight(r, 40)
        self.tcp_table.setItem(r, 0, _cell(host, center=False))
        self.tcp_table.setItem(r, 1, _cell(str(port)))
        self.tcp_table.setItem(r, 2, _cell(tr('● 대기'), _IDLE_FG, _IDLE_BG))
        for c in range(3, 7):
            self.tcp_table.setItem(r, c, _cell('-'))

    # ── 유틸 ─────────────────────────────────────────────────────────────────
    def _find_row(self, table, col, val, extra_col=None, extra_val=None):
        for r in range(table.rowCount()):
            it = table.item(r, col)
            if it and it.text() == val:
                if extra_col is None:
                    return r
                it2 = table.item(r, extra_col)
                if it2 and it2.text() == extra_val:
                    return r
        return -1

    def _refresh_summary(self):
        if self.btn_ping.isChecked():
            total = len(self._ping_stats)
            ok    = sum(1 for s in self._ping_stats.values() if s['ok'] > 0)
            self.lbl_summary.setText(f'총 {total}개  ·  응답 {ok}  실패 {total - ok}')
        else:
            total = len(self._tcp_stats)
            ok    = sum(1 for s in self._tcp_stats.values() if s['ok'] > 0)
            self.lbl_summary.setText(f'총 {total}개  ·  Open {ok}  Closed {total - ok}')

    def closeEvent(self, e):
        self._stop()
        super().closeEvent(e)
