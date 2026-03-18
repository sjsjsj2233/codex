"""
로그 분석 탭 — Cisco IOS / IOS-XE / NX-OS / ASA / Router
"""
import os
import re
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QTextEdit, QMessageBox,
    QCheckBox, QGroupBox, QTabWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from core.log_analyzer.parser import LogParserThread
from core.log_analyzer.constants import SEVERITY_COLORS, NETWORK_EVENTS, SECURITY_EVENTS

# 심각도 배경색 (연한 버전)
_BG = {
    'EMERGENCY': QColor(255, 220, 220),
    'ALERT':     QColor(255, 220, 220),
    'CRITICAL':  QColor(255, 220, 220),
    'ERROR':     QColor(255, 235, 235),
    'WARNING':   QColor(255, 243, 220),
    'NOTICE':    QColor(255, 251, 220),
    'INFO':      QColor(255, 255, 255),
    'DEBUG':     QColor(245, 245, 245),
}

_SEV_ORDER = ['EMERGENCY', 'ALERT', 'CRITICAL', 'ERROR', 'WARNING', 'NOTICE', 'INFO', 'DEBUG']


class LogAnalyzerTab:
    """main_window 에서 as_widget() 으로 사용"""

    def __init__(self, parent=None):
        self._widget = _LogAnalyzerWidget(parent)

    def as_widget(self):
        return self._widget


class _LogAnalyzerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_data      = []   # 전체 파싱 결과
        self.filtered_data = []   # 필터 적용 결과
        self.parser_thread = None
        self.file_queue    = []
        self.current_files = []

        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────
    def _build_ui(self):
        from ui.report_tab import _Header
        self.setObjectName('logAnalyzerWidget')
        self.setStyleSheet('#logAnalyzerWidget { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header(
            '로그 분석',
            'Cisco IOS / IOS-XE / NX-OS / ASA 로그 파일 파싱 · 분석 · 보고서',
            '#0f172a', '#dc2626',
        ))

        body = QWidget()
        body.setObjectName('logAnalyzerBody')
        body.setStyleSheet('#logAnalyzerBody { background: transparent; }')
        bv = QVBoxLayout(body)
        bv.setContentsMargins(8, 8, 8, 8)
        bv.setSpacing(6)
        root.addWidget(body, 1)

        # ── 상단 컨트롤 바 ──────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(6)

        self.btn_open = QPushButton("📂 로그 파일 열기")
        self.btn_open.setFixedHeight(32)
        self.btn_open.clicked.connect(self._open_files)
        top.addWidget(self.btn_open)

        self.device_combo = QComboBox()
        self.device_combo.setFixedHeight(32)
        self.device_combo.addItems([
            "자동 감지", "IOS-XE (Switch)", "IOS (Switch)",
            "NX-OS (Nexus)", "ASA/FTD", "Router (ISR/ASR)", "WLC (9800)",
        ])
        self.device_combo.setFixedWidth(160)
        top.addWidget(QLabel("장비:"))
        top.addWidget(self.device_combo)

        self.btn_parse = QPushButton("▶ 분석")
        self.btn_parse.setFixedHeight(32)
        self.btn_parse.setEnabled(False)
        self.btn_parse.clicked.connect(self._start_parse)
        top.addWidget(self.btn_parse)

        self.btn_clear = QPushButton("🗑 초기화")
        self.btn_clear.setFixedHeight(32)
        self.btn_clear.clicked.connect(self._clear)
        top.addWidget(self.btn_clear)

        self.btn_save = QPushButton("💾 내보내기")
        self.btn_save.setFixedHeight(32)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._export)
        top.addWidget(self.btn_save)

        self.btn_html = QPushButton("🌐 HTML 보고서")
        self.btn_html.setFixedHeight(32)
        self.btn_html.setEnabled(False)
        self.btn_html.clicked.connect(self._export_html)
        top.addWidget(self.btn_html)

        top.addStretch()
        self.lbl_file = QLabel("파일을 선택하세요")
        self.lbl_file.setStyleSheet("color:#64748b;font-size:11px")
        top.addWidget(self.lbl_file)
        bv.addLayout(top)

        # ── 진행 바 ──────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.hide()
        bv.addWidget(self.progress)

        # ── 필터 바 ──────────────────────────────────────────────
        fbox = QHBoxLayout()
        fbox.setSpacing(6)

        fbox.addWidget(QLabel("🔍 검색:"))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("키워드 또는 IP")
        self.kw_input.setFixedHeight(28)
        self.kw_input.textChanged.connect(self._apply_filters)
        fbox.addWidget(self.kw_input, 2)

        fbox.addWidget(QLabel("심각도:"))
        self.sev_combo = QComboBox()
        self.sev_combo.setFixedHeight(28)
        self.sev_combo.addItems(["전체", "ERROR 이상", "WARNING 이상", "NOTICE 이상"])
        self.sev_combo.currentIndexChanged.connect(self._apply_filters)
        fbox.addWidget(self.sev_combo)

        fbox.addWidget(QLabel("이벤트:"))
        self.evt_combo = QComboBox()
        self.evt_combo.setFixedHeight(28)
        self.evt_combo.addItem("전체", None)
        for k in NETWORK_EVENTS:
            self.evt_combo.addItem(f"[네트워크] {k}", k)
        for k in SECURITY_EVENTS:
            self.evt_combo.addItem(f"[보안] {k}", k)
        self.evt_combo.currentIndexChanged.connect(self._apply_filters)
        fbox.addWidget(self.evt_combo, 1)

        fbox.addWidget(QLabel("파일:"))
        self.file_combo = QComboBox()
        self.file_combo.setFixedHeight(28)
        self.file_combo.addItem("전체", None)
        self.file_combo.currentIndexChanged.connect(self._apply_filters)
        fbox.addWidget(self.file_combo, 1)

        self.lbl_count = QLabel("0 건")
        self.lbl_count.setStyleSheet("color:#3b82f6;font-weight:bold;font-size:12px")
        fbox.addWidget(self.lbl_count)

        bv.addLayout(fbox)

        # ── 메인 스플리터 ────────────────────────────────────────
        splitter = QSplitter(Qt.Vertical)

        # 로그 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["시간", "심각도", "Facility", "호스트", "메시지", "이벤트"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(5, 120)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.verticalHeader().hide()
        self.table.setFont(QFont("Consolas", 9))
        self.table.itemSelectionChanged.connect(self._on_row_select)
        splitter.addWidget(self.table)

        # 탭 (요약 / 상세)
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setMaximumHeight(220)

        # 요약 탭
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 9))
        self.detail_tabs.addTab(self.summary_text, "📊 요약")

        # 상세 탭
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Consolas", 9))
        self.detail_tabs.addTab(self.detail_text, "🔍 상세")

        splitter.addWidget(self.detail_tabs)
        splitter.setSizes([500, 200])
        bv.addWidget(splitter)

        # ── 상태바 ───────────────────────────────────────────────
        self.lbl_status = QLabel("준비")
        self.lbl_status.setStyleSheet("color:#64748b;font-size:11px;padding:2px 0")
        bv.addWidget(self.lbl_status)

    # ── 파일 열기 ────────────────────────────────────────────────
    def _open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "로그 파일 선택", "",
            "로그 파일 (*.log *.txt *.syslog *.gz);;모든 파일 (*)"
        )
        if not paths:
            return
        self.current_files = paths
        names = [os.path.basename(p) for p in paths]
        self.lbl_file.setText(", ".join(names[:3]) + (f" 외 {len(names)-3}개" if len(names) > 3 else ""))
        self.btn_parse.setEnabled(True)
        self.lbl_status.setText(f"{len(paths)}개 파일 선택됨")

    # ── 분석 시작 ────────────────────────────────────────────────
    _DEVICE_MAP = {
        0: None, 1: 'ios_xe', 2: 'ios',
        3: 'nxos', 4: 'asa', 5: 'router', 6: 'wlc',
    }

    def _start_parse(self):
        if not self.current_files:
            return
        # 이전 데이터 명시 해제
        self.log_data      = []
        self.filtered_data = []
        self.table.setRowCount(0)
        self.file_queue = list(self.current_files)
        self.file_combo.clear()
        self.file_combo.addItem("전체", None)
        for p in self.current_files:
            self.file_combo.addItem(os.path.basename(p), p)

        self.btn_parse.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.progress.show()
        self._parse_next()

    def _parse_next(self):
        if not self.file_queue:
            self._on_all_done()
            return
        path = self.file_queue.pop(0)
        device = self._DEVICE_MAP.get(self.device_combo.currentIndex())
        self.lbl_status.setText(f"분석 중: {os.path.basename(path)}")

        self.parser_thread = LogParserThread(path, device)
        self.parser_thread.progress_update.connect(self.progress.setValue)
        self.parser_thread.parsing_complete.connect(
            lambda logs, p=path: self._on_file_done(logs, p))
        self.parser_thread.error_occurred.connect(self._on_error)
        self.parser_thread.start()

    # 파일당 최대 보관 건수 (ERROR/WARNING은 무조건, INFO 이하는 이 한도까지)
    _MAX_PER_FILE   = 20_000
    _MAX_INFO_TOTAL = 30_000   # INFO/DEBUG/NOTICE 전체 합산 상한

    def _on_file_done(self, logs, path):
        from PyQt5.QtWidgets import QApplication
        fname = os.path.basename(path)

        # 우선순위 분리
        important = [e for e in logs if e.get('severity','INFO')
                     in ('EMERGENCY','ALERT','CRITICAL','ERROR','WARNING')]
        others    = [e for e in logs if e.get('severity','INFO')
                     not in ('EMERGENCY','ALERT','CRITICAL','ERROR','WARNING')]

        # INFO 이하는 전체 합산 상한 체크
        info_used = sum(1 for e in self.log_data
                        if e.get('severity','INFO')
                        not in ('EMERGENCY','ALERT','CRITICAL','ERROR','WARNING'))
        info_room = max(0, self._MAX_INFO_TOTAL - info_used)
        others    = others[:info_room]

        # 파일당 상한 (important 포함)
        combined = important + others
        combined = combined[:self._MAX_PER_FILE]

        for entry in combined:
            entry['source_file'] = fname
        self.log_data.extend(combined)

        skipped = len(logs) - len(combined)
        skip_note = f" (INFO {skipped:,}건 생략)" if skipped > 0 else ""
        self.lbl_status.setText(f"{fname}: {len(combined):,}건 파싱 완료{skip_note}")
        QApplication.processEvents()   # UI 갱신 기회
        self._parse_next()

    def _on_all_done(self):
        from PyQt5.QtWidgets import QApplication
        self.progress.hide()
        self.btn_parse.setEnabled(True)
        self.btn_save.setEnabled(bool(self.log_data))
        self.btn_html.setEnabled(bool(self.log_data))
        self.lbl_status.setText("필터 적용 중…")
        QApplication.processEvents()
        self._apply_filters()
        QApplication.processEvents()
        self._update_summary()
        total_orig = sum(1 for _ in self.log_data)   # 이미 제한된 수
        self.lbl_status.setText(
            f"분석 완료: 총 {len(self.log_data):,}건 ({len(self.current_files)}개 파일)")

    def _on_error(self, msg):
        self.lbl_status.setText(f"오류: {msg}")
        self._parse_next()

    # ── 필터 적용 ────────────────────────────────────────────────
    _SEV_THRESHOLD = {
        0: set(),                                                    # 전체
        1: {'EMERGENCY','ALERT','CRITICAL','ERROR'},
        2: {'EMERGENCY','ALERT','CRITICAL','ERROR','WARNING'},
        3: {'EMERGENCY','ALERT','CRITICAL','ERROR','WARNING','NOTICE'},
    }

    def _apply_filters(self):
        kw       = self.kw_input.text().strip().lower()
        sev_idx  = self.sev_combo.currentIndex()
        sev_set  = self._SEV_THRESHOLD.get(sev_idx, set())
        evt_type = self.evt_combo.currentData()
        src_file = self.file_combo.currentData()

        result = []
        for entry in self.log_data:
            if sev_set and entry.get('severity', 'INFO') not in sev_set:
                continue
            if evt_type and entry.get('event_type') != evt_type:
                continue
            if src_file and entry.get('source_file') != os.path.basename(src_file):
                continue
            if kw and kw not in entry.get('raw', '').lower():
                continue
            result.append(entry)

        self.filtered_data = result
        self._render_table()

    # ── 테이블 렌더링 ────────────────────────────────────────────
    def _render_table(self):
        MAX_ROWS = 2000
        data = self.filtered_data[:MAX_ROWS]

        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)           # 기존 행 제거 먼저 (메모리 즉시 해제)
        self.table.setRowCount(len(data))

        bold = QFont("Consolas", 9, QFont.Bold)
        for row, entry in enumerate(data):
            sev = entry.get('severity', 'INFO')
            bg  = _BG.get(sev, QColor(255, 255, 255))
            fg  = SEVERITY_COLORS.get(sev, QColor(0, 0, 0))

            values = [
                entry.get('timestamp', ''),
                sev,
                entry.get('facility_name', entry.get('facility', '')),
                entry.get('hostname', ''),
                entry.get('message', entry.get('raw', '')[:200]),
                entry.get('event_type', ''),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setBackground(bg)
                if col == 1:
                    item.setForeground(fg)
                    item.setFont(bold)
                self.table.setItem(row, col, item)

        self.table.setUpdatesEnabled(True)

        total = len(self.filtered_data)
        suffix = f" (상위 {MAX_ROWS}건 표시)" if total > MAX_ROWS else ""
        self.lbl_count.setText(f"{total:,}건{suffix}")

    # ── 행 선택 → 상세 표시 ──────────────────────────────────────
    def _on_row_select(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = self.table.currentRow()
        if row >= len(self.filtered_data):
            return
        entry = self.filtered_data[row]
        lines = [
            f"시간     : {entry.get('timestamp','-')}",
            f"심각도   : {entry.get('severity','-')}",
            f"Facility : {entry.get('facility','-')}",
            f"호스트   : {entry.get('hostname','-')}",
            f"이벤트   : {entry.get('event_type','-')} [{entry.get('event_category','-')}]",
            f"파일     : {entry.get('source_file','-')}",
            "",
            "── 메시지 ──────────────────────────────────────────",
            entry.get('message', entry.get('raw', '')),
            "",
            "── 원본 라인 ────────────────────────────────────────",
            entry.get('raw', ''),
        ]
        self.detail_text.setPlainText("\n".join(lines))
        self.detail_tabs.setCurrentIndex(1)

    # ── 요약 통계 ────────────────────────────────────────────────
    def _update_summary(self):
        data = self.log_data
        if not data:
            self.summary_text.setPlainText("데이터 없음")
            return

        # 심각도별 집계
        sev_count = {}
        for e in data:
            s = e.get('severity', 'INFO')
            sev_count[s] = sev_count.get(s, 0) + 1

        # 이벤트 타입별 집계
        evt_count = {}
        for e in data:
            t = e.get('event_type')
            if t:
                evt_count[t] = evt_count.get(t, 0) + 1

        # 호스트별 집계
        host_count = {}
        for e in data:
            h = e.get('hostname', '')
            if h:
                host_count[h] = host_count.get(h, 0) + 1

        # Facility별 집계
        fac_count = {}
        for e in data:
            f = e.get('facility_name', '')
            if f:
                fac_count[f] = fac_count.get(f, 0) + 1

        lines = [
            f"{'='*50}",
            f"  로그 분석 요약",
            f"{'='*50}",
            f"  총 로그 수   : {len(data):,}건",
            f"  파일 수      : {len(self.current_files)}개",
            "",
            "── 심각도별 ─────────────────────────────────────────",
        ]
        for sev in _SEV_ORDER:
            cnt = sev_count.get(sev, 0)
            if cnt:
                bar = '█' * min(30, cnt * 30 // max(sev_count.values()))
                lines.append(f"  {sev:<10}: {cnt:>6,}건  {bar}")

        lines += ["", "── 이벤트 유형 TOP 15 ───────────────────────────────"]
        for k, v in sorted(evt_count.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"  {k:<25}: {v:>6,}건")

        lines += ["", "── Facility TOP 15 ──────────────────────────────────"]
        for k, v in sorted(fac_count.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"  {k:<25}: {v:>6,}건")

        if host_count:
            lines += ["", "── 호스트별 TOP 10 ──────────────────────────────────"]
            for k, v in sorted(host_count.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"  {k:<25}: {v:>6,}건")

        self.summary_text.setPlainText("\n".join(lines))
        self.detail_tabs.setCurrentIndex(0)

    # ── 초기화 ───────────────────────────────────────────────────
    def _clear(self):
        self.log_data      = []
        self.filtered_data = []
        self.current_files = []
        self.file_queue    = []
        self.table.setRowCount(0)
        self.summary_text.clear()
        self.detail_text.clear()
        self.file_combo.clear()
        self.file_combo.addItem("전체", None)
        self.lbl_file.setText("파일을 선택하세요")
        self.lbl_count.setText("0 건")
        self.lbl_status.setText("초기화 완료")
        self.btn_parse.setEnabled(False)
        self.btn_save.setEnabled(False)

    # ── HTML 보고서 ──────────────────────────────────────────────
    def _export_html(self):
        import json, webbrowser, html as _html
        data = self.log_data
        if not data:
            return

        gen_time  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _fnames   = [os.path.basename(f) for f in self.current_files]
        if len(_fnames) <= 5:
            file_list = ", ".join(_fnames)
        else:
            file_list = ", ".join(_fnames[:5]) + f" 외 {len(_fnames)-5}개"

        # ── 집계 ────────────────────────────────────────────────
        sev_count  = {}
        evt_count  = {}
        fac_count  = {}
        host_count = {}
        mnemonic_count = {}

        for e in data:
            s = e.get('severity', 'INFO')
            sev_count[s] = sev_count.get(s, 0) + 1
            t = e.get('event_type')
            if t:
                evt_count[t] = evt_count.get(t, 0) + 1
            f = e.get('facility_name', '')
            if f:
                fac_count[f] = fac_count.get(f, 0) + 1
            h = e.get('hostname', '')
            if h:
                host_count[h] = host_count.get(h, 0) + 1
            mn = e.get('mnemonic', '')
            if mn and s in ('EMERGENCY','ALERT','CRITICAL','ERROR','WARNING'):
                mnemonic_count[mn] = mnemonic_count.get(mn, 0) + 1

        total     = len(data)
        error_cnt = sum(sev_count.get(s,0) for s in ('EMERGENCY','ALERT','CRITICAL','ERROR'))
        warn_cnt  = sev_count.get('WARNING', 0)
        info_cnt  = sev_count.get('INFO', 0)

        # ── 전체 로그 JSON 직렬화 (최대 30,000건) ───────────────
        SEV_MAP = {
            'EMERGENCY':'#dc2626','ALERT':'#dc2626','CRITICAL':'#b91c1c',
            'ERROR':'#ef4444','WARNING':'#f97316','NOTICE':'#eab308',
            'INFO':'#22c55e','DEBUG':'#94a3b8',
        }
        HTML_LOG_LIMIT = 30_000
        # ERROR/WARNING 우선 포함, 나머지는 최신순으로 채움
        priority = [e for e in data if e.get('severity','') in ('EMERGENCY','ALERT','CRITICAL','ERROR','WARNING')]
        others   = [e for e in data if e.get('severity','') not in ('EMERGENCY','ALERT','CRITICAL','ERROR','WARNING')]
        embed_data = priority[:HTML_LOG_LIMIT]
        remaining  = HTML_LOG_LIMIT - len(embed_data)
        if remaining > 0:
            embed_data += others[:remaining]
        embed_data.sort(key=lambda e: e.get('timestamp',''))
        truncated = total > HTML_LOG_LIMIT
        truncated_note = (f"※ 전체 {total:,}건 중 ERROR/WARNING 우선 {len(embed_data):,}건만 표시됩니다."
                          if truncated else "")

        rows_json = json.dumps([
            {
                'ts':   e.get('timestamp','')[:19],
                'sev':  e.get('severity','INFO'),
                'fac':  e.get('facility_name', e.get('facility','')),
                'host': e.get('hostname',''),
                'msg':  e.get('message', e.get('raw',''))[:300],
                'evt':  e.get('event_type',''),
                'src':  e.get('source_file',''),
                'raw':  e.get('raw','')[:500],
            }
            for e in embed_data
        ], ensure_ascii=False)

        # ── 대시보드용 Python 헬퍼 ──────────────────────────────
        def bar_rows(items, max_n=15, color="#3b82f6"):
            if not items:
                return "<p class='empty'>데이터 없음</p>"
            top = sorted(items.items(), key=lambda x: -x[1])[:max_n]
            mx  = top[0][1] or 1
            out = ""
            for k, v in top:
                pct = int(v / mx * 100)
                out += (f'<div class="brow"><span class="blabel">{_html.escape(str(k))}</span>'
                        f'<div class="btrack"><div class="bfill" style="width:{pct}%;background:{color}"></div></div>'
                        f'<span class="bval">{v:,}</span></div>')
            return out

        def sev_bars_html():
            out = ""
            for s in _SEV_ORDER:
                cnt = sev_count.get(s, 0)
                if not cnt:
                    continue
                pct = int(cnt / total * 100)
                c   = SEV_MAP.get(s, '#94a3b8')
                out += (f'<div class="brow"><span class="blabel" style="color:{c};font-weight:700">{s}</span>'
                        f'<div class="btrack"><div class="bfill" style="width:{pct}%;background:{c}">'
                        f'<span style="font-size:10px;color:#fff;padding-left:4px">{cnt:,}</span>'
                        f'</div></div><span class="bval">{pct}%</span></div>')
            return out

        def donut_svg():
            if total == 0:
                return ""
            r, cx, cy, sw = 52, 72, 72, 24
            circ  = 2 * 3.14159 * r
            e_pct = error_cnt / total
            w_pct = warn_cnt  / total
            o_pct = 1.0 - e_pct - w_pct
            def arc(pct, color, off):
                if pct <= 0:
                    return ""
                return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none"'
                        f' stroke="{color}" stroke-width="{sw}"'
                        f' stroke-dasharray="{pct*circ:.1f} {circ:.1f}"'
                        f' stroke-dashoffset="-{off:.1f}"'
                        f' transform="rotate(-90 {cx} {cy})"/>')
            o2 = o_pct * circ
            o3 = o2 + w_pct * circ
            return (f'<svg width="144" height="144">'
                    f'{arc(o_pct,"#22c55e",0)}{arc(w_pct,"#f97316",o2)}{arc(e_pct,"#ef4444",o3)}'
                    f'<text x="{cx}" y="{cy-4}" text-anchor="middle" font-size="20"'
                    f' font-weight="bold" fill="#1e293b">{total:,}</text>'
                    f'<text x="{cx}" y="{cy+15}" text-anchor="middle" font-size="10"'
                    f' fill="#64748b">총 로그</text></svg>')

        # ── unique 값 목록 (검색 탭 드롭다운) ───────────────────
        all_sev   = json.dumps(sorted(sev_count.keys(),  key=lambda x: _SEV_ORDER.index(x) if x in _SEV_ORDER else 99), ensure_ascii=False)
        all_hosts = json.dumps(sorted(host_count.keys()), ensure_ascii=False)
        all_facs  = json.dumps(sorted(fac_count.keys()),  ensure_ascii=False)
        all_evts  = json.dumps(sorted(evt_count.keys()),  ensure_ascii=False)
        all_files = json.dumps(sorted({e.get('source_file','') for e in data} - {''}), ensure_ascii=False)

        # ── TOP-N 이슈 메시지 패턴 ───────────────────────────────
        top_mnemonics = sorted(mnemonic_count.items(), key=lambda x: -x[1])[:20]
        mnem_rows = "".join(
            f'<tr><td class="mono">{_html.escape(k)}</td>'
            f'<td style="text-align:right;font-weight:700;color:#ef4444">{v:,}</td></tr>'
            for k, v in top_mnemonics
        ) or "<tr><td colspan='2' class='empty'>없음</td></tr>"

        html_doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>로그 분석 보고서 — {gen_time}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Malgun Gothic',Consolas,sans-serif;background:#f1f5f9;color:#1e293b;font-size:13px}}
/* ── 헤더 ── */
.hdr{{background:#1e293b;color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3)}}
.hdr h1{{font-size:17px;font-weight:700;letter-spacing:.3px}}
.hdr .meta{{font-size:11px;color:#94a3b8;text-align:right;line-height:1.6}}
/* ── 탭 바 ── */
.tabbar{{background:#fff;border-bottom:2px solid #e2e8f0;display:flex;gap:0;padding:0 20px;position:sticky;top:49px;z-index:90}}
.tabn{{padding:11px 20px;cursor:pointer;font-size:13px;font-weight:600;color:#64748b;border-bottom:3px solid transparent;margin-bottom:-2px;transition:all .15s;user-select:none}}
.tabn:hover{{color:#3b82f6}}
.tabn.active{{color:#3b82f6;border-bottom-color:#3b82f6}}
/* ── 탭 콘텐츠 ── */
.tabcontent{{display:none;padding:20px 24px}}
.tabcontent.active{{display:block}}
/* ── 카드 ── */
.card{{background:#fff;border-radius:10px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:16px}}
.card h2{{font-size:13px;font-weight:700;color:#334155;padding-bottom:8px;border-bottom:2px solid #f1f5f9;margin-bottom:14px}}
/* ── 그리드 ── */
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:16px}}
/* ── KPI ── */
.kpi{{text-align:center;padding:16px}}
.kpi-n{{font-size:34px;font-weight:800;line-height:1.1}}
.kpi-l{{font-size:11px;color:#64748b;margin-top:5px}}
/* ── 바 차트 ── */
.brow{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.blabel{{width:150px;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0;color:#334155}}
.btrack{{flex:1;background:#e2e8f0;border-radius:4px;height:16px;overflow:hidden}}
.bfill{{height:16px;border-radius:4px;min-width:4px;transition:width .3s}}
.bval{{width:46px;text-align:right;font-size:11px;color:#64748b;flex-shrink:0}}
/* ── 테이블 ── */
table{{width:100%;border-collapse:collapse}}
th{{background:#f8fafc;padding:7px 10px;text-align:left;border-bottom:2px solid #e2e8f0;font-size:11px;font-weight:700;color:#475569;position:sticky;top:0;cursor:pointer;user-select:none;white-space:nowrap}}
th:hover{{background:#f1f5f9}}
th.sort-asc::after{{content:" ▲"}}
th.sort-desc::after{{content:" ▼"}}
td{{padding:5px 10px;border-bottom:1px solid #f1f5f9;font-size:11px;vertical-align:top}}
tr:hover td{{background:#f8fafc}}
.mono{{font-family:Consolas,monospace;font-size:11px}}
.empty{{color:#94a3b8;font-size:12px;padding:8px 0}}
/* ── 심각도 배지 ── */
.badge{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:700;color:#fff;white-space:nowrap}}
/* ── 검색 바 ── */
.sbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px;background:#f8fafc;border-radius:8px;padding:12px 14px}}
.sbar input,.sbar select{{height:30px;border:1px solid #e2e8f0;border-radius:6px;padding:0 10px;font-size:12px;background:#fff;color:#1e293b;outline:none}}
.sbar input{{flex:1;min-width:160px}}
.sbar select{{min-width:130px}}
.sbar button{{height:30px;padding:0 16px;border:none;border-radius:6px;background:#3b82f6;color:#fff;font-size:12px;font-weight:700;cursor:pointer}}
.sbar button:hover{{background:#2563eb}}
.sbar .cnt{{font-size:12px;color:#3b82f6;font-weight:700;white-space:nowrap}}
/* ── 페이지네이션 ── */
.pager{{display:flex;gap:6px;align-items:center;justify-content:center;padding:10px 0}}
.pager button{{height:28px;min-width:32px;padding:0 10px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;font-size:12px}}
.pager button:hover{{background:#f1f5f9}}
.pager button.cur{{background:#3b82f6;color:#fff;border-color:#3b82f6;font-weight:700}}
.pager .pginfo{{font-size:12px;color:#64748b}}
/* ── 상세 패널 ── */
#detail-panel{{background:#1e293b;color:#e2e8f0;font-family:Consolas,monospace;font-size:11px;border-radius:8px;padding:14px;margin-top:10px;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow:auto;display:none}}
/* ── 색상 ── */
.red{{color:#ef4444}} .orange{{color:#f97316}} .green{{color:#22c55e}} .blue{{color:#3b82f6}} .purple{{color:#8b5cf6}}
.footer{{text-align:center;color:#94a3b8;font-size:11px;padding:20px 0 30px}}
</style>
</head>
<body>

<!-- 헤더 -->
<div class="hdr">
  <h1>📋 네트워크 장비 로그 분석 보고서</h1>
  <div class="meta">생성: {gen_time} &nbsp;|&nbsp; 파일 {len(self.current_files)}개<br>
    {_html.escape(file_list[:120]) + ("..." if len(file_list)>120 else "")}
  </div>
</div>
{"" if not truncated else f'<div style="background:#fef3c7;border-bottom:2px solid #fbbf24;padding:7px 28px;font-size:12px;color:#92400e">⚠️ {truncated_note}</div>'}

<!-- 탭 바 -->
<div class="tabbar">
  <div class="tabn active" onclick="switchTab(0)">📊 대시보드</div>
  <div class="tabn" onclick="switchTab(1)">📋 전체 로그</div>
  <div class="tabn" onclick="switchTab(2)">🔍 검색 / 필터</div>
  <div class="tabn" onclick="switchTab(3)">⚠️ 오류 분석</div>
</div>

<!-- ════════════════ TAB 0: 대시보드 ════════════════ -->
<div class="tabcontent active" id="tab0">

  <!-- KPI -->
  <div class="g4" style="margin-top:4px">
    <div class="card kpi"><div class="kpi-n blue">{total:,}</div><div class="kpi-l">전체 로그</div></div>
    <div class="card kpi"><div class="kpi-n red">{error_cnt:,}</div><div class="kpi-l">ERROR 이상</div></div>
    <div class="card kpi"><div class="kpi-n orange">{warn_cnt:,}</div><div class="kpi-l">WARNING</div></div>
    <div class="card kpi"><div class="kpi-n green">{info_cnt:,}</div><div class="kpi-l">INFO</div></div>
  </div>
  <div class="g4">
    <div class="card kpi"><div class="kpi-n purple">{len(host_count):,}</div><div class="kpi-l">호스트 수</div></div>
    <div class="card kpi"><div class="kpi-n" style="color:#0ea5e9">{len(fac_count):,}</div><div class="kpi-l">Facility 종류</div></div>
    <div class="card kpi"><div class="kpi-n" style="color:#10b981">{len(evt_count):,}</div><div class="kpi-l">감지 이벤트 유형</div></div>
    <div class="card kpi"><div class="kpi-n" style="color:#f59e0b">{len(self.current_files):,}</div><div class="kpi-l">분석 파일 수</div></div>
  </div>

  <!-- 분석 파일 목록 -->
  {"" if len(self.current_files) <= 1 else f'''<div class="card" style="margin-bottom:16px">
    <h2>📁 분석 파일 목록 ({len(self.current_files)}개)</h2>
    <div style="display:flex;flex-wrap:wrap;gap:8px">
      {"".join(
          f'<span style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;'
          f'padding:4px 10px;font-size:11px;font-family:Consolas">'
          f'{_html.escape(os.path.basename(fp))}</span>'
          for fp in self.current_files
      )}
    </div>
  </div>'''}

  <!-- 심각도 + 도넛 -->
  <div class="g2">
    <div class="card">
      <h2>심각도 분포</h2>
      {sev_bars_html()}
    </div>
    <div class="card" style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px">
      <h2 style="align-self:flex-start;width:100%">심각도 비율</h2>
      {donut_svg()}
      <div style="display:flex;gap:14px;font-size:11px;flex-wrap:wrap;justify-content:center">
        <span><span class="red">●</span> ERROR+ &nbsp;<b>{error_cnt:,}</b></span>
        <span><span class="orange">●</span> WARNING &nbsp;<b>{warn_cnt:,}</b></span>
        <span><span class="green">●</span> 나머지 &nbsp;<b>{total-error_cnt-warn_cnt:,}</b></span>
      </div>
    </div>
  </div>

  <!-- 이벤트 / Facility / 호스트 -->
  <div class="g3">
    <div class="card"><h2>이벤트 유형 TOP 15</h2>{bar_rows(evt_count, 15, "#8b5cf6")}</div>
    <div class="card"><h2>Facility TOP 15</h2>{bar_rows(fac_count, 15, "#0ea5e9")}</div>
    <div class="card"><h2>호스트별 TOP 15</h2>{bar_rows(host_count, 15, "#10b981") if host_count else "<p class='empty'>호스트 정보 없음</p>"}</div>
  </div>

</div><!-- /tab0 -->

<!-- ════════════════ TAB 1: 전체 로그 ════════════════ -->
<div class="tabcontent" id="tab1">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">
    <span id="all-cnt" class="blue" style="font-weight:700;font-size:13px"></span>
    <select id="all-sev" onchange="renderAll()" style="height:28px;border:1px solid #e2e8f0;border-radius:6px;padding:0 8px;font-size:12px">
      <option value="">전체 심각도</option>
    </select>
    <select id="all-host" onchange="renderAll()" style="height:28px;border:1px solid #e2e8f0;border-radius:6px;padding:0 8px;font-size:12px">
      <option value="">전체 호스트</option>
    </select>
    <select id="all-file" onchange="renderAll()" style="height:28px;border:1px solid #e2e8f0;border-radius:6px;padding:0 8px;font-size:12px">
      <option value="">전체 파일</option>
    </select>
    <span style="font-size:11px;color:#94a3b8">행 클릭 → 상세 보기</span>
  </div>
  <div style="overflow-x:auto">
  <table id="all-table">
    <thead><tr>
      <th onclick="sortAll(0)" style="width:150px">시간</th>
      <th onclick="sortAll(1)" style="width:80px">심각도</th>
      <th onclick="sortAll(2)" style="width:120px">Facility</th>
      <th onclick="sortAll(3)" style="width:100px">호스트</th>
      <th>메시지</th>
      <th onclick="sortAll(5)" style="width:110px">이벤트</th>
      <th onclick="sortAll(6)" style="width:100px">파일</th>
    </tr></thead>
    <tbody id="all-body"></tbody>
  </table>
  </div>
  <div class="pager" id="all-pager"></div>
  <div id="detail-panel"></div>
</div><!-- /tab1 -->

<!-- ════════════════ TAB 2: 검색 ════════════════ -->
<div class="tabcontent" id="tab2">
  <div class="sbar">
    <input type="text" id="s-kw" placeholder="🔍 키워드, IP, 메시지 검색..." oninput="runSearch()">
    <select id="s-sev" onchange="runSearch()"><option value="">전체 심각도</option></select>
    <select id="s-host" onchange="runSearch()"><option value="">전체 호스트</option></select>
    <select id="s-fac" onchange="runSearch()"><option value="">전체 Facility</option></select>
    <select id="s-evt" onchange="runSearch()"><option value="">전체 이벤트</option></select>
    <select id="s-file" onchange="runSearch()"><option value="">전체 파일</option></select>
    <button onclick="clearSearch()">초기화</button>
    <span class="cnt" id="s-cnt">0 건</span>
  </div>
  <div style="overflow-x:auto">
  <table id="s-table">
    <thead><tr>
      <th style="width:150px">시간</th>
      <th style="width:80px">심각도</th>
      <th style="width:120px">Facility</th>
      <th style="width:100px">호스트</th>
      <th>메시지</th>
      <th style="width:110px">이벤트</th>
      <th style="width:100px">파일</th>
    </tr></thead>
    <tbody id="s-body"></tbody>
  </table>
  </div>
  <div class="pager" id="s-pager"></div>
  <div id="s-detail-panel" style="background:#1e293b;color:#e2e8f0;font-family:Consolas,monospace;font-size:11px;border-radius:8px;padding:14px;margin-top:10px;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow:auto;display:none"></div>
</div><!-- /tab2 -->

<!-- ════════════════ TAB 3: 오류 분석 ════════════════ -->
<div class="tabcontent" id="tab3">
  <div class="g2">
    <div class="card">
      <h2>심각도별 집계</h2>
      <table>
        <tr><th>심각도</th><th style="text-align:right">건수</th><th style="text-align:right">비율</th></tr>
        {"".join(
            f'<tr><td><span class="badge" style="background:{SEV_MAP.get(s,"#94a3b8")}">{s}</span></td>'
            f'<td style="text-align:right;font-weight:700">{sev_count.get(s,0):,}</td>'
            f'<td style="text-align:right;color:#64748b">{sev_count.get(s,0)/total*100:.1f}%</td></tr>'
            for s in _SEV_ORDER if sev_count.get(s,0)
        )}
      </table>
    </div>
    <div class="card">
      <h2>⚠️ 빈도 높은 경보 Mnemonic TOP 20</h2>
      <table>
        <tr><th>Mnemonic</th><th style="text-align:right">건수</th></tr>
        {mnem_rows}
      </table>
    </div>
  </div>
  <div class="g2">
    <div class="card">
      <h2>Facility별 집계 (전체)</h2>
      {bar_rows(fac_count, 30, "#0ea5e9")}
    </div>
    <div class="card">
      <h2>호스트별 집계 (전체)</h2>
      {bar_rows(host_count, 30, "#10b981") if host_count else "<p class='empty'>호스트 정보 없음</p>"}
    </div>
  </div>
  <div class="card">
    <h2>ERROR 이상 로그 — 전체 목록</h2>
    <div style="overflow-x:auto">
    <table id="err-table">
      <thead><tr>
        <th style="width:150px">시간</th><th style="width:80px">심각도</th>
        <th style="width:100px">호스트</th><th style="width:130px">Facility</th><th>메시지</th>
      </tr></thead>
      <tbody id="err-body"></tbody>
    </table>
    </div>
    <div class="pager" id="err-pager"></div>
    <div id="err-detail-panel" style="background:#1e293b;color:#e2e8f0;font-family:Consolas,monospace;font-size:11px;border-radius:8px;padding:14px;margin-top:10px;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow:auto;display:none"></div>
  </div>
</div><!-- /tab3 -->

<div class="footer">Network Automation v6.1 &nbsp;|&nbsp; {gen_time}</div>

<script>
const LOGS = {rows_json};
const SEV_COLOR = {json.dumps(SEV_MAP)};
const SEV_ORDER = {json.dumps(_SEV_ORDER)};
const ALL_SEV   = {all_sev};
const ALL_HOSTS = {all_hosts};
const ALL_FACS  = {all_facs};
const ALL_EVTS  = {all_evts};
const ALL_FILES = {all_files};

// ── 탭 전환 ──────────────────────────────────────────
function switchTab(n) {{
  document.querySelectorAll('.tabn').forEach((el,i) => el.classList.toggle('active', i===n));
  document.querySelectorAll('.tabcontent').forEach((el,i) => el.classList.toggle('active', i===n));
  if (n===1 && !allInited) initAll();
  if (n===2 && !searchInited) initSearch();
  if (n===3 && !errInited) initErr();
}}

// ── 배지 HTML ─────────────────────────────────────────
function badge(sev) {{
  const c = SEV_COLOR[sev] || '#94a3b8';
  return `<span class="badge" style="background:${{c}}">${{sev}}</span>`;
}}

// ── 페이지네이션 헬퍼 ─────────────────────────────────
function makePager(containerId, page, total, pageSize, cb) {{
  const el = document.getElementById(containerId);
  const pages = Math.ceil(total / pageSize) || 1;
  if (pages <= 1) {{ el.innerHTML=''; return; }}
  let html = '';
  if (page > 0) html += `<button onclick="${{cb}}(${{page-1}})">‹</button>`;
  const start = Math.max(0, page-3), end = Math.min(pages-1, page+3);
  if (start>0) html += `<button onclick="${{cb}}(0)">1</button>${{start>1?'<span>…</span>':''}}`;
  for (let i=start;i<=end;i++) html += `<button class="${{i===page?'cur':''}}" onclick="${{cb}}(${{i}})">${{i+1}}</button>`;
  if (end<pages-1) html += `${{end<pages-2?'<span>…</span>':''}}<button onclick="${{cb}}(${{pages-1}})">${{pages}}</button>`;
  if (page < pages-1) html += `<button onclick="${{cb}}(${{page+1}})">›</button>`;
  html += `<span class="pginfo">&nbsp;${{page+1}} / ${{pages}} 페이지 (${{total.toLocaleString()}}건)</span>`;
  el.innerHTML = html;
}}

// ── 행 렌더 공통 ──────────────────────────────────────
function rowHtml(r, idx, detailPanelId) {{
  const c = SEV_COLOR[r.sev] || '#94a3b8';
  const rowBg = r.sev==='ERROR'||r.sev==='CRITICAL'||r.sev==='ALERT'||r.sev==='EMERGENCY'
    ? '#fff5f5' : r.sev==='WARNING' ? '#fffbeb' : '';
  return `<tr style="background:${{rowBg}};cursor:pointer" onclick="showDetail(${{JSON.stringify(r)}},'${{detailPanelId}}')">
    <td class="mono" style="color:#64748b;white-space:nowrap">${{r.ts}}</td>
    <td>${{badge(r.sev)}}</td>
    <td class="mono" style="color:#6d28d9">${{r.fac}}</td>
    <td style="color:#0f172a">${{r.host}}</td>
    <td style="max-width:500px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{r.msg.replace(/"/g,'&quot;')}}">${{r.msg}}</td>
    <td style="color:#7c3aed;font-size:10px">${{r.evt}}</td>
    <td style="color:#64748b;font-size:10px">${{r.src}}</td>
  </tr>`;
}}

function showDetail(r, panelId) {{
  const p = document.getElementById(panelId);
  if (p.dataset.last === JSON.stringify(r)) {{ p.style.display = p.style.display==='none'?'block':'none'; return; }}
  p.dataset.last = JSON.stringify(r);
  p.style.display = 'block';
  p.textContent = [
    '시간     : ' + r.ts,
    '심각도   : ' + r.sev,
    'Facility : ' + r.fac,
    '호스트   : ' + r.host,
    '이벤트   : ' + r.evt,
    '파일     : ' + r.src,
    '',
    '── 메시지 ──────────────────────────────────────────',
    r.msg,
    '',
    '── 원본 라인 ────────────────────────────────────────',
    r.raw,
  ].join('\\n');
}}

// ════════════════ TAB 1: 전체 로그 ════════════════════
let allInited=false, allFiltered=LOGS, allPage=0, allSortCol=-1, allSortAsc=true;
const ALL_PAGE_SIZE = 200;

function initAll() {{
  allInited = true;
  populate('all-sev', ALL_SEV);
  populate('all-host', ALL_HOSTS);
  populate('all-file', ALL_FILES);
  allFiltered = LOGS;
  renderAll();
}}

function populate(id, arr) {{
  const sel = document.getElementById(id);
  arr.forEach(v => {{ const o=document.createElement('option'); o.value=o.text=v; sel.appendChild(o); }});
}}

function renderAll() {{
  const sev  = document.getElementById('all-sev').value;
  const host = document.getElementById('all-host').value;
  const file = document.getElementById('all-file').value;
  allFiltered = LOGS.filter(r =>
    (!sev  || r.sev===sev) &&
    (!host || r.host===host) &&
    (!file || r.src===file)
  );
  allPage = 0;
  renderAllPage(0);
}}

function renderAllPage(pg) {{
  allPage = pg;
  const slice = allFiltered.slice(pg*ALL_PAGE_SIZE, (pg+1)*ALL_PAGE_SIZE);
  document.getElementById('all-body').innerHTML = slice.map((r,i) => rowHtml(r,i,'detail-panel')).join('');
  document.getElementById('all-cnt').textContent = allFiltered.length.toLocaleString() + ' 건';
  makePager('all-pager', pg, allFiltered.length, ALL_PAGE_SIZE, 'renderAllPage');
}}

let allSortState={{}};
function sortAll(col) {{
  const ths = document.querySelectorAll('#all-table th');
  const asc = allSortState[col] === undefined ? true : !allSortState[col];
  allSortState = {{}}; allSortState[col] = asc;
  ths.forEach((th,i)=>{{ th.classList.remove('sort-asc','sort-desc'); if(i===col) th.classList.add(asc?'sort-asc':'sort-desc'); }});
  const keys = ['ts','sev','fac','host','msg','evt','src'];
  const k = keys[col];
  allFiltered.sort((a,b) => {{
    const va=a[k]||'', vb=b[k]||'';
    if(k==='sev') {{ const ia=SEV_ORDER.indexOf(va),ib=SEV_ORDER.indexOf(vb); return asc?ia-ib:ib-ia; }}
    return asc ? va.localeCompare(vb) : vb.localeCompare(va);
  }});
  renderAllPage(0);
}}

// ════════════════ TAB 2: 검색 ════════════════════════
let searchInited=false, searchResult=[], searchPage=0;
const SEARCH_PAGE_SIZE = 200;

function initSearch() {{
  searchInited = true;
  populate('s-sev',  ALL_SEV);
  populate('s-host', ALL_HOSTS);
  populate('s-fac',  ALL_FACS);
  populate('s-evt',  ALL_EVTS);
  populate('s-file', ALL_FILES);
  runSearch();
}}

function runSearch() {{
  const kw   = document.getElementById('s-kw').value.toLowerCase();
  const sev  = document.getElementById('s-sev').value;
  const host = document.getElementById('s-host').value;
  const fac  = document.getElementById('s-fac').value;
  const evt  = document.getElementById('s-evt').value;
  const file = document.getElementById('s-file').value;
  searchResult = LOGS.filter(r =>
    (!kw   || r.raw.toLowerCase().includes(kw) || r.msg.toLowerCase().includes(kw)) &&
    (!sev  || r.sev===sev) &&
    (!host || r.host===host) &&
    (!fac  || r.fac===fac) &&
    (!evt  || r.evt===evt) &&
    (!file || r.src===file)
  );
  searchPage = 0;
  renderSearchPage(0);
}}

function clearSearch() {{
  ['s-kw'].forEach(id => document.getElementById(id).value='');
  ['s-sev','s-host','s-fac','s-evt','s-file'].forEach(id => document.getElementById(id).selectedIndex=0);
  runSearch();
}}

function renderSearchPage(pg) {{
  searchPage = pg;
  const slice = searchResult.slice(pg*SEARCH_PAGE_SIZE, (pg+1)*SEARCH_PAGE_SIZE);
  document.getElementById('s-body').innerHTML = slice.map((r,i) => rowHtml(r,i,'s-detail-panel')).join('');
  document.getElementById('s-cnt').textContent = searchResult.length.toLocaleString() + ' 건';
  makePager('s-pager', pg, searchResult.length, SEARCH_PAGE_SIZE, 'renderSearchPage');
}}

// ════════════════ TAB 3: 오류 분석 ════════════════════
let errInited=false, errData=[], errPage=0;
const ERR_PAGE_SIZE = 200;

function initErr() {{
  errInited = true;
  errData = LOGS.filter(r => ['EMERGENCY','ALERT','CRITICAL','ERROR'].includes(r.sev));
  renderErrPage(0);
}}

function renderErrPage(pg) {{
  errPage = pg;
  const slice = errData.slice(pg*ERR_PAGE_SIZE, (pg+1)*ERR_PAGE_SIZE);
  document.getElementById('err-body').innerHTML = slice.map((r,i) => {{
    const c = SEV_COLOR[r.sev]||'#ef4444';
    return `<tr style="background:#fff5f5;cursor:pointer" onclick="showDetail(${{JSON.stringify(r)}},'err-detail-panel')">
      <td class="mono" style="color:#64748b;white-space:nowrap">${{r.ts}}</td>
      <td>${{badge(r.sev)}}</td>
      <td style="color:#0f172a">${{r.host}}</td>
      <td class="mono" style="color:#6d28d9">${{r.fac}}</td>
      <td style="max-width:600px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{r.msg.replace(/"/g,'&quot;')}}">${{r.msg}}</td>
    </tr>`;
  }}).join('');
  makePager('err-pager', pg, errData.length, ERR_PAGE_SIZE, 'renderErrPage');
}}
</script>
</body></html>"""

        default = f"log_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path, _ = QFileDialog.getSaveFileName(
            self, "HTML 보고서 저장", default, "HTML (*.html)"
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_doc)
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", str(e))
            return
        reply = QMessageBox.question(
            self, "저장 완료",
            f"저장 완료:\n{path}\n\n브라우저에서 열겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import sys
            if sys.platform == "win32":
                os.startfile(path)
            else:
                webbrowser.open(f'file:///{path}')
        self.lbl_status.setText(f"HTML 보고서 저장: {path}")

    # ── 내보내기 ─────────────────────────────────────────────────
    def _export(self):
        if not self.filtered_data:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "내보내기", f"log_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "CSV (*.csv);;텍스트 (*.txt)"
        )
        if not path:
            return
        try:
            if path.endswith('.csv'):
                import csv
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f)
                    w.writerow(['시간','심각도','Facility','호스트','메시지','이벤트','파일'])
                    for e in self.filtered_data:
                        w.writerow([
                            e.get('timestamp',''), e.get('severity',''),
                            e.get('facility_name',''), e.get('hostname',''),
                            e.get('message',''), e.get('event_type',''),
                            e.get('source_file',''),
                        ])
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    for e in self.filtered_data:
                        f.write(e.get('raw','') + '\n')
            QMessageBox.information(self, "완료", f"저장되었습니다:\n{path}")
        except Exception as ex:
            QMessageBox.warning(self, "오류", str(ex))
