"""
보고서 탭
"""
import os
import csv
import re
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QCheckBox, QPushButton, QFileDialog, QMessageBox, QSizePolicy,
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QBrush, QLinearGradient, QPen,
)
from PyQt5.QtCore import Qt

from openpyxl import Workbook


# ── 헤더 ─────────────────────────────────────────────────────────────────────
class _Header(QWidget):
    def __init__(self, title, subtitle, c0, c1, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self._title    = title
        self._subtitle = subtitle
        self._c0, self._c1 = c0, c1

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor(self._c0))
        g.setColorAt(1.0, QColor(self._c1))
        p.fillRect(self.rect(), QBrush(g))
        p.setOpacity(0.07)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 80, -30, 160, 160)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor('#f8fafc')))
        p.setFont(QFont('맑은 고딕', 15, QFont.Bold))
        p.drawText(28, 30, self._title)
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(30, 50, self._subtitle)
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
        'color:#94a3b8;background:transparent;border:none;letter-spacing:1px'
    )
    return l


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet('QFrame{background:#f1f5f9;border:none;max-height:1px}')
    return f


_SS_CB = (
    'QCheckBox{color:#475569;background:transparent;border:none;font-size:9pt}'
    'QCheckBox::indicator{width:15px;height:15px;border-radius:3px;'
    '  border:1px solid #cbd5e1;background:#f8fafc}'
    'QCheckBox::indicator:checked{background:#3b82f6;border-color:#3b82f6}'
)


# ── 메인 보고서 클래스 ─────────────────────────────────────────────────────────
class EnhancedInspectionReportGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.device_data = []
        self.init_ui()

    # ── UI 구성 ───────────────────────────────────────────────────────────────
    def init_ui(self):
        self.setObjectName('iosXEReport')
        self.setStyleSheet('#iosXEReport { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header(
            'IOS-XE 보고서',
            'Cisco IOS / IOS-XE 장비 데이터 수집 · 분석 · 내보내기',
            '#0f172a', '#1d4ed8',
        ))

        body = QWidget()
        body.setObjectName('iosXEBody')
        body.setStyleSheet('#iosXEBody { background: transparent; }')
        bv = QHBoxLayout(body)
        bv.setContentsMargins(18, 16, 18, 16)
        bv.setSpacing(12)

        bv.addWidget(self._build_left())
        bv.addWidget(self._build_right(), 1)

        root.addWidget(body, 1)

    def _build_left(self):
        card = _card()
        card.setFixedWidth(210)
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        # 파일 불러오기
        v.addWidget(_sec('파일 불러오기'))

        load_btn = QPushButton('파일 열기')
        load_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        load_btn.setFixedHeight(36)
        load_btn.setStyleSheet(
            'QPushButton{background:#3b82f6;color:#fff;border:none;border-radius:8px}'
            'QPushButton:hover{background:#2563eb}'
        )
        load_btn.clicked.connect(self.load_txt_files)
        v.addWidget(load_btn)

        # 파일 카운트 배지
        self._count_frame = QFrame()
        self._count_frame.setFixedHeight(36)
        self._count_frame.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:7px;border:1px solid #e2e8f0}'
        )
        cf = QHBoxLayout(self._count_frame)
        cf.setContentsMargins(10, 0, 10, 0)
        self._dot_lbl = QLabel('●')
        self._dot_lbl.setFont(QFont('맑은 고딕', 10))
        self._dot_lbl.setStyleSheet('background:transparent;border:none;color:#cbd5e1')
        self.file_count_label = QLabel('로드된 파일: 0개')
        self.file_count_label.setFont(QFont('맑은 고딕', 9))
        self.file_count_label.setStyleSheet('background:transparent;border:none;color:#94a3b8')
        cf.addWidget(self._dot_lbl)
        cf.addWidget(self.file_count_label, 1)
        v.addWidget(self._count_frame)

        v.addWidget(_sep())

        # 출력 항목
        v.addWidget(_sec('출력 항목'))

        self.include_cpu = QCheckBox('CPU 사용률')
        self.include_cpu.setChecked(True)
        self.include_cpu.setFont(QFont('맑은 고딕', 9))
        self.include_cpu.setStyleSheet(_SS_CB)

        self.include_memory = QCheckBox('메모리 정보')
        self.include_memory.setChecked(True)
        self.include_memory.setFont(QFont('맑은 고딕', 9))
        self.include_memory.setStyleSheet(_SS_CB)

        self.include_uptime = QCheckBox('가동 시간')
        self.include_uptime.setChecked(True)
        self.include_uptime.setFont(QFont('맑은 고딕', 9))
        self.include_uptime.setStyleSheet(_SS_CB)

        for cb in (self.include_cpu, self.include_memory, self.include_uptime):
            v.addWidget(cb)

        v.addWidget(_sep())

        # 내보내기
        v.addWidget(_sec('내보내기'))

        excel_btn = QPushButton('Excel 저장')
        excel_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        excel_btn.setFixedHeight(34)
        excel_btn.setStyleSheet(
            'QPushButton{background:#10b981;color:#fff;border:none;border-radius:8px}'
            'QPushButton:hover{background:#059669}'
        )
        excel_btn.clicked.connect(self.save_to_excel)
        v.addWidget(excel_btn)

        csv_btn = QPushButton('CSV 저장')
        csv_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        csv_btn.setFixedHeight(34)
        csv_btn.setStyleSheet(
            'QPushButton{background:#10b981;color:#fff;border:none;border-radius:8px}'
            'QPushButton:hover{background:#059669}'
        )
        csv_btn.clicked.connect(self.save_to_csv)
        v.addWidget(csv_btn)

        v.addStretch()

        clear_btn = QPushButton('초기화')
        clear_btn.setFont(QFont('맑은 고딕', 9))
        clear_btn.setFixedHeight(30)
        clear_btn.setStyleSheet(
            'QPushButton{background:#fee2e2;color:#ef4444;border:1px solid #fca5a5;'
            '  border-radius:7px}'
            'QPushButton:hover{background:#fecaca}'
        )
        clear_btn.clicked.connect(self.clear_data)
        v.addWidget(clear_btn)

        return card

    def _build_right(self):
        card = _card()
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 테이블 상단 바
        bar = QFrame()
        bar.setFixedHeight(40)
        bar.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:10px 10px 0 0;'
            'border-bottom:1px solid #e2e8f0}'
        )
        barv = QHBoxLayout(bar)
        barv.setContentsMargins(16, 0, 16, 0)
        t = QLabel('장비 데이터')
        t.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        t.setStyleSheet('color:#1e293b;background:transparent;border:none')
        barv.addWidget(t)
        barv.addStretch()
        v.addWidget(bar)

        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(10)
        self.result_table.setHorizontalHeaderLabels([
            '파일명', '호스트명', '모델', 'IOS 버전', 'SW 버전',
            'CPU', '메모리 총량', '메모리 사용', '사용률', '가동시간',
        ])
        hdr = self.result_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        for i in range(3, 10):
            hdr.setSectionResizeMode(i, QHeaderView.Stretch)

        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setShowGrid(False)
        self.result_table.setFont(QFont('맑은 고딕', 9))
        self.result_table.horizontalHeader().setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self.result_table.setStyleSheet(
            'QTableWidget{background:#ffffff;border:none;outline:none}'
            'QTableWidget::item{padding:6px 10px;border-bottom:1px solid #f1f5f9}'
            'QTableWidget::item:selected{background:#dbeafe;color:#1e40af}'
            'QTableWidget::item:alternate{background:#f8fafc}'
            'QHeaderView::section{background:#f8fafc;color:#64748b;padding:8px 10px;'
            '  border:none;border-bottom:1px solid #e2e8f0;font-weight:bold}'
        )
        self.result_table.itemClicked.connect(self.show_device_details)
        v.addWidget(self.result_table, 1)

        # 상세 정보 바
        dbar = QFrame()
        dbar.setFixedHeight(34)
        dbar.setStyleSheet(
            'QFrame{background:#f8fafc;border-top:1px solid #e2e8f0;border-bottom:none;'
            'border-left:none;border-right:none}'
        )
        dbarv = QHBoxLayout(dbar)
        dbarv.setContentsMargins(16, 0, 16, 0)
        dt = QLabel('상세 정보')
        dt.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        dt.setStyleSheet('color:#64748b;background:transparent;border:none')
        dbarv.addWidget(dt)
        v.addWidget(dbar)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont('Consolas', 9))
        self.details_text.setFixedHeight(120)
        self.details_text.setPlaceholderText('장비를 선택하면 상세 정보가 표시됩니다...')
        self.details_text.setStyleSheet(
            'QTextEdit{background:#f8fafc;border:none;border-radius:0 0 10px 10px;'
            'padding:10px;color:#334155}'
        )
        v.addWidget(self.details_text)

        return card

    # ── 데이터 메서드 (기존 로직 동일) ────────────────────────────────────────
    def load_txt_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, '텍스트 파일 선택', '', 'Text Files (*.txt);;All Files (*)'
        )
        if not files:
            return
        self.details_text.append(f'[로드] {len(files)}개 파일')
        for file in files:
            self.details_text.append(f'  • {os.path.basename(file)}')
        self.parse_txt_files(files)
        n = len(self.device_data)
        self.file_count_label.setText(f'로드된 파일: {n}개')
        # 배지 업데이트
        self._dot_lbl.setStyleSheet('background:transparent;border:none;color:#3b82f6')
        self.file_count_label.setStyleSheet('background:transparent;border:none;color:#1e293b;font-size:9pt')
        self._count_frame.setStyleSheet(
            'QFrame{background:#eff6ff;border-radius:7px;border:1px solid #bfdbfe}'
        )
        logging.info(f'[INFO] 파일 로드: {len(files)}개')

    def parse_txt_files(self, files):
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                filename = os.path.splitext(os.path.basename(file))[0]
                run_hostname = self.parse_run_hostname(content)
                ios_version, sw_version, model = self.parse_show_version(content)
                total_mem, used_mem, free_mem, memory_usage = self.parse_memory(content)
                cpu_usage = self.parse_cpu(content)
                uptime = self.parse_uptime(content)
                device_info = {
                    'filename': filename, 'hostname': run_hostname,
                    'cpu': cpu_usage, 'memory_total': total_mem,
                    'memory_used': used_mem, 'memory_free': free_mem,
                    'memory_usage': memory_usage, 'uptime': uptime,
                    'ios_version': ios_version, 'sw_version': sw_version,
                    'model': model, 'raw_content': content,
                }
                self.device_data.append(device_info)
                self.add_device_to_table(device_info)
            except Exception as e:
                self.details_text.append(f'[오류] {os.path.basename(file)}: {e}')
                logging.error(f'[ERROR] 파싱 실패: {file} - {e}')

    def add_device_to_table(self, device):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setRowHeight(row, 38)
        items = [
            device['filename'], device['hostname'], device['model'],
            device['ios_version'], device['sw_version'], device['cpu'],
            str(device['memory_total']), str(device['memory_used']),
            device['memory_usage'], device['uptime'],
        ]
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFont(QFont('맑은 고딕', 9))
            self.result_table.setItem(row, col, item)

    def show_device_details(self, item):
        row = item.row()
        it = self.result_table.item(row, 0)
        if not it:
            return
        filename = it.text()
        device = next((d for d in self.device_data if d['filename'] == filename), None)
        if not device:
            return
        self.details_text.clear()
        self.details_text.append(f'━━━  {filename}  ━━━')
        self.details_text.append(f'호스트 : {device["hostname"]}')
        self.details_text.append(f'모델   : {device["model"]}')
        self.details_text.append(f'IOS    : {device["ios_version"]}')
        self.details_text.append(f'CPU    : {device["cpu"]}')
        self.details_text.append(f'메모리 : {device["memory_usage"]}')
        self.details_text.append(f'가동   : {device["uptime"]}')

    def clear_data(self):
        if not self.device_data:
            return
        reply = QMessageBox.question(
            self, '초기화', '모든 데이터를 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.device_data.clear()
            self.result_table.setRowCount(0)
            self.details_text.clear()
            self.file_count_label.setText('로드된 파일: 0개')
            self.file_count_label.setStyleSheet('background:transparent;border:none;color:#94a3b8')
            self._dot_lbl.setStyleSheet('background:transparent;border:none;color:#cbd5e1')
            self._count_frame.setStyleSheet(
                'QFrame{background:#f8fafc;border-radius:7px;border:1px solid #e2e8f0}'
            )

    def save_to_excel(self):
        if not self.device_data:
            QMessageBox.warning(self, '오류', '저장할 데이터가 없습니다.')
            return
        try:
            path, _ = QFileDialog.getSaveFileName(self, 'Excel 저장', 'Report.xlsx', 'Excel Files (*.xlsx)')
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = 'Report'
            headers = ['파일명', '호스트명', '모델', 'IOS', 'SW']
            if self.include_cpu.isChecked():
                headers.append('CPU')
            if self.include_memory.isChecked():
                headers.extend(['메모리', '사용', '여유', '사용률'])
            if self.include_uptime.isChecked():
                headers.append('가동시간')
            ws.append(headers)
            for d in self.device_data:
                row = [d['filename'], d['hostname'], d['model'], d['ios_version'], d['sw_version']]
                if self.include_cpu.isChecked():
                    row.append(d['cpu'])
                if self.include_memory.isChecked():
                    row.extend([d['memory_total'], d['memory_used'], d['memory_free'], d['memory_usage']])
                if self.include_uptime.isChecked():
                    row.append(d['uptime'])
                ws.append(row)
            wb.save(path)
            QMessageBox.information(self, '완료', f'저장 완료:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, '오류', f'저장 실패: {e}')

    def save_to_csv(self):
        if not self.device_data:
            QMessageBox.warning(self, '오류', '저장할 데이터가 없습니다.')
            return
        try:
            path, _ = QFileDialog.getSaveFileName(self, 'CSV 저장', 'Report.csv', 'CSV Files (*.csv)')
            if not path:
                return
            headers = ['파일명', '호스트명', '모델', 'IOS', 'SW']
            if self.include_cpu.isChecked():
                headers.append('CPU')
            if self.include_memory.isChecked():
                headers.extend(['메모리', '사용', '여유', '사용률'])
            if self.include_uptime.isChecked():
                headers.append('가동시간')
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(headers)
                for d in self.device_data:
                    row = [d['filename'], d['hostname'], d['model'], d['ios_version'], d['sw_version']]
                    if self.include_cpu.isChecked():
                        row.append(d['cpu'])
                    if self.include_memory.isChecked():
                        row.extend([d['memory_total'], d['memory_used'], d['memory_free'], d['memory_usage']])
                    if self.include_uptime.isChecked():
                        row.append(d['uptime'])
                    w.writerow(row)
            QMessageBox.information(self, '완료', f'저장 완료:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, '오류', f'저장 실패: {e}')

    # ── 파싱 메서드 (기존 그대로) ──────────────────────────────────────────────
    def parse_run_hostname(self, content):
        m = re.search(r'^hostname\s+(\S+)', content, re.MULTILINE)
        return m.group(1) if m else 'N/A'

    def parse_show_version(self, content):
        m = re.search(r'Version\s+([\d\.\(\)A-Z]+)', content)
        ios = m.group(1) if m else 'N/A'
        m2 = re.search(r'Model number\s+:\s+(\S+)', content, re.IGNORECASE)
        if m2:
            model = m2.group(1)
        else:
            m2 = re.search(r'\bC\d{4,}\b', content)
            model = m2.group(0) if m2 else 'N/A'
        return ios, ios, model

    def parse_memory(self, content):
        m = re.search(r'Processor Pool Total:\s+(\d+)\s+Used:\s+(\d+)\s+Free:\s+(\d+)', content)
        if m:
            t, u, f_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return t, u, f_, f'{round((u/t)*100, 1)}%'
        m = re.search(r'System memory\s+:\s+(\d+)K total,\s+(\d+)K used,\s+(\d+)K free', content)
        if m:
            t, u, f_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return t, u, f_, f'{round((u/t)*100, 1)}%'
        return 'N/A', 'N/A', 'N/A', 'N/A'

    def parse_cpu(self, content):
        m = re.search(r'CPU utilization for five seconds:.*?(\d+)%', content)
        return m.group(1) + '%' if m else 'N/A'

    def parse_uptime(self, content):
        m = re.search(r'uptime is (.+)', content)
        return m.group(1).strip() if m else 'N/A'


# ── Nexus 보고서 ──────────────────────────────────────────────────────────────
class EnhancedNexusReportGenerator(EnhancedInspectionReportGenerator):
    def __init__(self):
        super().__init__()
        # 헤더 교체
        self.result_table.setHorizontalHeaderLabels([
            '파일명', '호스트명', '모델', 'NX-OS', 'CPU',
            '메모리', '사용', '사용률', '가동시간', '재부팅',
        ])
        # 헤더 색상 재설정 (NX-OS 전용)
        self._update_header_color()

    def _update_header_color(self):
        # 부모의 헤더 위젯을 찾아서 색상만 변경
        for widget in self.findChildren(_Header):
            widget._title    = 'NX-OS 보고서'
            widget._subtitle = 'Cisco Nexus 장비 데이터 수집 · 분석 · 내보내기'
            widget._c0 = '#0f172a'
            widget._c1 = '#7c3aed'
            widget.update()
            break

    def parse_txt_files(self, files):
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                filename = os.path.splitext(os.path.basename(file))[0]
                hostname, nxos, model = self.parse_show_version_nexus(content)
                cpu, total_mem, used_mem, free_mem, mem_usage, uptime = self.parse_system_resources(content)
                reboot = self.parse_last_reboot(content)
                device_info = {
                    'filename': filename,
                    'hostname': hostname if hostname != 'N/A' else filename,
                    'cpu': cpu, 'memory_total': total_mem,
                    'memory_used': used_mem, 'memory_free': free_mem,
                    'memory_usage': mem_usage, 'uptime': uptime,
                    'nxos_version': nxos, 'model': model,
                    'last_reboot': reboot, 'raw_content': content,
                }
                self.device_data.append(device_info)
                self.add_device_to_table_nexus(device_info)
            except Exception as e:
                self.details_text.append(f'[오류] {os.path.basename(file)}: {e}')

    def add_device_to_table_nexus(self, device):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setRowHeight(row, 38)
        items = [
            device['filename'], device['hostname'], device['model'],
            device['nxos_version'], device['cpu'],
            str(device['memory_total']), str(device['memory_used']),
            device['memory_usage'], device['uptime'], device['last_reboot'],
        ]
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFont(QFont('맑은 고딕', 9))
            self.result_table.setItem(row, col, item)

    def parse_show_version_nexus(self, content):
        m = re.search(r'Device name:\s+(\S+)', content)
        hostname = m.group(1) if m else 'N/A'
        m = re.search(r'NXOS: version\s+([\d\.\(\)A-Z]+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'System version:\s+([\d\.\(\)A-Z]+)', content, re.IGNORECASE)
        nxos = m.group(1) if m else 'N/A'
        m = re.search(r'Hardware\s+:\s+cisco\s+Nexus\d+\s+(\S+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'\b(N\d[KX]?-\S+)\b', content)
        model = m.group(1) if m else 'N/A'
        return hostname, nxos, model

    def parse_system_resources(self, content):
        m = re.search(r'CPU states\s+:\s+([\d\.]+)% user,\s+([\d\.]+)% kernel', content)
        cpu = f'{round(float(m.group(1)) + float(m.group(2)), 1)}%' if m else 'N/A'
        m = re.search(r'Memory usage:\s+(\d+)K total,\s+(\d+)K used,\s+(\d+)K free', content)
        if m:
            t, u, f_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
            usage = f'{round((u/t)*100, 1)}%'
        else:
            t, u, f_, usage = 'N/A', 'N/A', 'N/A', 'N/A'
        m = re.search(r'Kernel uptime is (\d+) day\(s\), (\d+) hour\(s\)', content)
        uptime = f'{m.group(1)}d {m.group(2)}h' if m else 'N/A'
        return cpu, t, u, f_, usage, uptime

    def parse_last_reboot(self, content):
        m = re.search(r'Last reset at\s+(.+?)(\s+Reason:|\n)', content)
        return m.group(1).strip() if m else 'N/A'


# ── 통합 보고서 (IOS-XE + NX-OS 자동 감지) ────────────────────────────────────
class UnifiedReportGenerator(QWidget):
    """IOS-XE / NX-OS 자동 감지 통합 보고서"""

    def __init__(self):
        super().__init__()
        self.device_data = []
        self.init_ui()

    # ── UI ────────────────────────────────────────────────────────────────────
    def init_ui(self):
        self.setObjectName('unifiedReport')
        self.setStyleSheet('#unifiedReport { background: #f1f5f9; }')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header(
            '장비 보고서',
            'Cisco IOS-XE / NX-OS 자동 감지 · 데이터 수집 · 분석 · 내보내기',
            '#0f172a', '#2563eb',
        ))

        body = QWidget()
        body.setObjectName('unifiedBody')
        body.setStyleSheet('#unifiedBody { background: transparent; }')
        bv = QHBoxLayout(body)
        bv.setContentsMargins(18, 16, 18, 16)
        bv.setSpacing(12)
        bv.addWidget(self._build_left())
        bv.addWidget(self._build_right(), 1)
        root.addWidget(body, 1)

    def _build_left(self):
        card = _card()
        card.setFixedWidth(210)
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        v.addWidget(_sec('파일 불러오기'))

        load_btn = QPushButton('파일 열기')
        load_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        load_btn.setFixedHeight(36)
        load_btn.setStyleSheet(
            'QPushButton{background:#3b82f6;color:#fff;border:none;border-radius:8px}'
            'QPushButton:hover{background:#2563eb}'
        )
        load_btn.clicked.connect(self.load_files)
        v.addWidget(load_btn)

        self._count_frame = QFrame()
        self._count_frame.setFixedHeight(36)
        self._count_frame.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:7px;border:1px solid #e2e8f0}'
        )
        cf = QHBoxLayout(self._count_frame)
        cf.setContentsMargins(10, 0, 10, 0)
        self._dot_lbl = QLabel('●')
        self._dot_lbl.setFont(QFont('맑은 고딕', 10))
        self._dot_lbl.setStyleSheet('background:transparent;border:none;color:#cbd5e1')
        self.file_count_label = QLabel('로드된 파일: 0개')
        self.file_count_label.setFont(QFont('맑은 고딕', 9))
        self.file_count_label.setStyleSheet('background:transparent;border:none;color:#94a3b8')
        cf.addWidget(self._dot_lbl)
        cf.addWidget(self.file_count_label, 1)
        v.addWidget(self._count_frame)

        v.addWidget(_sep())
        v.addWidget(_sec('장비 유형'))

        self._ios_lbl = QLabel('IOS-XE : 0대')
        self._ios_lbl.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self._ios_lbl.setStyleSheet('color:#2563eb;background:transparent;border:none')
        self._nxos_lbl = QLabel('NX-OS  : 0대')
        self._nxos_lbl.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self._nxos_lbl.setStyleSheet('color:#7c3aed;background:transparent;border:none')
        v.addWidget(self._ios_lbl)
        v.addWidget(self._nxos_lbl)

        v.addWidget(_sep())
        v.addWidget(_sec('내보내기'))

        for label, slot, color, hover in [
            ('Excel 저장', self.save_to_excel, '#10b981', '#059669'),
            ('CSV 저장',   self.save_to_csv,   '#10b981', '#059669'),
        ]:
            btn = QPushButton(label)
            btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
            btn.setFixedHeight(34)
            btn.setStyleSheet(
                f'QPushButton{{background:{color};color:#fff;border:none;border-radius:8px}}'
                f'QPushButton:hover{{background:{hover}}}'
            )
            btn.clicked.connect(slot)
            v.addWidget(btn)

        v.addStretch()

        clear_btn = QPushButton('초기화')
        clear_btn.setFont(QFont('맑은 고딕', 9))
        clear_btn.setFixedHeight(30)
        clear_btn.setStyleSheet(
            'QPushButton{background:#fee2e2;color:#ef4444;'
            'border:1px solid #fca5a5;border-radius:7px}'
            'QPushButton:hover{background:#fecaca}'
        )
        clear_btn.clicked.connect(self.clear_data)
        v.addWidget(clear_btn)
        return card

    def _build_right(self):
        card = _card()
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        bar = QFrame()
        bar.setFixedHeight(40)
        bar.setStyleSheet(
            'QFrame{background:#f8fafc;border-radius:10px 10px 0 0;'
            'border-bottom:1px solid #e2e8f0}'
        )
        barv = QHBoxLayout(bar)
        barv.setContentsMargins(16, 0, 16, 0)
        t = QLabel('장비 데이터')
        t.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        t.setStyleSheet('color:#1e293b;background:transparent;border:none')
        barv.addWidget(t)
        barv.addStretch()
        v.addWidget(bar)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(12)
        self.result_table.setHorizontalHeaderLabels([
            '유형', '파일명', '호스트명', 'OS 버전', '시리얼',
            'CPU 5초', 'CPU 1분', 'CPU 5분',
            '메모리 총량', '메모리 사용', '사용률', '가동시간',
        ])
        hdr = self.result_table.horizontalHeader()
        for i in range(12):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setShowGrid(False)
        self.result_table.setFont(QFont('맑은 고딕', 9))
        self.result_table.horizontalHeader().setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self.result_table.setStyleSheet(
            'QTableWidget{background:#ffffff;border:none;outline:none}'
            'QTableWidget::item{padding:6px 10px;border-bottom:1px solid #f1f5f9}'
            'QTableWidget::item:selected{background:#dbeafe;color:#1e40af}'
            'QTableWidget::item:alternate{background:#f8fafc}'
            'QHeaderView::section{background:#f8fafc;color:#64748b;padding:8px 10px;'
            '  border:none;border-bottom:1px solid #e2e8f0;font-weight:bold}'
        )
        self.result_table.itemClicked.connect(self.show_device_details)
        v.addWidget(self.result_table, 1)

        dbar = QFrame()
        dbar.setFixedHeight(34)
        dbar.setStyleSheet(
            'QFrame{background:#f8fafc;border-top:1px solid #e2e8f0;'
            'border-bottom:none;border-left:none;border-right:none}'
        )
        dbarv = QHBoxLayout(dbar)
        dbarv.setContentsMargins(16, 0, 16, 0)
        dt = QLabel('상세 정보')
        dt.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        dt.setStyleSheet('color:#64748b;background:transparent;border:none')
        dbarv.addWidget(dt)
        v.addWidget(dbar)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont('Consolas', 9))
        self.details_text.setFixedHeight(150)
        self.details_text.setPlaceholderText('장비를 선택하면 상세 정보가 표시됩니다...')
        self.details_text.setStyleSheet(
            'QTextEdit{background:#f8fafc;border:none;border-radius:0 0 10px 10px;'
            'padding:10px;color:#334155}'
        )
        v.addWidget(self.details_text)
        return card

    # ── 장비 유형 감지 ────────────────────────────────────────────────────────
    def _detect_device_type(self, content):
        cl = content.lower()
        nxos_kw = [
            'nxos:', 'nx-os',
            'show system resources', 'sh system resources',  # 전체/약어 모두
            'kernel uptime is',
            'cisco nexus operating system',
            'device name:',
            'cpu states',       # NX-OS show system resources 고유
            'memory usage:',    # NX-OS 고유 (IOS-XE 는 "System memory:")
            'load average:',    # NX-OS 고유
            'processes   :',    # NX-OS show system resources 고유
        ]
        if any(kw in cl for kw in nxos_kw):
            return 'NX-OS'
        return 'IOS-XE'

    # ── IOS-XE 파싱 ───────────────────────────────────────────────────────────
    def _parse_ios_xe(self, content, filename):
        # Hostname — hostname config > uptime 문장 > CLI 프롬프트 순
        m = re.search(r'^hostname\s+(\S+)', content, re.MULTILINE | re.IGNORECASE)
        if not m:
            m = re.search(r'^(\S+)\s+uptime\s+is', content, re.MULTILINE)
        if not m:
            m = re.search(r'^(\S+)[#>]', content, re.MULTILINE)
        hostname = m.group(1) if m else 'N/A'

        # OS version — 여러 패턴 순서대로 시도
        m = re.search(r'Cisco IOS XE Software,\s*Version\s+(\S+?)(?:,|\s|$)', content)
        if not m:
            m = re.search(r'Cisco IOS\s+\S*\s*Software.*?,\s*Version\s+([\d\.\(\)A-Za-z]+)', content, re.DOTALL)
        if not m:
            m = re.search(r'IOS.{0,30}Version\s+([\d]+\.[\d][\d\.\(\)A-Za-z]*)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'\bVersion\s+([\d]+\.[\d][\d\.\(\)A-Za-z]*)', content)
        os_version = m.group(1).rstrip(',') if m else 'N/A'

        # Serial
        m = re.search(r'Processor board ID\s+(\S+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'System serial number\s*:\s*(\S+)', content, re.IGNORECASE)
        serial = m.group(1) if m else 'N/A'

        # Uptime — "Switch uptime is ..." 또는 "uptime is ..."
        m = re.search(r'(?:^\S+\s+)?uptime\s+is\s+(.+?)(?:\r?\n|$)', content, re.IGNORECASE | re.MULTILINE)
        uptime = m.group(1).strip() if m else 'N/A'

        # CPU 5s / 1m / 5m
        # 형식: "CPU utilization for five seconds: 3%/0%; one minute: 3%; five minutes: 3%"
        m = re.search(
            r'CPU utilization for five seconds:\s*([\d\.]+)%.*?'
            r'one minute:\s*([\d\.]+)%.*?'
            r'five minutes:\s*([\d\.]+)%',
            content, re.DOTALL | re.IGNORECASE
        )
        if m:
            cpu_5s, cpu_1m, cpu_5m = m.group(1)+'%', m.group(2)+'%', m.group(3)+'%'
        else:
            cpu_5s = cpu_1m = cpu_5m = 'N/A'

        # CPU History
        mh = re.search(r'((?:CPU|cpu)%?\s+per second.*?)(?=\n\s*\n|\Z)', content, re.DOTALL)
        cpu_history = mh.group(1)[:600] if mh else ''

        # Memory — Processor Pool 우선, 없으면 System memory
        # 형식: "Processor Pool Total:   73910760 Used:   26542632 Free:   47368128"
        m = re.search(r'Processor Pool Total:\s*(\d+)\s+Used:\s*(\d+)', content, re.IGNORECASE)
        if m:
            total, used = int(m.group(1)), int(m.group(2))
            mem_total = f'{total:,} B'
            mem_used  = f'{used:,} B'
            mem_pct   = f'{round(used/total*100, 1)}%' if total else 'N/A'
        else:
            m = re.search(r'System memory\s*:\s*(\d+)\s*K\s*total,\s*(\d+)\s*K\s*used', content, re.IGNORECASE)
            if m:
                total, used = int(m.group(1)), int(m.group(2))
                mem_total = f'{total:,} K'
                mem_used  = f'{used:,} K'
                mem_pct   = f'{round(used/total*100, 1)}%' if total else 'N/A'
            else:
                mem_total = mem_used = mem_pct = 'N/A'

        # Model
        m = re.search(r'Model number\s*:\s*(\S+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'cisco\s+(C\d{4}[^\s,]+)', content, re.IGNORECASE)
        model = m.group(1) if m else 'N/A'

        return {
            'device_type': 'IOS-XE', 'filename': filename,
            'hostname': hostname, 'os_version': os_version,
            'serial': serial, 'uptime': uptime,
            'cpu_5s': cpu_5s, 'cpu_1m': cpu_1m, 'cpu_5m': cpu_5m,
            'cpu_history': cpu_history,
            'mem_total': mem_total, 'mem_used': mem_used, 'mem_pct': mem_pct,
            'model': model, 'raw': content,
        }

    # ── NX-OS 파싱 ────────────────────────────────────────────────────────────
    def _parse_nxos(self, content, filename):
        # Hostname — Device name > switchname > hostname > CLI 프롬프트 순
        m = re.search(r'Device name:\s*(\S+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'^switchname\s+(\S+)', content, re.MULTILINE | re.IGNORECASE)
        if not m:
            m = re.search(r'^hostname\s+(\S+)', content, re.MULTILINE | re.IGNORECASE)
        if not m:
            # CLI 프롬프트: "Main_jujo_sw02# " 또는 "Router> " 형태
            m = re.search(r'^(\S+)[#>]', content, re.MULTILINE)
        hostname = m.group(1) if m else 'N/A'

        # OS version — NXOS: version / system: version / Nexus ~Version
        m = re.search(r'NXOS:\s+version\s+(\S+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'system:\s+version\s+(\S+)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'Cisco Nexus[^\n]*[Vv]ersion\s+([\d\.]+[\(\)A-Za-z\d]*)', content)
        if not m:
            m = re.search(r'NX-OS[^\n]*[Vv]ersion\s+([\d\.]+[\(\)A-Za-z\d]*)', content)
        os_version = m.group(1) if m else 'N/A'

        # Serial
        m = re.search(r'Processor board ID\s+(\S+)', content, re.IGNORECASE)
        serial = m.group(1) if m else 'N/A'

        # Uptime
        m = re.search(r'Kernel uptime is\s+(.+?)(?:\r?\n|$)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'uptime\s+is\s+(.+?)(?:\r?\n|$)', content, re.IGNORECASE)
        uptime = m.group(1).strip() if m else 'N/A'

        # CPU — show system resources
        # 형식: CPU states  :   0.00% user,   0.00% kernel,  99.99% idle
        cpu_5s = cpu_1m = cpu_5m = 'N/A'
        m = re.search(
            r'CPU states\s*:\s*([\d\.]+)%\s+user.*?([\d\.]+)%\s+kernel',
            content, re.IGNORECASE | re.DOTALL
        )
        if m:
            cpu_5s = f'{round(float(m.group(1)) + float(m.group(2)), 1)}%'
        else:
            # idle에서 역산
            m = re.search(r'([\d\.]+)%\s+idle', content, re.IGNORECASE)
            if m:
                cpu_5s = f'{round(100.0 - float(m.group(1)), 1)}%'

        # Load average (1분, 5분)
        m = re.search(
            r'Load average:\s*1 minute:\s*([\d\.]+)\s+5 minutes:\s*([\d\.]+)',
            content, re.IGNORECASE
        )
        if m:
            cpu_1m = f'{m.group(1)} (avg)'
            cpu_5m = f'{m.group(2)} (avg)'

        # Memory — Memory usage: XK total, YK used, ZK free
        # 공백·K 위치 유연하게 처리
        m = re.search(
            r'Memory usage:\s*(\d+)\s*K?\s+total,\s*(\d+)\s*K?\s+used',
            content, re.IGNORECASE
        )
        if m:
            total, used = int(m.group(1)), int(m.group(2))
            mem_total = f'{total:,} K'
            mem_used  = f'{used:,} K'
            mem_pct   = f'{round(used/total*100, 1)}%' if total else 'N/A'
        else:
            mem_total = mem_used = mem_pct = 'N/A'

        # Model
        m = re.search(r'Hardware\s*\n\s*cisco\s+(.+?)(?:\n|Chassis)', content, re.IGNORECASE)
        if not m:
            m = re.search(r'cisco\s+(N\d[KX]?\S+)', content, re.IGNORECASE)
        model = m.group(1).strip() if m else 'N/A'

        return {
            'device_type': 'NX-OS', 'filename': filename,
            'hostname': hostname, 'os_version': os_version,
            'serial': serial, 'uptime': uptime,
            'cpu_5s': cpu_5s, 'cpu_1m': cpu_1m, 'cpu_5m': cpu_5m,
            'cpu_history': '',
            'mem_total': mem_total, 'mem_used': mem_used, 'mem_pct': mem_pct,
            'model': model, 'raw': content,
        }

    # ── 파일 로드 ─────────────────────────────────────────────────────────────
    def load_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, '텍스트 파일 선택', '', 'Text Files (*.txt);;All Files (*)'
        )
        if not files:
            return
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                filename = os.path.splitext(os.path.basename(fp))[0]
                dtype = self._detect_device_type(content)
                info = self._parse_nxos(content, filename) if dtype == 'NX-OS' \
                    else self._parse_ios_xe(content, filename)
                self.device_data.append(info)
                self._add_to_table(info)
            except Exception as e:
                logging.error(f'[ERROR] 파싱 실패: {fp} - {e}')

        n      = len(self.device_data)
        ios_n  = sum(1 for d in self.device_data if d['device_type'] == 'IOS-XE')
        nxos_n = sum(1 for d in self.device_data if d['device_type'] == 'NX-OS')
        self.file_count_label.setText(f'로드된 파일: {n}개')
        self._ios_lbl.setText(f'IOS-XE : {ios_n}대')
        self._nxos_lbl.setText(f'NX-OS  : {nxos_n}대')
        self._dot_lbl.setStyleSheet('background:transparent;border:none;color:#3b82f6')
        self.file_count_label.setStyleSheet(
            'background:transparent;border:none;color:#1e293b;font-size:9pt'
        )
        self._count_frame.setStyleSheet(
            'QFrame{background:#eff6ff;border-radius:7px;border:1px solid #bfdbfe}'
        )
        logging.info(f'[INFO] 파일 로드: {n}개 (IOS-XE:{ios_n}, NX-OS:{nxos_n})')

    def _add_to_table(self, device):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setRowHeight(row, 38)
        dtype = device['device_type']
        row_data = [
            dtype, device['filename'], device['hostname'],
            device['os_version'], device['serial'],
            device['cpu_5s'], device['cpu_1m'], device['cpu_5m'],
            device['mem_total'], device['mem_used'], device['mem_pct'],
            device['uptime'],
        ]
        type_color = '#2563eb' if dtype == 'IOS-XE' else '#7c3aed'
        for col, text in enumerate(row_data):
            item = QTableWidgetItem(text)
            item.setFont(QFont('맑은 고딕', 9))
            if col == 0:
                item.setForeground(QColor(type_color))
            self.result_table.setItem(row, col, item)

    def show_device_details(self, item):
        row = item.row()
        it = self.result_table.item(row, 1)
        if not it:
            return
        filename = it.text()
        device = next((d for d in self.device_data if d['filename'] == filename), None)
        if not device:
            return
        self.details_text.clear()
        lines = [
            f'━━━  {filename}  [{device["device_type"]}]  ━━━',
            f'호스트명  : {device["hostname"]}',
            f'OS 버전   : {device["os_version"]}',
            f'시리얼    : {device["serial"]}',
            f'CPU 5초   : {device["cpu_5s"]}',
            f'CPU 1분   : {device["cpu_1m"]}',
            f'CPU 5분   : {device["cpu_5m"]}',
            f'메모리    : {device["mem_used"]} / {device["mem_total"]} ({device["mem_pct"]})',
            f'가동시간  : {device["uptime"]}',
        ]
        if device.get('cpu_history'):
            lines.append('')
            lines.append('[CPU History]')
            lines.append(device['cpu_history'])
        self.details_text.setPlainText('\n'.join(lines))

    def clear_data(self):
        if not self.device_data:
            return
        reply = QMessageBox.question(
            self, '초기화', '모든 데이터를 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.device_data.clear()
            self.result_table.setRowCount(0)
            self.details_text.clear()
            self.file_count_label.setText('로드된 파일: 0개')
            self._ios_lbl.setText('IOS-XE : 0대')
            self._nxos_lbl.setText('NX-OS  : 0대')
            self._dot_lbl.setStyleSheet('background:transparent;border:none;color:#cbd5e1')
            self.file_count_label.setStyleSheet(
                'background:transparent;border:none;color:#94a3b8'
            )
            self._count_frame.setStyleSheet(
                'QFrame{background:#f8fafc;border-radius:7px;border:1px solid #e2e8f0}'
            )

    def save_to_excel(self):
        if not self.device_data:
            QMessageBox.warning(self, '오류', '저장할 데이터가 없습니다.')
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Excel 저장', 'UnifiedReport.xlsx', 'Excel Files (*.xlsx)'
            )
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = 'Report'
            ws.append(['유형', '파일명', '호스트명', 'OS 버전', '시리얼',
                        'CPU 5초', 'CPU 1분', 'CPU 5분',
                        '메모리 총량', '메모리 사용', '사용률', '가동시간'])
            for d in self.device_data:
                ws.append([
                    d['device_type'], d['filename'], d['hostname'], d['os_version'],
                    d['serial'], d['cpu_5s'], d['cpu_1m'], d['cpu_5m'],
                    d['mem_total'], d['mem_used'], d['mem_pct'], d['uptime'],
                ])
            wb.save(path)
            QMessageBox.information(self, '완료', f'저장 완료:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, '오류', f'저장 실패: {e}')

    def save_to_csv(self):
        if not self.device_data:
            QMessageBox.warning(self, '오류', '저장할 데이터가 없습니다.')
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, 'CSV 저장', 'UnifiedReport.csv', 'CSV Files (*.csv)'
            )
            if not path:
                return
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['유형', '파일명', '호스트명', 'OS 버전', '시리얼',
                            'CPU 5초', 'CPU 1분', 'CPU 5분',
                            '메모리 총량', '메모리 사용', '사용률', '가동시간'])
                for d in self.device_data:
                    w.writerow([
                        d['device_type'], d['filename'], d['hostname'], d['os_version'],
                        d['serial'], d['cpu_5s'], d['cpu_1m'], d['cpu_5m'],
                        d['mem_total'], d['mem_used'], d['mem_pct'], d['uptime'],
                    ])
            QMessageBox.information(self, '완료', f'저장 완료:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, '오류', f'저장 실패: {e}')
