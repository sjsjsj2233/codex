"""
Palo Alto (PAN-OS) 점검 탭
작업 전(Before) / 작업 후(After) show 명령어 출력 파일을 각각 등록하고
같은 순서로 짝지어 비교한다. 체크리스트 요약이 아니라, 파일에 실제로 있는
명령어를 그대로 따라가며 원본 출력을 줄 단위로 diff한다.
"""
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QSplitter, QTextEdit, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QApplication,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from core.paloalto_checklist import (
    compare_files_full, to_tsv_lines, save_xlsx_lines, PALOALTO_INSPECTION_COMMANDS,
)
from core.config_diff import ConfigComparator, DiffType


class PaloAltoTab:
    def __init__(self, parent=None):
        self._widget = _PaloAltoWidget(parent)

    def as_widget(self):
        return self._widget


class _FileListBox(QGroupBox):
    """Before/After 공용 파일 목록 박스"""
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        v = QVBoxLayout(self)
        v.setSpacing(6)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ 파일 추가")
        self.btn_add.setFixedHeight(26)
        self.btn_del = QPushButton("− 선택 제거")
        self.btn_del.setFixedHeight(26)
        self.btn_clr = QPushButton("전체 제거")
        self.btn_clr.setFixedHeight(26)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_del)
        btn_row.addWidget(self.btn_clr)
        btn_row.addStretch()
        v.addLayout(btn_row)

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Consolas", 9))
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setFixedHeight(120)
        v.addWidget(self.list_widget)

        self.btn_add.clicked.connect(self._add_files)
        self.btn_del.clicked.connect(self._remove_selected)
        self.btn_clr.clicked.connect(self.list_widget.clear)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "show 명령어 파일 선택", "",
            "텍스트 파일 (*.txt *.log *.cfg);;모든 파일 (*)"
        )
        existing = self.paths()
        for p in paths:
            if p not in existing:
                item = QListWidgetItem(f"  {os.path.basename(p)}")
                item.setData(Qt.UserRole, p)
                item.setToolTip(p)
                self.list_widget.addItem(item)

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def paths(self):
        return [self.list_widget.item(i).data(Qt.UserRole)
                for i in range(self.list_widget.count())]


_STATUS_LABEL = {
    'changed':   '변경됨',
    'unchanged': '변경없음',
    'added':     '신규(작업 후)',
    'removed':   '삭제(작업 후)',
    'unparsed':  '파싱 실패',
}
_STATUS_COLOR = {
    'changed':   '#fecaca',
    'added':     '#fed7aa',
    'removed':   '#fed7aa',
    'unparsed':  '#e5e7eb',
}


class _PaloAltoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._diff_results = []   # List[(hostname, List[CommandDiffResult])]
        self._row_results   = []  # 표의 각 행 -> CommandDiffResult (헤더 행은 None)
        self._comparator = ConfigComparator()
        self._comparator.case_sensitive = True
        self._build_ui()

    def _build_ui(self):
        from ui.report_tab import _Header
        self.setObjectName('paloaltoWidget')
        self.setStyleSheet('#paloaltoWidget { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header(
            'Palo Alto 점검',
            'OS 업그레이드 전/후 명령어별 원본 출력 비교 · 엑셀 붙여넣기용 결과 생성',
            '#7f1d1d', '#dc2626',
        ))

        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(10, 10, 10, 10)
        bv.setSpacing(8)
        root.addWidget(body, 1)

        splitter = QSplitter(Qt.Horizontal)

        # ── 좌측: Before/After 파일 목록 + 명령어 안내 ──────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 6, 0)
        lv.setSpacing(8)

        self.before_box = _FileListBox("📁 작업 전(Before) 파일")
        self.after_box  = _FileListBox("📁 작업 후(After) 파일")
        lv.addWidget(self.before_box)
        lv.addWidget(self.after_box)

        hint = QLabel(
            "※ Before/After는 같은 순서(같은 장비)로 추가하세요. "
            "예: Before 1번째 = SW-01 작업전, After 1번째 = SW-01 작업후\n"
            "※ 비교는 체크리스트가 아니라 파일에 실제로 있는 명령어를 그대로 따라갑니다 — "
            "점검 명령어가 바뀌어도 그대로 비교됩니다."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748b;font-size:10px")
        lv.addWidget(hint)

        cmd_box = QGroupBox("📋 점검 명령어 (참고용 — 장비에서 실행 후 파일 저장)")
        cmd_v = QVBoxLayout(cmd_box)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setFont(QFont("Consolas", 9))
        te.setPlainText(PALOALTO_INSPECTION_COMMANDS)
        te.setFixedHeight(160)
        te.setStyleSheet(
            "QTextEdit{background:#0f172a;color:#a5f3fc;"
            "border-radius:4px;padding:6px;border:none}"
        )
        cmd_v.addWidget(te)

        btn_copy_cmd = QPushButton("📋 명령어 복사")
        btn_copy_cmd.setFixedHeight(26)
        btn_copy_cmd.setStyleSheet(
            "QPushButton{background:#334155;color:white;border-radius:4px;font-size:10px;}"
            "QPushButton:hover{background:#475569;}"
        )
        btn_copy_cmd.clicked.connect(lambda: self._copy_text(PALOALTO_INSPECTION_COMMANDS, "명령어가 클립보드에 복사되었습니다"))
        cmd_v.addWidget(btn_copy_cmd)

        lv.addWidget(cmd_box, 1)

        # ── 우측: 명령어별 결과 표 + 상세 diff 뷰 ────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 0, 0, 0)
        rv.setSpacing(8)

        action_row = QHBoxLayout()
        self.btn_compare = QPushButton("🔍 비교 실행")
        self.btn_compare.setFixedHeight(32)
        self.btn_compare.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.btn_compare.setStyleSheet("background:#dc2626;color:#fff;border-radius:6px")
        self.btn_compare.clicked.connect(self._run_compare)

        self.btn_copy_excel = QPushButton("📊 엑셀로 복사")
        self.btn_copy_excel.setFixedHeight(32)
        self.btn_copy_excel.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.btn_copy_excel.setStyleSheet("background:#0891b2;color:#fff;border-radius:6px")
        self.btn_copy_excel.clicked.connect(self._copy_result_to_excel)

        self.btn_save_excel = QPushButton("💾 엑셀 파일로 저장 (다름 자동 색칠)")
        self.btn_save_excel.setFixedHeight(32)
        self.btn_save_excel.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.btn_save_excel.setStyleSheet("background:#16a34a;color:#fff;border-radius:6px")
        self.btn_save_excel.clicked.connect(self._save_result_to_xlsx)

        action_row.addWidget(self.btn_compare)
        action_row.addWidget(self.btn_copy_excel)
        action_row.addWidget(self.btn_save_excel)
        action_row.addStretch()
        rv.addLayout(action_row)

        result_splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['명령어', '상태', '변경'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        result_splitter.addWidget(self.table)

        self.detail_view = QTextBrowser()
        self.detail_view.setFont(QFont("Consolas", 9))
        self.detail_view.setHtml(
            "<div style='color:#94a3b8;padding:20px;font-family:맑은 고딕,sans-serif;'>"
            "표에서 명령어 행을 클릭하면 실제로 달라진 내용이 여기에 나타납니다.</div>"
        )
        result_splitter.addWidget(self.detail_view)
        result_splitter.setSizes([260, 360])

        rv.addWidget(result_splitter, 1)

        self.lbl_status = QLabel("Before/After 파일을 추가한 뒤 비교 실행을 누르세요")
        self.lbl_status.setStyleSheet("color:#64748b;font-size:11px")
        rv.addWidget(self.lbl_status)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([340, 640])
        bv.addWidget(splitter, 1)

    # ── 동작 ──────────────────────────────────────────────────────
    def _copy_text(self, text, msg):
        QApplication.clipboard().setText(text)
        self.lbl_status.setText(msg)

    def _run_compare(self):
        before_paths = self.before_box.paths()
        after_paths  = self.after_box.paths()

        if not before_paths or not after_paths:
            QMessageBox.warning(self, "파일 없음", "Before/After 파일을 각각 최소 1개 이상 추가하세요.")
            return
        if len(before_paths) != len(after_paths):
            QMessageBox.warning(
                self, "개수 불일치",
                f"Before({len(before_paths)}개)와 After({len(after_paths)}개) 파일 개수가 다릅니다.\n"
                "같은 순서로 장비를 짝지어 추가해주세요."
            )
            return

        try:
            self._diff_results = []
            for bp, ap in zip(before_paths, after_paths):
                hostname, results = compare_files_full(bp, ap)
                self._diff_results.append((hostname, results))
        except Exception as ex:
            QMessageBox.critical(self, "비교 오류", f"파일 파싱/비교 중 오류가 발생했습니다:\n{ex}")
            return

        self._render_table()

    def _render_table(self):
        self.table.setRowCount(0)
        self._row_results = []
        self.detail_view.setHtml(
            "<div style='color:#94a3b8;padding:20px;font-family:맑은 고딕,sans-serif;'>"
            "표에서 명령어 행을 클릭하면 실제로 달라진 내용이 여기에 나타납니다.</div>"
        )

        changed_count = 0
        total_count = 0
        for hostname, results in self._diff_results:
            r = self.table.rowCount()
            self.table.insertRow(r)
            host_item = QTableWidgetItem(f"■ {hostname}")
            host_item.setFont(QFont("맑은 고딕", 9, QFont.Bold))
            self.table.setItem(r, 0, host_item)
            for c in range(1, 3):
                self.table.setItem(r, c, QTableWidgetItem(""))
            for c in range(3):
                self.table.item(r, c).setBackground(QColor('#e2e8f0'))
            self._row_results.append(None)

            for cd in results:
                total_count += 1
                r = self.table.rowCount()
                self.table.insertRow(r)
                self._row_results.append(cd)

                change_txt = ''
                if cd.status == 'changed':
                    change_txt = f"+{cd.added_count} / -{cd.removed_count}"
                    changed_count += 1

                cmd_item = QTableWidgetItem(cd.command)
                status_item = QTableWidgetItem(_STATUS_LABEL.get(cd.status, cd.status))
                change_item = QTableWidgetItem(change_txt)

                bg = _STATUS_COLOR.get(cd.status)
                for c, it in enumerate((cmd_item, status_item, change_item)):
                    if bg:
                        it.setBackground(QColor(bg))
                    self.table.setItem(r, c, it)

        self.lbl_status.setText(f"비교 완료 — 총 {total_count}개 명령어, 변경됨 {changed_count}건")

    def _on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx >= len(self._row_results):
            return
        cd = self._row_results[idx]
        if cd is None:
            return  # 장비 구분 헤더 행
        self._show_detail(cd)

    def _show_detail(self, cd):
        if cd.status == 'unchanged':
            self.detail_view.setHtml(
                "<div style='color:#16a34a;padding:20px;font-family:맑은 고딕,sans-serif;'>"
                f"'{self._escape(cd.command)}' — 작업 전/후 출력이 동일합니다 (변경 없음).</div>"
            )
            return
        if cd.status == 'added':
            self.detail_view.setHtml(
                "<div style='padding:12px;font-family:Consolas,monospace;font-size:9pt;'>"
                "<div style='color:#c2410c;font-weight:bold;margin-bottom:8px;'>"
                "작업 후에만 존재하는 명령어입니다 (작업 전 파일에는 없음)</div>"
                f"<pre style='white-space:pre-wrap'>{self._escape(cd.after_text)}</pre></div>"
            )
            return
        if cd.status == 'removed':
            self.detail_view.setHtml(
                "<div style='padding:12px;font-family:Consolas,monospace;font-size:9pt;'>"
                "<div style='color:#c2410c;font-weight:bold;margin-bottom:8px;'>"
                "작업 전에만 존재하는 명령어입니다 (작업 후 결과에서 사라짐)</div>"
                f"<pre style='white-space:pre-wrap'>{self._escape(cd.before_text)}</pre></div>"
            )
            return
        # changed / unparsed → 사이드바이사이드 diff
        self.detail_view.setHtml(self._sidebyside_html(cd.before_text, cd.after_text))

    def _escape(self, text):
        return (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def _sidebyside_html(self, before_text, after_text):
        """core/config_diff.py의 ConfigComparator를 그대로 재사용한 사이드바이사이드 렌더링
        (ui/config_compare_tab.py의 _render_diff()와 동일한 스타일)."""
        lines1 = before_text.splitlines()
        lines2 = after_text.splitlines()
        rows = self._comparator._make_sidebyside_rows(lines1, lines2)

        CSS = (
            "* {box-sizing:border-box;margin:0;padding:0;}"
            "body{font-family:Consolas,'Courier New',monospace;font-size:9pt;background:#f1f5f9;}"
            "table{border-collapse:collapse;width:100%;background:#fff;table-layout:fixed;}"
            "col.ln{width:38px;} col.code{width:calc(50% - 38px);}"
            "thead tr{background:#334155;color:#f1f5f9;}"
            "th{padding:5px 8px;font-size:9pt;font-weight:700;text-align:left;}"
            ".ln{width:38px;text-align:right;padding:1px 5px;color:#94a3b8;background:#f8fafc;"
            "border-right:1px solid #e2e8f0;user-select:none;font-size:8pt;vertical-align:top;}"
            "td.lc,td.rc{padding:1px 6px;white-space:pre-wrap;word-break:break-all;vertical-align:top;}"
            "tr.eq td.lc,tr.eq td.rc{background:#fff;}"
            "td.del{background:#fef2f2;} td.add{background:#f0fdf4;} td.empty{background:#f8fafc;}"
            "span.hi{background:#fca5a5;border-radius:2px;padding:0 1px;}"
            "td.add span.hi{background:#86efac;}"
        )

        html = [
            "<!DOCTYPE html><html><head><meta charset='UTF-8'>",
            f"<style>{CSS}</style></head><body>",
            "<table><colgroup>",
            "<col class='ln'><col class='code'><col class='ln'><col class='code'>",
            "</colgroup><thead><tr>",
            "<th>#</th><th>작업 전 (Before)</th><th>#</th><th>작업 후 (After)</th>",
            "</tr></thead><tbody>",
        ]

        ln1 = ln2 = 0
        for left, right, rtype in rows:
            if left is not None:
                ln1 += 1
            if right is not None:
                ln2 += 1
            ls = str(ln1) if left is not None else ''
            rs = str(ln2) if right is not None else ''

            if rtype == 'equal':
                lh, rh = self._escape(left), self._escape(right)
                html.append(
                    f'<tr class="eq"><td class="ln">{ls}</td><td class="lc">{lh}</td>'
                    f'<td class="ln">{rs}</td><td class="rc">{rh}</td></tr>'
                )
            elif rtype == 'replace':
                if left is not None and right is not None:
                    lh, rh = self._comparator._inline_diff_html(left, right)
                    html.append(
                        f'<tr><td class="ln">{ls}</td><td class="lc del">{lh}</td>'
                        f'<td class="ln">{rs}</td><td class="rc add">{rh}</td></tr>'
                    )
                elif left is not None:
                    html.append(
                        f'<tr><td class="ln">{ls}</td><td class="lc del">{self._escape(left)}</td>'
                        f'<td class="ln"></td><td class="rc empty"></td></tr>'
                    )
                else:
                    html.append(
                        f'<tr><td class="ln"></td><td class="lc empty"></td>'
                        f'<td class="ln">{rs}</td><td class="rc add">{self._escape(right)}</td></tr>'
                    )
            elif rtype == 'delete':
                html.append(
                    f'<tr><td class="ln">{ls}</td><td class="lc del">{self._escape(left)}</td>'
                    f'<td class="ln"></td><td class="rc empty"></td></tr>'
                )
            elif rtype == 'insert':
                html.append(
                    f'<tr><td class="ln"></td><td class="lc empty"></td>'
                    f'<td class="ln">{rs}</td><td class="rc add">{self._escape(right)}</td></tr>'
                )

        html.append("</tbody></table></body></html>")
        return ''.join(html)

    def _copy_result_to_excel(self):
        if not self._diff_results:
            QMessageBox.warning(self, "결과 없음", "먼저 비교 실행을 눌러 결과를 생성하세요.")
            return
        tsv = to_tsv_lines(self._diff_results)
        QApplication.clipboard().setText(tsv)
        self.lbl_status.setText("줄 단위 비교 결과가 클립보드에 복사되었습니다 — 엑셀에 Ctrl+V로 붙여넣으세요")

    def _save_result_to_xlsx(self):
        if not self._diff_results:
            QMessageBox.warning(self, "결과 없음", "먼저 비교 실행을 눌러 결과를 생성하세요.")
            return
        default_name = "팔로알토_비교결과.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "엑셀 파일로 저장", default_name, "Excel 파일 (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        try:
            save_xlsx_lines(self._diff_results, path)
        except ImportError:
            QMessageBox.warning(self, "openpyxl 없음", "openpyxl 라이브러리가 없어 엑셀 파일을 만들 수 없습니다.")
            return
        except Exception as ex:
            QMessageBox.critical(self, "저장 오류", f"엑셀 파일 저장 중 오류가 발생했습니다:\n{ex}")
            return
        self.lbl_status.setText(f"저장 완료 — '다름' 행이 자동으로 색칠된 상태입니다: {path}")
        QMessageBox.information(self, "저장 완료", f"엑셀 파일이 저장되었습니다:\n{path}\n\n'다름' 행은 빨간색으로 자동 표시됩니다.")
