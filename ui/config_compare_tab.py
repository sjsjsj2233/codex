"""
IOS 업그레이드 전/후 설정 비교 탭
"""

import os
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QGroupBox, QSplitter, QTabWidget, QComboBox,
    QCheckBox, QFileDialog, QMessageBox, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.config_diff import ConfigComparator, DiffType


# ───────────────────────────── 워커 ─────────────────────────────

class CompareWorker(QThread):
    completed = pyqtSignal(list, object)
    error     = pyqtSignal(str)

    def __init__(self, config1, config2, ignore_noise, ignore_case):
        super().__init__()
        self.config1      = config1
        self.config2      = config2
        self.ignore_noise = ignore_noise
        self.ignore_case  = ignore_case

    def run(self):
        try:
            c = ConfigComparator()
            c.ignore_whitespace = self.ignore_noise
            c.ignore_comments   = self.ignore_noise
            c.case_sensitive    = not self.ignore_case
            diff_lines, summary = c.compare_strings(self.config1, self.config2)
            self.completed.emit(diff_lines, summary)
        except Exception as e:
            self.error.emit(str(e))


# ───────────────────────────── 메인 탭 ──────────────────────────

class ConfigCompareTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.diff_lines = []
        self.summary    = None
        self.comparator = ConfigComparator()
        self.worker     = None
        self._c1        = ""
        self._c2        = ""
        self._build_ui()

    # ═══════════════════════════ UI 구성 ════════════════════════

    def _build_ui(self):
        from ui.report_tab import _Header
        self.setObjectName('configCompareTab')
        self.setStyleSheet('#configCompareTab { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header(
            '설정 비교',
            '업그레이드 전/후 설정 변경사항 비교 · 분석 · 보고서',
            '#0f172a', '#7c3aed',
        ))

        body = QWidget()
        body.setObjectName('configCompareBody')
        body.setStyleSheet('#configCompareBody { background: transparent; }')
        bv = QVBoxLayout(body)
        bv.setContentsMargins(6, 6, 6, 6)
        bv.setSpacing(4)

        # 상하 스플리터
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(5)

        # ── 상단: 입력 영역 ──
        top = QWidget()
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(3)

        lr = QSplitter(Qt.Horizontal)
        lr.setHandleWidth(6)
        self.before_panel = self._input_panel("업그레이드 전  (Before)")
        self.after_panel  = self._input_panel("업그레이드 후  (After)")
        lr.addWidget(self.before_panel)
        lr.addWidget(self.after_panel)
        lr.setSizes([500, 500])
        top_lay.addWidget(lr)
        top_lay.addWidget(self._options_bar())

        splitter.addWidget(top)

        # ── 하단: 결과 영역 ──
        splitter.addWidget(self._result_area())
        splitter.setSizes([320, 400])

        bv.addWidget(splitter)
        root.addWidget(body, 1)

    # ─────────────────────── 입력 패널 ──────────────────────────

    def _input_panel(self, title):
        group = QGroupBox(title)
        lay   = QVBoxLayout(group)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(3)

        # 버튼 행
        bar = QHBoxLayout()
        bar.setSpacing(4)

        combo = QComboBox()
        combo.addItems([
            "show running-config",
            "show version",
            "show interfaces",
            "show ip route",
            "show ip bgp summary",
            "기타",
        ])
        combo.setFixedWidth(152)
        combo.setFixedHeight(24)

        open_btn  = self._small_btn("파일 열기")
        paste_btn = self._small_btn("클립보드")
        clear_btn = self._small_btn("지우기",  danger=True)

        bar.addWidget(combo)
        bar.addStretch()
        bar.addWidget(open_btn)
        bar.addWidget(paste_btn)
        bar.addWidget(clear_btn)
        lay.addLayout(bar)

        # 텍스트 영역
        text = QTextEdit()
        text.setFont(QFont("Consolas", 9))
        text.setPlaceholderText(
            "여기에 명령어 출력을 붙여넣으세요.\n\n"
            "예)  show running-config\n"
            "     show version"
        )
        lay.addWidget(text)

        # 줄 수
        info = QLabel("0줄")
        info.setAlignment(Qt.AlignRight)
        info.setStyleSheet("font-size:10px; color:#94a3b8;")
        lay.addWidget(info)

        text.textChanged.connect(
            lambda: info.setText(
                f"{len([l for l in text.toPlainText().splitlines() if l.strip()])}줄"
            )
        )
        open_btn.clicked.connect(lambda: self._open_file(text))
        paste_btn.clicked.connect(lambda: self._paste(text))
        clear_btn.clicked.connect(text.clear)

        group.text_edit         = text
        group.config_type_combo = combo
        return group

    def _small_btn(self, text, danger=False):
        btn = QPushButton(text)
        btn.setFixedHeight(24)
        if danger:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444; color: white;
                    border: none; border-radius: 4px;
                    padding: 0 10px; font-size: 11px; font-weight: 600;
                }
                QPushButton:hover { background-color: #dc2626; }
            """)
        return btn

    # ─────────────────────── 옵션 바 ────────────────────────────

    def _options_bar(self):
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(10)

        self.ignore_noise_cb = QCheckBox("주석·빈줄 무시")
        self.ignore_noise_cb.setChecked(True)
        self.ignore_case_cb  = QCheckBox("대소문자 무시")
        self.ignore_case_cb.setChecked(True)

        lay.addWidget(self.ignore_noise_cb)
        lay.addWidget(self.ignore_case_cb)
        lay.addStretch()

        self.clear_btn = QPushButton("결과 초기화")
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #64748b; color: white;
                border: none; border-radius: 4px;
                padding: 0 14px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.clear_btn.clicked.connect(self._clear)

        self.compare_btn = QPushButton("▶  비교 분석")
        self.compare_btn.setFixedHeight(28)
        self.compare_btn.setMinimumWidth(110)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white;
                border: none; border-radius: 4px;
                padding: 0 16px; font-size: 11px; font-weight: 700;
            }
            QPushButton:hover    { background-color: #1d4ed8; }
            QPushButton:pressed  { background-color: #1e40af; }
            QPushButton:disabled { background-color: #93c5fd; }
        """)
        self.compare_btn.clicked.connect(self._run)

        lay.addWidget(self.clear_btn)
        lay.addSpacing(4)
        lay.addWidget(self.compare_btn)
        return w

    # ─────────────────────── 결과 영역 ──────────────────────────

    def _result_area(self):
        self.result_tabs = QTabWidget()

        self.result_tabs.addTab(self._tab_summary(),   "📊  요약")
        self.result_tabs.addTab(self._tab_diff(),      "🔍  변경사항")
        self.result_tabs.addTab(self._tab_important(), "⚠️  중요 변경사항")
        self.result_tabs.addTab(self._tab_export(),    "💾  저장")

        return self.result_tabs

    # ── 요약 탭 ─────────────────────────────────────────────────

    def _tab_summary(self):
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # 안내 라벨 (초기 표시)
        self.ph = QLabel(
            "비교 분석을 실행하면 결과가 여기에 표시됩니다.\n\n"
            "① 업그레이드 전/후 설정을 각 패널에 붙여넣으세요.\n"
            "② [▶ 비교 분석] 버튼을 클릭하세요."
        )
        self.ph.setAlignment(Qt.AlignCenter)
        self.ph.setStyleSheet("color:#94a3b8; font-size:11px;")
        lay.addWidget(self.ph)

        # 실제 결과 (초기 숨김)
        self.summary_box = QWidget()
        self.summary_box.setVisible(False)
        sb = QVBoxLayout(self.summary_box)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(6)

        # 통계 카드 4개
        cards = QHBoxLayout()
        cards.setSpacing(6)
        self.card_add  = self._stat_card("추가된 줄", "0", "#16a34a", "#f0fdf4")
        self.card_del  = self._stat_card("삭제된 줄", "0", "#dc2626", "#fef2f2")
        self.card_tot  = self._stat_card("총 변경",   "0", "#2563eb", "#eff6ff")
        self.card_imp  = self._stat_card("주요 변경", "0", "#d97706", "#fffbeb")
        for c in (self.card_add, self.card_del, self.card_tot, self.card_imp):
            cards.addWidget(c)
        sb.addLayout(cards)

        # 파일 정보 한 줄
        self.info_lbl = QLabel()
        self.info_lbl.setStyleSheet("font-size:10px; color:#64748b;")
        sb.addWidget(self.info_lbl)

        # 비교 유형
        self.type_lbl = QLabel()
        self.type_lbl.setStyleSheet(
            "font-size:10px; color:#374151; background:#f8fafc; "
            "border:1px solid #e2e8f0; border-radius:4px; padding:4px 8px;"
        )
        sb.addWidget(self.type_lbl)

        # 주요 변경사항 미리보기
        imp_group = QGroupBox("주요 변경사항 미리보기 (최대 20개)")
        ig = QVBoxLayout(imp_group)
        ig.setContentsMargins(4, 4, 4, 4)
        self.imp_preview = QTextEdit()
        self.imp_preview.setReadOnly(True)
        self.imp_preview.setFont(QFont("Consolas", 9))
        self.imp_preview.setFixedHeight(120)
        ig.addWidget(self.imp_preview)
        sb.addWidget(imp_group)

        lay.addWidget(self.summary_box)
        return w

    def _stat_card(self, label, value, fg, bg):
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background:{bg}; border:1px solid {fg}44; "
            f"border-radius:6px; }}"
        )
        f.setMinimumHeight(70)
        lay = QVBoxLayout(f)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(0)
        lay.setContentsMargins(8, 6, 8, 6)

        v = QLabel(value)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet(
            f"color:{fg}; font-size:22px; font-weight:700; "
            "border:none; background:transparent;"
        )
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color:{fg}; font-size:10px; border:none; background:transparent;"
        )
        lay.addWidget(v)
        lay.addWidget(lbl)

        f.value_label = v
        return f

    # ── Diff 탭 ──────────────────────────────────────────────────

    def _tab_diff(self):
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(3)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.ctx_cb = QCheckBox("전후 컨텍스트 줄 표시")
        self.ctx_cb.setChecked(False)
        self.ctx_cb.stateChanged.connect(self._refresh_diff)
        self.diff_stat = QLabel("")
        self.diff_stat.setStyleSheet("font-size:10px; color:#64748b;")
        bar.addWidget(self.ctx_cb)
        bar.addStretch()
        bar.addWidget(self.diff_stat)
        lay.addLayout(bar)

        self.diff_browser = QTextBrowser()
        self.diff_browser.setFont(QFont("Consolas", 9))
        self.diff_browser.setOpenLinks(False)
        lay.addWidget(self.diff_browser)
        return w

    # ── 중요 변경사항 탭 ─────────────────────────────────────────

    def _tab_important(self):
        self.imp_table = QTableWidget()
        self.imp_table.setColumnCount(3)
        self.imp_table.setHorizontalHeaderLabels(["구분", "줄#", "설정 내용"])
        h = self.imp_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.imp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.imp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.imp_table.setAlternatingRowColors(True)
        self.imp_table.setFont(QFont("Consolas", 9))
        return self.imp_table

    # ── 저장 탭 ──────────────────────────────────────────────────

    def _tab_export(self):
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        note = QLabel(
            "비교 완료 후 보고서를 파일로 저장할 수 있습니다.\n"
            "• HTML — 브라우저에서 열 수 있는 색상 코딩 보고서\n"
            "• TXT  — 메모장 등 일반 텍스트 편집기용"
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "font-size:11px; color:#374151; background:#f8fafc; "
            "border:1px solid #e2e8f0; border-radius:4px; padding:8px 10px;"
        )
        lay.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.save_html_btn = QPushButton("💾  HTML 보고서 저장")
        self.save_html_btn.setFixedHeight(32)
        self.save_html_btn.setStyleSheet("""
            QPushButton {
                background:#059669; color:white; border:none;
                border-radius:4px; padding:0 16px;
                font-size:11px; font-weight:700;
            }
            QPushButton:hover    { background:#047857; }
            QPushButton:disabled { background:#9ca3af; }
        """)
        self.save_html_btn.clicked.connect(self._save_html)
        self.save_html_btn.setEnabled(False)

        self.save_txt_btn = QPushButton("📄  TXT 보고서 저장")
        self.save_txt_btn.setFixedHeight(32)
        self.save_txt_btn.setStyleSheet("""
            QPushButton {
                background:#6366f1; color:white; border:none;
                border-radius:4px; padding:0 16px;
                font-size:11px; font-weight:700;
            }
            QPushButton:hover    { background:#4f46e5; }
            QPushButton:disabled { background:#9ca3af; }
        """)
        self.save_txt_btn.clicked.connect(self._save_txt)
        self.save_txt_btn.setEnabled(False)

        btn_row.addWidget(self.save_html_btn)
        btn_row.addWidget(self.save_txt_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        lay.addStretch()
        return w

    # ═══════════════════════ 이벤트 핸들러 ═════════════════════

    def _open_file(self, text_edit):
        path, _ = QFileDialog.getOpenFileName(
            self, "설정 파일 열기", "",
            "텍스트 파일 (*.txt *.log *.cfg *.conf);;모든 파일 (*.*)"
        )
        if not path:
            return
        for enc in ("utf-8", "euc-kr", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    text_edit.setPlainText(f.read())
                return
            except (UnicodeDecodeError, LookupError):
                continue
        QMessageBox.warning(self, "열기 실패", "파일 인코딩을 인식할 수 없습니다.")

    def _paste(self, text_edit):
        text = QApplication.clipboard().text()
        if text:
            text_edit.setPlainText(text)
        else:
            QMessageBox.information(self, "알림", "클립보드에 텍스트가 없습니다.")

    def _run(self):
        c1 = self.before_panel.text_edit.toPlainText().strip()
        c2 = self.after_panel.text_edit.toPlainText().strip()
        if not c1:
            QMessageBox.warning(self, "입력 오류", "업그레이드 전(Before) 설정을 입력하세요.")
            return
        if not c2:
            QMessageBox.warning(self, "입력 오류", "업그레이드 후(After) 설정을 입력하세요.")
            return

        self._c1 = c1
        self._c2 = c2
        self.compare_btn.setEnabled(False)
        self.compare_btn.setText("분석 중…")

        self.worker = CompareWorker(
            c1, c2,
            self.ignore_noise_cb.isChecked(),
            self.ignore_case_cb.isChecked()
        )
        self.worker.completed.connect(self._on_done)
        self.worker.error.connect(self._on_err)
        self.worker.start()

    def _on_done(self, diff_lines, summary):
        self.diff_lines = diff_lines
        self.summary    = summary

        self._update_summary(summary)
        self._render_diff(diff_lines)
        self._update_imp_table(diff_lines)

        self.save_html_btn.setEnabled(True)
        self.save_txt_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.compare_btn.setText("▶  비교 분석")

        total = summary.added_count + summary.removed_count
        if total == 0:
            QMessageBox.information(self, "비교 결과",
                                    "변경된 설정이 없습니다.\n두 설정이 동일합니다.")
            self.result_tabs.setCurrentIndex(0)
        else:
            self.result_tabs.setCurrentIndex(1)

    def _on_err(self, msg):
        QMessageBox.critical(self, "오류", f"비교 중 오류:\n{msg}")
        self.compare_btn.setEnabled(True)
        self.compare_btn.setText("▶  비교 분석")

    def _clear(self):
        self.diff_lines = []
        self.summary    = None
        self._c1        = ""
        self._c2        = ""
        self.diff_browser.clear()
        self.diff_stat.setText("")
        self.imp_table.setRowCount(0)
        self.result_tabs.setTabText(2, "⚠️  중요 변경사항")
        self.ph.setVisible(True)
        self.summary_box.setVisible(False)
        self.save_html_btn.setEnabled(False)
        self.save_txt_btn.setEnabled(False)

    def _refresh_diff(self):
        if self.diff_lines:
            self._render_diff(self.diff_lines)

    # ═══════════════════════ 결과 업데이트 ═════════════════════

    def _update_summary(self, s):
        self.ph.setVisible(False)
        self.summary_box.setVisible(True)

        total = s.added_count + s.removed_count
        self.card_add.value_label.setText(str(s.added_count))
        self.card_del.value_label.setText(str(s.removed_count))
        self.card_tot.value_label.setText(str(total))
        self.card_imp.value_label.setText(str(len(s.important_changes)))

        self.info_lbl.setText(
            f"이전: {s.total_lines_old}줄  /  "
            f"현재: {s.total_lines_new}줄  /  "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        bt = self.before_panel.config_type_combo.currentText()
        at = self.after_panel.config_type_combo.currentText()
        self.type_lbl.setText(f"Before: {bt}   →   After: {at}")

        self.imp_preview.setPlainText(
            "\n".join(s.important_changes[:20]) if s.important_changes
            else "(주요 변경사항 없음)"
        )

    def _render_diff(self, diff_lines):
        added   = sum(1 for l in diff_lines if l.diff_type == DiffType.ADDED)
        removed = sum(1 for l in diff_lines if l.diff_type == DiffType.REMOVED)
        self.diff_stat.setText(f"+{added}  −{removed}  총 {added+removed}줄 변경")

        if not diff_lines:
            self.diff_browser.setHtml(
                "<div style='text-align:center;padding:40px;color:#94a3b8;"
                "font-family:맑은 고딕,sans-serif;font-size:11px;'>"
                "변경된 내용이 없습니다.</div>"
            )
            return

        # 비교기 옵션 동기화 후 side-by-side HTML 생성
        self.comparator.ignore_whitespace = self.ignore_noise_cb.isChecked()
        self.comparator.ignore_comments   = self.ignore_noise_cb.isChecked()
        self.comparator.case_sensitive    = not self.ignore_case_cb.isChecked()

        show_ctx   = self.ctx_cb.isChecked()
        import difflib, re

        lines1 = self._c1.splitlines()
        lines2 = self._c2.splitlines()
        if self.comparator.ignore_whitespace or self.comparator.ignore_comments:
            lines1 = [l for l in lines1 if self.comparator._preprocess_line(l).strip()]
            lines2 = [l for l in lines2 if self.comparator._preprocess_line(l).strip()]

        rows = self.comparator._make_sidebyside_rows(lines1, lines2)

        CSS = (
            "* {box-sizing:border-box;margin:0;padding:0;}"
            "body{font-family:Consolas,'Courier New',monospace;font-size:9pt;"
            "background:#f1f5f9;}"
            "table{border-collapse:collapse;width:100%;background:#fff;"
            "table-layout:fixed;}"
            "col.ln{width:38px;} col.code{width:calc(50% - 38px);}"
            "thead tr{background:#334155;color:#f1f5f9;}"
            "th{padding:5px 8px;font-size:9pt;font-weight:700;text-align:left;}"
            ".ln{width:38px;text-align:right;padding:1px 5px;"
            "color:#94a3b8;background:#f8fafc;border-right:1px solid #e2e8f0;"
            "user-select:none;font-size:8pt;vertical-align:top;}"
            "td.lc,td.rc{padding:1px 6px;white-space:pre-wrap;word-break:break-all;"
            "vertical-align:top;}"
            "tr.eq td.lc,tr.eq td.rc{background:#fff;}"
            "td.del{background:#fef2f2;}"
            "td.add{background:#f0fdf4;}"
            "td.empty{background:#f8fafc;}"
            "span.hi{background:#fca5a5;border-radius:2px;padding:0 1px;}"
            "td.add span.hi{background:#86efac;}"
            "tbody tr:hover td{filter:brightness(0.97);}"
        )

        html = [
            "<!DOCTYPE html><html><head><meta charset='UTF-8'>",
            f"<style>{CSS}</style></head><body>",
            "<table><colgroup>",
            "<col class='ln'><col class='code'><col class='ln'><col class='code'>",
            "</colgroup><thead><tr>",
            "<th>#</th><th>Before (업그레이드 전)</th>",
            "<th>#</th><th>After (업그레이드 후)</th>",
            "</tr></thead><tbody>",
        ]

        ln1 = ln2 = 0
        for left, right, rtype in rows:
            if rtype == 'equal' and not show_ctx:
                if left  is not None: ln1 += 1
                if right is not None: ln2 += 1
                continue

            if left  is not None: ln1 += 1
            if right is not None: ln2 += 1
            ls = str(ln1) if left  is not None else ''
            rs = str(ln2) if right is not None else ''

            def esc(t):
                return (t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                        if t else '')

            if rtype == 'equal':
                lh = esc(left); rh = esc(right)
                html.append(
                    f'<tr class="eq">'
                    f'<td class="ln">{ls}</td><td class="lc">{lh}</td>'
                    f'<td class="ln">{rs}</td><td class="rc">{rh}</td>'
                    f'</tr>'
                )
            elif rtype == 'replace':
                if left is not None and right is not None:
                    lh, rh = self.comparator._inline_diff_html(left, right)
                    html.append(
                        f'<tr class="ch">'
                        f'<td class="ln">{ls}</td><td class="lc del">{lh}</td>'
                        f'<td class="ln">{rs}</td><td class="rc add">{rh}</td>'
                        f'</tr>'
                    )
                elif left is not None:
                    html.append(
                        f'<tr class="ch">'
                        f'<td class="ln">{ls}</td><td class="lc del">{esc(left)}</td>'
                        f'<td class="ln"></td><td class="rc empty"></td>'
                        f'</tr>'
                    )
                else:
                    html.append(
                        f'<tr class="ch">'
                        f'<td class="ln"></td><td class="lc empty"></td>'
                        f'<td class="ln">{rs}</td><td class="rc add">{esc(right)}</td>'
                        f'</tr>'
                    )
            elif rtype == 'delete':
                html.append(
                    f'<tr class="ch">'
                    f'<td class="ln">{ls}</td><td class="lc del">{esc(left)}</td>'
                    f'<td class="ln"></td><td class="rc empty"></td>'
                    f'</tr>'
                )
            elif rtype == 'insert':
                html.append(
                    f'<tr class="ch">'
                    f'<td class="ln"></td><td class="lc empty"></td>'
                    f'<td class="ln">{rs}</td><td class="rc add">{esc(right)}</td>'
                    f'</tr>'
                )

        html.append("</tbody></table></body></html>")
        self.diff_browser.setHtml("".join(html))

    def _update_imp_table(self, diff_lines):
        rows = [l for l in diff_lines if l.is_important]
        self.imp_table.setRowCount(len(rows))

        for i, line in enumerate(rows):
            is_add = line.diff_type == DiffType.ADDED

            t = QTableWidgetItem("추가" if is_add else "삭제")
            t.setBackground(QColor("#f0fdf4" if is_add else "#fef2f2"))
            t.setForeground(QColor("#15803d" if is_add else "#b91c1c"))
            t.setTextAlignment(Qt.AlignCenter)

            n = line.line_number_new if is_add else line.line_number_old
            num = QTableWidgetItem(str(n) if n > 0 else "-")
            num.setTextAlignment(Qt.AlignCenter)

            self.imp_table.setItem(i, 0, t)
            self.imp_table.setItem(i, 1, num)
            self.imp_table.setItem(i, 2, QTableWidgetItem(line.content.strip()))

        label = f"⚠️  중요 변경사항 ({len(rows)})" if rows else "⚠️  중요 변경사항"
        self.result_tabs.setTabText(2, label)

    # ═══════════════════════ 파일 저장 ═════════════════════════

    def _save_html(self):
        if self.summary is None:
            QMessageBox.warning(self, "저장 오류", "먼저 비교 분석을 실행하세요.")
            return
        default = f"config_diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path, _ = QFileDialog.getSaveFileName(
            self, "HTML 저장", default, "HTML (*.html)"
        )
        if not path:
            return
        try:
            bt = self.before_panel.config_type_combo.currentText()
            self.comparator.ignore_whitespace = self.ignore_noise_cb.isChecked()
            self.comparator.ignore_comments   = self.ignore_noise_cb.isChecked()
            self.comparator.case_sensitive    = not self.ignore_case_cb.isChecked()
            html = self.comparator.generate_sidebyside_html(
                self._c1, self._c2,
                f"설정 비교: {bt} (Before → After)"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            reply = QMessageBox.question(
                self, "저장 완료",
                f"저장 완료:\n{path}\n\n브라우저에서 열겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes and sys.platform == "win32":
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", str(e))

    def _save_txt(self):
        if self.summary is None:
            QMessageBox.warning(self, "저장 오류", "먼저 비교 분석을 실행하세요.")
            return
        default = f"config_diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "TXT 저장", default, "텍스트 (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.comparator.generate_text_report(
                    self.diff_lines, self.summary
                ))
            QMessageBox.information(self, "저장 완료", f"저장 완료:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", str(e))
