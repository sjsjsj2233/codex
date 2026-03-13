"""
보고서 탭 - 프로페셔널 디자인
"""
import sys
import os
import logging
import csv
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QTableWidget,
    QHBoxLayout, QCheckBox, QPushButton,
    QFileDialog, QTableWidgetItem, QHeaderView, QSplitter,
    QMessageBox, QFrame, QScrollArea
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from openpyxl import Workbook


class EnhancedInspectionReportGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.device_data = []
        self.init_ui()

    def init_ui(self):
        """메인 UI 초기화 - 깔끔하고 정돈된 레이아웃"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # 상단 컨트롤 영역 (파일 & 옵션)
        control_section = self.create_control_section()
        main_layout.addWidget(control_section)

        # 중단 액션 영역 (저장 버튼들)
        action_section = self.create_action_section()
        main_layout.addWidget(action_section)

        # 하단 데이터 영역 (테이블 & 상세정보)
        data_section = self.create_data_section()
        main_layout.addWidget(data_section, 1)

    def create_control_section(self):
        """상단 컨트롤 섹션 - 파일 불러오기 & 옵션"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        section.setFixedHeight(90)

        layout = QHBoxLayout(section)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(20)

        # 왼쪽: 파일 불러오기
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        load_btn = QPushButton("📂 파일 열기")
        load_btn.setFixedSize(120, 32)
        load_btn.clicked.connect(self.load_txt_files)
        load_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2563eb, stop:1 #1d4ed8);
            }
        """)

        self.file_count_label = QLabel("📄 로드된 파일: 0개")
        self.file_count_label.setStyleSheet("""
            color: #475569;
            font-size: 10pt;
            font-weight: 600;
            padding: 4px 0px;
        """)

        left_layout.addWidget(load_btn)
        left_layout.addWidget(self.file_count_label)

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { background-color: #cbd5e1; }")
        separator.setFixedWidth(2)

        # 오른쪽: 출력 옵션
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        options_label = QLabel("📊 출력 항목 선택:")
        options_label.setStyleSheet("""
            color: #1e293b;
            font-size: 10pt;
            font-weight: 700;
        """)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(15)

        self.include_cpu = QCheckBox("CPU 사용률")
        self.include_cpu.setChecked(True)
        self.include_memory = QCheckBox("메모리 정보")
        self.include_memory.setChecked(True)
        self.include_uptime = QCheckBox("가동 시간")
        self.include_uptime.setChecked(True)

        checkbox_style = """
            QCheckBox {
                color: #475569;
                font-size: 10pt;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #cbd5e1;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border-color: #3b82f6;
            }
            QCheckBox::indicator:hover {
                border-color: #3b82f6;
            }
        """
        self.include_cpu.setStyleSheet(checkbox_style)
        self.include_memory.setStyleSheet(checkbox_style)
        self.include_uptime.setStyleSheet(checkbox_style)

        checkbox_layout.addWidget(self.include_cpu)
        checkbox_layout.addWidget(self.include_memory)
        checkbox_layout.addWidget(self.include_uptime)
        checkbox_layout.addStretch()

        right_layout.addWidget(options_label)
        right_layout.addLayout(checkbox_layout)

        # 레이아웃 조합
        layout.addLayout(left_layout)
        layout.addWidget(separator)
        layout.addLayout(right_layout, 1)

        return section

    def create_action_section(self):
        """중단 액션 섹션 - 저장 버튼들"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        section.setFixedHeight(70)

        layout = QHBoxLayout(section)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # 액션 라벨
        action_label = QLabel("💾 저장 옵션:")
        action_label.setStyleSheet("""
            color: #1e293b;
            font-size: 11pt;
            font-weight: 700;
        """)

        # Excel 저장 버튼
        excel_btn = QPushButton("Excel 저장")
        excel_btn.setFixedSize(120, 36)
        excel_btn.clicked.connect(self.save_to_excel)
        excel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
            }
        """)

        # CSV 저장 버튼
        csv_btn = QPushButton("CSV 저장")
        csv_btn.setFixedSize(120, 36)
        csv_btn.clicked.connect(self.save_to_csv)
        csv_btn.setStyleSheet(excel_btn.styleSheet())

        # 초기화 버튼
        clear_btn = QPushButton("🗑 초기화")
        clear_btn.setFixedSize(100, 36)
        clear_btn.clicked.connect(self.clear_data)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #ef4444;
                border: 2px solid #fca5a5;
                border-radius: 6px;
                font-size: 10pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                border-color: #ef4444;
            }
        """)

        layout.addWidget(action_label)
        layout.addWidget(excel_btn)
        layout.addWidget(csv_btn)
        layout.addStretch()
        layout.addWidget(clear_btn)

        return section

    def create_data_section(self):
        """데이터 섹션 - 테이블 및 상세정보"""
        # 메인 프레임
        main_frame = QFrame()
        main_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 테이블 섹션
        table_label = QLabel("📊 장비 데이터")
        table_label.setStyleSheet("""
            color: #1e293b;
            font-size: 11pt;
            font-weight: 700;
            padding: 5px 0px;
        """)
        main_layout.addWidget(table_label)

        # 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(10)
        self.result_table.setHorizontalHeaderLabels([
            "파일명", "호스트명", "모델", "IOS 버전", "SW 버전",
            "CPU", "메모리 총량", "메모리 사용", "사용률", "가동시간"
        ])

        # 컬럼 너비 조정
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        for i in range(3, 10):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setShowGrid(True)
        self.result_table.setMinimumHeight(300)

        # 세련된 테이블 스타일
        self.result_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                gridline-color: #f1f5f9;
                font-size: 10pt;
                color: #1e293b;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
            QTableWidget::item:alternate {
                background-color: #f8fafc;
            }
            QTableWidget::item:hover {
                background-color: #f0f9ff;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8fafc, stop:1 #f1f5f9);
                color: #475569;
                font-weight: 700;
                font-size: 10pt;
                border: 1px solid #e2e8f0;
                padding: 10px;
                text-align: left;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e2e8f0, stop:1 #cbd5e1);
            }
        """)

        main_layout.addWidget(self.result_table)

        # 상세 정보 섹션
        details_label = QLabel("📋 상세 정보")
        details_label.setStyleSheet("""
            color: #1e293b;
            font-size: 11pt;
            font-weight: 700;
            padding: 5px 0px;
        """)
        main_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        self.details_text.setFixedHeight(150)
        self.details_text.setPlaceholderText("장비를 선택하면 상세 정보가 표시됩니다...")
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 12px;
                color: #334155;
            }
        """)

        main_layout.addWidget(self.details_text)

        self.result_table.itemClicked.connect(self.show_device_details)

        return main_frame

    def load_txt_files(self):
        """텍스트 파일 불러오기"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "텍스트 파일 선택", "", "Text Files (*.txt);;All Files (*)"
        )
        if not files:
            return

        self.details_text.append(f"[로드] {len(files)}개 파일")
        for file in files:
            self.details_text.append(f"  • {os.path.basename(file)}")

        self.parse_txt_files(files)
        self.file_count_label.setText(f"📄 로드된 파일: {len(self.device_data)}개")
        logging.info(f"[INFO] 파일 로드: {len(files)}개")

    def parse_txt_files(self, files):
        """파일 파싱"""
        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                filename = os.path.splitext(os.path.basename(file))[0]
                run_hostname = self.parse_run_hostname(content)
                ios_version, sw_version, model = self.parse_show_version(content)
                total_mem, used_mem, free_mem, memory_usage = self.parse_memory(content)
                cpu_usage = self.parse_cpu(content)
                uptime = self.parse_uptime(content)

                device_info = {
                    "filename": filename,
                    "hostname": run_hostname,
                    "cpu": cpu_usage,
                    "memory_total": total_mem,
                    "memory_used": used_mem,
                    "memory_free": free_mem,
                    "memory_usage": memory_usage,
                    "uptime": uptime,
                    "ios_version": ios_version,
                    "sw_version": sw_version,
                    "model": model,
                    "raw_content": content
                }
                self.device_data.append(device_info)
                self.add_device_to_table(device_info)

            except Exception as e:
                self.details_text.append(f"[오류] {os.path.basename(file)}: {e}")
                logging.error(f"[ERROR] 파싱 실패: {file} - {e}")

    def add_device_to_table(self, device):
        """테이블에 장치 추가"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        items = [
            device["filename"], device["hostname"], device["model"],
            device["ios_version"], device["sw_version"], device["cpu"],
            str(device["memory_total"]), str(device["memory_used"]),
            device["memory_usage"], device["uptime"]
        ]

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFont(QFont("맑은 고딕", 9))
            self.result_table.setItem(row, col, item)

    def show_device_details(self, item):
        """상세 정보 표시"""
        row = item.row()
        filename = self.result_table.item(row, 0).text()
        device = next((d for d in self.device_data if d["filename"] == filename), None)

        if not device:
            return

        self.details_text.clear()
        self.details_text.append(f"━━━ {filename} ━━━")
        self.details_text.append(f"호스트: {device['hostname']}")
        self.details_text.append(f"모델: {device['model']}")
        self.details_text.append(f"IOS: {device['ios_version']}")
        self.details_text.append(f"CPU: {device['cpu']}")
        self.details_text.append(f"메모리: {device['memory_usage']}")
        self.details_text.append(f"가동: {device['uptime']}")

    def clear_data(self):
        """데이터 초기화"""
        if not self.device_data:
            return

        reply = QMessageBox.question(
            self, "초기화", "모든 데이터를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.device_data.clear()
            self.result_table.setRowCount(0)
            self.details_text.clear()
            self.file_count_label.setText("📄 로드된 파일: 0개")

    def save_to_excel(self):
        """Excel 저장"""
        if not self.device_data:
            QMessageBox.warning(self, "오류", "저장할 데이터가 없습니다.")
            return

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Excel 저장", "Report.xlsx", "Excel Files (*.xlsx)"
            )
            if not file_path:
                return

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Report"

            headers = ["파일명", "호스트명", "모델", "IOS", "SW"]
            if self.include_cpu.isChecked():
                headers.append("CPU")
            if self.include_memory.isChecked():
                headers.extend(["메모리", "사용", "여유", "사용률"])
            if self.include_uptime.isChecked():
                headers.append("가동시간")

            sheet.append(headers)

            for device in self.device_data:
                row_data = [
                    device["filename"], device["hostname"], device["model"],
                    device["ios_version"], device["sw_version"]
                ]
                if self.include_cpu.isChecked():
                    row_data.append(device["cpu"])
                if self.include_memory.isChecked():
                    row_data.extend([
                        device["memory_total"], device["memory_used"],
                        device["memory_free"], device["memory_usage"]
                    ])
                if self.include_uptime.isChecked():
                    row_data.append(device["uptime"])
                sheet.append(row_data)

            workbook.save(file_path)
            QMessageBox.information(self, "완료", f"저장 완료:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")

    def save_to_csv(self):
        """CSV 저장"""
        if not self.device_data:
            QMessageBox.warning(self, "오류", "저장할 데이터가 없습니다.")
            return

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "CSV 저장", "Report.csv", "CSV Files (*.csv)"
            )
            if not file_path:
                return

            headers = ["파일명", "호스트명", "모델", "IOS", "SW"]
            if self.include_cpu.isChecked():
                headers.append("CPU")
            if self.include_memory.isChecked():
                headers.extend(["메모리", "사용", "여유", "사용률"])
            if self.include_uptime.isChecked():
                headers.append("가동시간")

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for device in self.device_data:
                    row_data = [
                        device["filename"], device["hostname"], device["model"],
                        device["ios_version"], device["sw_version"]
                    ]
                    if self.include_cpu.isChecked():
                        row_data.append(device["cpu"])
                    if self.include_memory.isChecked():
                        row_data.extend([
                            device["memory_total"], device["memory_used"],
                            device["memory_free"], device["memory_usage"]
                        ])
                    if self.include_uptime.isChecked():
                        row_data.append(device["uptime"])
                    writer.writerow(row_data)

            QMessageBox.information(self, "완료", f"저장 완료:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")

    # 파싱 메서드들
    def parse_run_hostname(self, content):
        match = re.search(r"^hostname\s+(\S+)", content, re.MULTILINE)
        return match.group(1) if match else "N/A"

    def parse_show_version(self, content):
        ios_match = re.search(r"Version\s+([\d\.\(\)A-Z]+)", content)
        ios_version = ios_match.group(1) if ios_match else "N/A"

        model_match = re.search(r"Model number\s+:\s+(\S+)", content, re.IGNORECASE)
        if model_match:
            model = model_match.group(1)
        else:
            model_match = re.search(r"\bC\d{4,}\b", content)
            model = model_match.group(0) if model_match else "N/A"

        return ios_version, ios_version, model

    def parse_memory(self, content):
        match = re.search(r"Processor Pool Total:\s+(\d+)\s+Used:\s+(\d+)\s+Free:\s+(\d+)", content)
        if match:
            total, used, free = int(match.group(1)), int(match.group(2)), int(match.group(3))
            usage = f"{round((used/total)*100, 1)}%"
            return total, used, free, usage

        match = re.search(r"System memory\s+:\s+(\d+)K total,\s+(\d+)K used,\s+(\d+)K free", content)
        if match:
            total, used, free = int(match.group(1)), int(match.group(2)), int(match.group(3))
            usage = f"{round((used/total)*100, 1)}%"
            return total, used, free, usage

        return "N/A", "N/A", "N/A", "N/A"

    def parse_cpu(self, content):
        match = re.search(r"CPU utilization for five seconds:.*?(\d+)%", content)
        return match.group(1) + "%" if match else "N/A"

    def parse_uptime(self, content):
        match = re.search(r"uptime is (.+)", content)
        return match.group(1).strip() if match else "N/A"


class EnhancedNexusReportGenerator(EnhancedInspectionReportGenerator):
    """Nexus 보고서 생성기"""

    def __init__(self):
        super().__init__()
        self.result_table.setHorizontalHeaderLabels([
            "파일명", "호스트명", "모델", "NX-OS", "CPU",
            "메모리", "사용", "사용률", "가동시간", "재부팅"
        ])

    def parse_txt_files(self, files):
        """Nexus 파싱"""
        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                filename = os.path.splitext(os.path.basename(file))[0]
                hostname, nxos_version, model = self.parse_show_version_nexus(content)
                cpu, total_mem, used_mem, free_mem, mem_usage, uptime = self.parse_system_resources(content)
                reboot = self.parse_last_reboot(content)

                device_info = {
                    "filename": filename,
                    "hostname": hostname if hostname != "N/A" else filename,
                    "cpu": cpu,
                    "memory_total": total_mem,
                    "memory_used": used_mem,
                    "memory_free": free_mem,
                    "memory_usage": mem_usage,
                    "uptime": uptime,
                    "nxos_version": nxos_version,
                    "model": model,
                    "last_reboot": reboot,
                    "raw_content": content
                }
                self.device_data.append(device_info)
                self.add_device_to_table_nexus(device_info)

            except Exception as e:
                self.details_text.append(f"[오류] {os.path.basename(file)}: {e}")

    def add_device_to_table_nexus(self, device):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        items = [
            device["filename"], device["hostname"], device["model"],
            device["nxos_version"], device["cpu"],
            str(device["memory_total"]), str(device["memory_used"]),
            device["memory_usage"], device["uptime"], device["last_reboot"]
        ]

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFont(QFont("맑은 고딕", 9))
            self.result_table.setItem(row, col, item)

    def parse_show_version_nexus(self, content):
        hostname_match = re.search(r"Device name:\s+(\S+)", content)
        hostname = hostname_match.group(1) if hostname_match else "N/A"

        nxos_match = re.search(r"NXOS: version\s+([\d\.\(\)A-Z]+)", content, re.IGNORECASE)
        if not nxos_match:
            nxos_match = re.search(r"System version:\s+([\d\.\(\)A-Z]+)", content, re.IGNORECASE)
        nxos = nxos_match.group(1) if nxos_match else "N/A"

        model_match = re.search(r"Hardware\s+:\s+cisco\s+Nexus\d+\s+(\S+)", content, re.IGNORECASE)
        if not model_match:
            model_match = re.search(r"\b(N\d[KX]?-\S+)\b", content)
        model = model_match.group(1) if model_match else "N/A"

        return hostname, nxos, model

    def parse_system_resources(self, content):
        cpu_match = re.search(r"CPU states\s+:\s+([\d\.]+)% user,\s+([\d\.]+)% kernel", content)
        if cpu_match:
            cpu = f"{round(float(cpu_match.group(1)) + float(cpu_match.group(2)), 1)}%"
        else:
            cpu = "N/A"

        mem_match = re.search(r"Memory usage:\s+(\d+)K total,\s+(\d+)K used,\s+(\d+)K free", content)
        if mem_match:
            total, used, free = int(mem_match.group(1)), int(mem_match.group(2)), int(mem_match.group(3))
            usage = f"{round((used/total)*100, 1)}%"
        else:
            total, used, free, usage = "N/A", "N/A", "N/A", "N/A"

        uptime_match = re.search(r"Kernel uptime is (\d+) day\(s\), (\d+) hour\(s\)", content)
        uptime = f"{uptime_match.group(1)}d {uptime_match.group(2)}h" if uptime_match else "N/A"

        return cpu, total, used, free, usage, uptime

    def parse_last_reboot(self, content):
        match = re.search(r"Last reset at\s+(.+?)(\s+Reason:|\n)", content)
        return match.group(1).strip() if match else "N/A"
