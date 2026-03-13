import sys
import os
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# PyQt5 라이브러리
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QLineEdit, 
    QCheckBox, QPushButton, QSpinBox, QTableWidget, 
    QHBoxLayout, QTableWidgetItem, QHeaderView, QFrame, 
    QSplitter, QMessageBox, QGroupBox, QFormLayout, QDialog, QRadioButton
)
from PyQt5.QtGui import QFont, QIcon, QBrush, QColor
from PyQt5.QtCore import Qt, QTimer, QDateTime

# monitoring_tab.py 파일 상단에서 임포트 부분 찾기
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QCheckBox, QRadioButton, QSpinBox, QTextEdit, QFormLayout, QGroupBox, 
    QComboBox, QSplitter, QProgressBar, QFileDialog  # QProgressBar 추가
)

# 필요한 내부 모듈 import
from workers import PingThread, EnhancedPingThread, TCPingThread
import matplotlib
import matplotlib.font_manager as fm

font_path = "C:/Windows/Fonts/malgun.ttf"  # 맑은 고딕
if os.path.exists(font_path):
    font_name = fm.FontProperties(fname=font_path).get_name()
    matplotlib.rc('font', family=font_name)


class PingChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # matplotlib Figure 및 Canvas 생성
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def update_chart(self, ip_data):
        """IP별 응답 시간 차트 업데이트"""
        # 기존 그래프 초기화
        self.ax.clear()
        
        # IP와 응답 시간 데이터 준비
        ips = list(ip_data.keys())
        response_times = list(ip_data.values())
        
        # 막대 그래프 그리기
        self.ax.bar(ips, response_times)
        self.ax.set_title('IP별 Ping 응답 시간')
        self.ax.set_xlabel('IP 주소')
        self.ax.set_ylabel('응답 시간 (ms)')
        
        # 그래프 회전 및 레이아웃 조정
        plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
        plt.tight_layout()
        
        # 캔버스 다시 그리기
        self.canvas.draw()

class ChartDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ping 응답 시간 차트")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # PingChart 생성 및 추가
        self.ping_chart = PingChart()
        layout.addWidget(self.ping_chart)
        
        self.setLayout(layout)

class EnhancedPingTestTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Ping Test")
        self.ping_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # QSplitter로 입력 영역과 결과 영역 분리
        splitter = QSplitter(Qt.Vertical)

        # IP 리스트 입력 영역
        ip_input_widget = QWidget()
        ip_layout = QVBoxLayout()
        ip_label = QLabel("한 줄에 하나씩 IP 주소를 입력하세요:")
        self.ip_input = QTextEdit()
        self.ip_input.setPlaceholderText("192.168.1.1\n192.168.1.2\n...")
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        ip_input_widget.setLayout(ip_layout)

        # Ping 옵션 설정 영역
        options_group = QGroupBox("Ping 옵션")
        options_layout = QFormLayout()

        # 간격 설정
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 60)
        self.interval_input.setValue(1)
        self.interval_input.setSuffix(" 초")
        options_layout.addRow("간격:", self.interval_input)

        # 타임아웃 설정
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 30)
        self.timeout_input.setValue(3)
        self.timeout_input.setSuffix(" 초")
        options_layout.addRow("타임아웃:", self.timeout_input)

        # 반복 횟수 설정
        repeat_layout = QHBoxLayout()
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 999)
        self.repeat_input.setValue(4)
        self.unlimited_repeat = QCheckBox("무제한")
        self.unlimited_repeat.stateChanged.connect(self.toggle_repeat_input)
        repeat_layout.addWidget(self.repeat_input)
        repeat_layout.addWidget(self.unlimited_repeat)
        options_layout.addRow("반복 횟수:", repeat_layout)

        # 패킷 크기 설정
        self.packet_size_input = QSpinBox()
        self.packet_size_input.setRange(32, 65500)
        self.packet_size_input.setValue(32)
        self.packet_size_input.setSuffix(" 바이트")
        options_layout.addRow("패킷 크기:", self.packet_size_input)

        # TCP 포트 체크
        self.tcp_check = QCheckBox("TCP 포트(22, 23) 확인")
        options_layout.addRow("", self.tcp_check)

        options_group.setLayout(options_layout)
        ip_layout.addWidget(options_group)

        # 결과 표시 영역
        result_widget = QWidget()
        result_layout = QVBoxLayout()
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("Ping 테스트 결과가 여기에 표시됩니다.")
        result_layout.addWidget(self.result_display)
        result_widget.setLayout(result_layout)

        splitter.addWidget(ip_input_widget)
        splitter.addWidget(result_widget)
        splitter.setSizes([150, 250])  # 입력 영역과 결과 영역의 초기 크기 설정

        layout.addWidget(splitter)

        # 컨트롤 버튼 영역
        control_layout = QHBoxLayout()
        
        self.ping_button = QPushButton("PING TEST 시작")
        self.ping_button.clicked.connect(self.run_ping_test)
        control_layout.addWidget(self.ping_button)
        
        self.stop_button = QPushButton("중지")
        self.stop_button.clicked.connect(self.stop_ping_test)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_results)
        control_layout.addWidget(clear_button)

        layout.addLayout(control_layout)
        self.setLayout(layout)

    def toggle_repeat_input(self, state):
        """무제한 체크박스 상태에 따라 반복 횟수 입력 활성화/비활성화"""
        self.repeat_input.setEnabled(not state)

    def run_ping_test(self):
        # 줄바꿈을 기준으로 각 IP를 읽음
        ip_list = [ip.strip() for ip in self.ip_input.toPlainText().splitlines() if ip.strip()]
        if not ip_list:
            self.result_display.append("Please enter valid IP addresses.")
            return

        # 입력 설정 가져오기
        interval = self.interval_input.value()
        timeout = self.timeout_input.value()
        packet_size = self.packet_size_input.value()
        
        if self.unlimited_repeat.isChecked():
            repeat = 0  # 0은 무제한을 의미
        else:
            repeat = self.repeat_input.value()
        
        check_tcp = self.tcp_check.isChecked()
        
        # UI 업데이트
        self.ping_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.result_display.clear()
        
        # Ping 스레드 시작
        self.ping_thread = PingThread(ip_list, interval, timeout, repeat, packet_size, check_tcp)
        self.ping_thread.result_ready.connect(self.update_result)
        self.ping_thread.finished.connect(self.on_ping_finished)
        self.ping_thread.start()

    def stop_ping_test(self):
        """Ping 테스트 중지"""
        if self.ping_thread and self.ping_thread.isRunning():
            self.ping_thread.stop()
            self.result_display.append("<b>Ping 테스트가 중지되었습니다.</b>")
    
    def on_ping_finished(self):
        """Ping 테스트 완료 처리"""
        self.ping_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.result_display.append("<b>Ping 테스트가 완료되었습니다.</b>")

    def update_result(self, ip, result, color):
        """Ping 결과 업데이트"""
        self.result_display.append(f"<b>{ip}</b>: <font color='{color}'>{result}</font>")

    def clear_results(self):
        """결과 표시 영역 초기화"""
        self.result_display.clear()




class EnhancedPingViewTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ping View")
        self.ping_thread = None
        self.ping_results = {}  # IP별 결과 저장 
        self.response_times = {}  # IP별 응답 시간 기록
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 상단 제어 영역
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_frame)
        
        # IP 입력 영역
        ip_layout = QVBoxLayout()
        ip_label = QLabel("모니터링할 IP 주소:")
        self.ip_input = QTextEdit()
        self.ip_input.setPlaceholderText("한 줄에 하나씩 IP 주소 입력\n192.168.1.1\n192.168.1.2")
        self.ip_input.setMaximumHeight(100)
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        
        # 설정 영역
        settings_layout = QFormLayout()
        
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 60)
        self.interval_input.setValue(2)
        self.interval_input.setSuffix(" 초")
        
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 10)
        self.timeout_input.setValue(2)
        self.timeout_input.setSuffix(" 초")
        
        self.alert_threshold = QSpinBox()
        self.alert_threshold.setRange(10, 5000)
        self.alert_threshold.setValue(500)
        self.alert_threshold.setSuffix(" ms")
        
        self.show_chart = QCheckBox("응답 시간 차트 표시")
        self.show_chart.setChecked(True)
        
        settings_layout.addRow("간격:", self.interval_input)
        settings_layout.addRow("타임아웃:", self.timeout_input)
        settings_layout.addRow("알림 임계값:", self.alert_threshold)
        settings_layout.addWidget(self.show_chart)
        
        settings_group = QGroupBox("모니터링 설정")
        settings_group.setLayout(settings_layout)
        
        # 제어 영역에 추가
        control_layout.addLayout(ip_layout, 2)
        control_layout.addWidget(settings_group, 1)
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["IP 주소", "상태", "응답 시간", "패킷 손실", "마지막 응답"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 차트 영역
        self.chart_view = QWidget()
        chart_layout = QVBoxLayout(self.chart_view)
        chart_label = QLabel("응답 시간 차트")
        chart_label.setAlignment(Qt.AlignCenter)
        
        # 차트 위젯 (matplotlib으로 구현 필요)
        self.chart_widget = QFrame()
        self.chart_widget.setFrameShape(QFrame.StyledPanel)
        self.chart_widget.setMinimumHeight(200)
        self.chart_widget.setStyleSheet("background-color: #f0f0f0;")

        # PingChart 인스턴스 생성 및 추가
        self.ping_chart = PingChart()
        chart_widget_layout = QVBoxLayout(self.chart_widget)
        chart_widget_layout.addWidget(self.ping_chart)
        
        chart_layout.addWidget(chart_label)
        chart_layout.addWidget(self.chart_widget)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("모니터링 시작")
        self.start_button.clicked.connect(self.start_monitoring)
        
        self.stop_button = QPushButton("중지")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        
        clear_button = QPushButton("초기화")
        clear_button.clicked.connect(self.clear_results)
        
        chart_button = QPushButton("차트 보기")
        chart_button.clicked.connect(self.open_chart_dialog)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(clear_button)
        
        # 레이아웃에 위젯 추가
        layout.addWidget(control_frame)
        layout.addWidget(self.result_table, 2)
        layout.addWidget(self.chart_view, 1)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def open_chart_dialog(self):
        """차트 다이얼로그를 여는 메서드"""
        try:
            # ChartDialog에서 PingChart를 새로 생성하여 전달
            dialog = ChartDialog(self)
            dialog.exec_()
        except RuntimeError:
            print("PingChart 객체가 삭제되었습니다. 차트 다이얼로그를 열 수 없습니다.")




    def start_monitoring(self):
        # IP 목록 가져오기
        ip_list = [ip.strip() for ip in self.ip_input.toPlainText().splitlines() if ip.strip()]
        if not ip_list:
            QMessageBox.warning(self, "입력 오류", "모니터링할 IP 주소를 입력하세요!")
            return
        
        # 설정 가져오기
        interval = self.interval_input.value()
        timeout = self.timeout_input.value()
        
        # 테이블 초기화
        self.result_table.setRowCount(len(ip_list))
        for i, ip in enumerate(ip_list):
            # IP 주소 표시
            ip_item = QTableWidgetItem(ip)
            self.result_table.setItem(i, 0, ip_item)
            
            # 초기 상태 설정
            status_item = QTableWidgetItem("대기 중...")
            self.result_table.setItem(i, 1, status_item)
            
            # 나머지 열 초기화
            for j in range(2, 5):
                self.result_table.setItem(i, j, QTableWidgetItem("-"))
                
            # 결과 저장소 초기화
            self.ping_results[ip] = {"success": 0, "fail": 0, "total": 0, "last_time": "-"}
            self.response_times[ip] = []
        
        # UI 상태 변경
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.ip_input.setEnabled(False)
        
        # 모니터링 스레드 시작
        self.ping_thread = EnhancedPingThread(ip_list, interval, timeout)
        self.ping_thread.ping_result.connect(self.update_result)
        self.ping_thread.chart_update.connect(self.update_chart)
        self.ping_thread.start()

    def stop_monitoring(self):
        if self.ping_thread and self.ping_thread.isRunning():
            self.ping_thread.stop()
            self.ping_thread.wait()
            
        # UI 상태 변경
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.ip_input.setEnabled(True)

    def update_result(self, ip, success, response_time, message):
        # 테이블에서 해당 IP의 행 찾기
        for row in range(self.result_table.rowCount()):
            if self.result_table.item(row, 0).text() == ip:
                # 결과 업데이트
                self.ping_results[ip]["total"] += 1
                if success:
                    self.ping_results[ip]["success"] += 1
                    status_item = QTableWidgetItem("연결됨")
                    status_item.setForeground(QBrush(QColor("green")))
                    self.result_table.setItem(row, 1, status_item)
                    
                    # 응답 시간 저장 및 표시
                    time_item = QTableWidgetItem(f"{response_time} ms")
                    self.result_table.setItem(row, 2, time_item)
                    self.ping_results[ip]["last_time"] = response_time
                    
                    # 임계값 초과 시 알림
                    if response_time > self.alert_threshold.value():
                        time_item.setBackground(QBrush(QColor(255, 200, 200)))
                else:
                    self.ping_results[ip]["fail"] += 1
                    status_item = QTableWidgetItem("연결 끊김")
                    status_item.setForeground(QBrush(QColor("red")))
                    self.result_table.setItem(row, 1, status_item)
                    
                    # 응답 시간 업데이트
                    self.result_table.setItem(row, 2, QTableWidgetItem("-"))
                
                # 패킷 손실률 계산 및 표시
                total = self.ping_results[ip]["total"]
                fail = self.ping_results[ip]["fail"]
                loss_rate = (fail / total) * 100 if total > 0 else 0
                loss_item = QTableWidgetItem(f"{loss_rate:.1f}%")
                self.result_table.setItem(row, 3, loss_item)
                
                # 마지막 응답 시간 업데이트
                now = QDateTime.currentDateTime().toString("hh:mm:ss")
                self.result_table.setItem(row, 4, QTableWidgetItem(now))
                break

    def update_chart(self, ip_data):
        """차트 데이터 업데이트"""
        if not self.show_chart.isChecked():
            return

        # 🔹 self.ping_chart가 삭제되지 않았는지 확인
        if hasattr(self, "ping_chart") and self.ping_chart:
            try:
                self.ping_chart.update_chart(ip_data)
            except RuntimeError:
                print("PingChart 객체가 삭제된 후 호출됨. 업데이트 중단.")



    def clear_results(self):
        self.stop_monitoring()
        self.result_table.setRowCount(0)
        self.ping_results = {}
        self.response_times = {}



class TCPingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCPing Test")
        self.tcping_threads = []  # 여러 스레드를 관리하기 위한 리스트
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # QSplitter로 입력 영역과 결과 영역 분리
        splitter = QSplitter(Qt.Vertical)

        # 입력 영역
        input_widget = QWidget()
        input_layout = QVBoxLayout()
        
        # IP 또는 호스트 입력
        host_group = QGroupBox("대상 설정")
        host_layout = QVBoxLayout()
        
        # 호스트 입력 방식 선택
        host_selection = QHBoxLayout()
        self.host_single_radio = QRadioButton("단일 호스트")
        self.host_single_radio.setChecked(True)
        self.host_multiple_radio = QRadioButton("복수 호스트")
        host_selection.addWidget(self.host_single_radio)
        host_selection.addWidget(self.host_multiple_radio)
        host_layout.addLayout(host_selection)
        
        # 단일 호스트 입력
        self.single_host_widget = QWidget()
        single_host_layout = QHBoxLayout()
        single_host_layout.setContentsMargins(0, 0, 0, 0)
        single_host_label = QLabel("대상 IP/호스트:")
        self.single_host_input = QLineEdit()
        self.single_host_input.setPlaceholderText("예: 192.168.1.1 또는 example.com")
        single_host_layout.addWidget(single_host_label)
        single_host_layout.addWidget(self.single_host_input)
        self.single_host_widget.setLayout(single_host_layout)
        
        # 복수 호스트 입력
        self.multiple_hosts_widget = QWidget()
        multiple_hosts_layout = QVBoxLayout()
        multiple_hosts_layout.setContentsMargins(0, 0, 0, 0)
        multiple_hosts_label = QLabel("대상 IP/호스트 목록 (한 줄에 하나씩):")
        self.multiple_hosts_input = QTextEdit()
        self.multiple_hosts_input.setPlaceholderText("예:\n192.168.1.1\n192.168.1.2\nexample.com")
        self.multiple_hosts_input.setMaximumHeight(100)
        multiple_hosts_layout.addWidget(multiple_hosts_label)
        multiple_hosts_layout.addWidget(self.multiple_hosts_input)
        self.multiple_hosts_widget.setLayout(multiple_hosts_layout)
        
        # 초기 상태 설정
        self.multiple_hosts_widget.setVisible(False)
        
        # 호스트 선택 방식 변경 시 UI 업데이트
        self.host_single_radio.toggled.connect(self.toggle_host_input)
        self.host_multiple_radio.toggled.connect(self.toggle_host_input)
        
        host_layout.addWidget(self.single_host_widget)
        host_layout.addWidget(self.multiple_hosts_widget)
        host_group.setLayout(host_layout)
        input_layout.addWidget(host_group)
        
        # 포트 입력 영역
        port_group = QGroupBox("포트 설정")
        port_layout = QVBoxLayout()
        
        # 포트 선택 방식
        self.port_single_radio = QRadioButton("단일 포트")
        self.port_single_radio.setChecked(True)
        self.port_range_radio = QRadioButton("포트 범위")
        self.port_list_radio = QRadioButton("포트 목록")
        
        port_selection = QHBoxLayout()
        port_selection.addWidget(self.port_single_radio)
        port_selection.addWidget(self.port_range_radio)
        port_selection.addWidget(self.port_list_radio)
        port_layout.addLayout(port_selection)
        
        # 단일 포트 입력
        self.single_port_widget = QWidget()
        single_port_layout = QHBoxLayout()
        single_port_layout.setContentsMargins(0, 0, 0, 0)
        single_port_label = QLabel("포트:")
        self.single_port_input = QSpinBox()
        self.single_port_input.setRange(1, 65535)
        self.single_port_input.setValue(80)
        single_port_layout.addWidget(single_port_label)
        single_port_layout.addWidget(self.single_port_input)
        self.single_port_widget.setLayout(single_port_layout)
        
        # 포트 범위 입력
        self.port_range_widget = QWidget()
        port_range_layout = QHBoxLayout()
        port_range_layout.setContentsMargins(0, 0, 0, 0)
        port_range_from_label = QLabel("시작 포트:")
        self.port_range_from = QSpinBox()
        self.port_range_from.setRange(1, 65535)
        self.port_range_from.setValue(80)
        port_range_to_label = QLabel("종료 포트:")
        self.port_range_to = QSpinBox()
        self.port_range_to.setRange(1, 65535)
        self.port_range_to.setValue(100)
        port_range_layout.addWidget(port_range_from_label)
        port_range_layout.addWidget(self.port_range_from)
        port_range_layout.addWidget(port_range_to_label)
        port_range_layout.addWidget(self.port_range_to)
        self.port_range_widget.setLayout(port_range_layout)
        
        # 포트 목록 입력
        self.port_list_widget = QWidget()
        port_list_layout = QVBoxLayout()
        port_list_layout.setContentsMargins(0, 0, 0, 0)
        port_list_label = QLabel("포트 목록 (쉼표로 구분):")
        self.port_list_input = QLineEdit()
        self.port_list_input.setPlaceholderText("예: 80,443,3389,8080")
        port_list_layout.addWidget(port_list_label)
        port_list_layout.addWidget(self.port_list_input)
        self.port_list_widget.setLayout(port_list_layout)
        
        # 초기 상태 설정 (단일 포트만 표시)
        self.port_range_widget.setVisible(False)
        self.port_list_widget.setVisible(False)
        
        # 포트 선택 방식 변경 시 UI 업데이트
        self.port_single_radio.toggled.connect(self.toggle_port_input)
        self.port_range_radio.toggled.connect(self.toggle_port_input)
        self.port_list_radio.toggled.connect(self.toggle_port_input)
        
        port_layout.addWidget(self.single_port_widget)
        port_layout.addWidget(self.port_range_widget)
        port_layout.addWidget(self.port_list_widget)
        port_group.setLayout(port_layout)
        input_layout.addWidget(port_group)
        
        # TCPing 옵션 설정
        options_group = QGroupBox("TCPing 옵션")
        options_layout = QFormLayout()
        
        # 간격 설정
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 60)
        self.interval_input.setValue(1)
        self.interval_input.setSuffix(" 초")
        options_layout.addRow("간격:", self.interval_input)
        
        # 타임아웃 설정
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 30)
        self.timeout_input.setValue(3)
        self.timeout_input.setSuffix(" 초")
        options_layout.addRow("타임아웃:", self.timeout_input)
        
        # 반복 횟수 설정
        repeat_layout = QHBoxLayout()
        self.repeat_input = QSpinBox()
        self.repeat_input.setRange(1, 999)
        self.repeat_input.setValue(4)
        self.unlimited_repeat = QCheckBox("무제한")
        self.unlimited_repeat.stateChanged.connect(lambda state: self.repeat_input.setEnabled(not state))
        repeat_layout.addWidget(self.repeat_input)
        repeat_layout.addWidget(self.unlimited_repeat)
        options_layout.addRow("반복 횟수:", repeat_layout)
        
        # 병렬 실행 설정
        self.parallel_execution = QCheckBox("모든 호스트 동시 테스트")
        self.parallel_execution.setChecked(True)
        self.parallel_execution.setToolTip("체크하면 모든 호스트를 동시에 테스트합니다. 해제하면 순차적으로 테스트합니다.")
        options_layout.addRow("실행 방식:", self.parallel_execution)
        
        options_group.setLayout(options_layout)
        input_layout.addWidget(options_group)
        
        input_widget.setLayout(input_layout)
        
        # 결과 표시 영역
        result_widget = QWidget()
        result_layout = QVBoxLayout()
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("TCPing 테스트 결과가 여기에 표시됩니다.")
        
        # 결과 필터 옵션
        filter_layout = QHBoxLayout()
        filter_label = QLabel("결과 필터:")
        self.show_all_results = QRadioButton("모든 결과")
        self.show_all_results.setChecked(True)
        self.show_open_only = QRadioButton("열린 포트만")
        self.show_closed_only = QRadioButton("닫힌 포트만")
        
        self.show_all_results.toggled.connect(self.apply_result_filter)
        self.show_open_only.toggled.connect(self.apply_result_filter)
        self.show_closed_only.toggled.connect(self.apply_result_filter)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.show_all_results)
        filter_layout.addWidget(self.show_open_only)
        filter_layout.addWidget(self.show_closed_only)
        filter_layout.addStretch()
        
        result_layout.addLayout(filter_layout)
        result_layout.addWidget(self.result_display)
        result_widget.setLayout(result_layout)
        
        splitter.addWidget(input_widget)
        splitter.addWidget(result_widget)
        splitter.setSizes([300, 400])  # 초기 크기 설정
        
        layout.addWidget(splitter)
        
        # 컨트롤 버튼 영역
        control_layout = QHBoxLayout()
        
        self.tcping_button = QPushButton("TCPing 시작")
        self.tcping_button.clicked.connect(self.run_tcping_test)
        control_layout.addWidget(self.tcping_button)
        
        self.stop_button = QPushButton("중지")
        self.stop_button.clicked.connect(self.stop_tcping_test)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        # 진행 상황 막대
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar, 2)  # 진행 상황 막대가 더 많은 공간 차지
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_results)
        control_layout.addWidget(clear_button)
        
        # 결과 저장 버튼
        save_button = QPushButton("결과 저장")
        save_button.clicked.connect(self.save_results)
        control_layout.addWidget(save_button)
        
        layout.addLayout(control_layout)
        self.setLayout(layout)
        
        # 모든 테스트 결과 저장 (필터링용)
        self.all_results = []

    def toggle_host_input(self):
        """호스트 입력 방식에 따라 UI 표시 설정"""
        self.single_host_widget.setVisible(self.host_single_radio.isChecked())
        self.multiple_hosts_widget.setVisible(self.host_multiple_radio.isChecked())

    def toggle_port_input(self):
        """포트 입력 방식에 따라 UI 표시 설정"""
        self.single_port_widget.setVisible(self.port_single_radio.isChecked())
        self.port_range_widget.setVisible(self.port_range_radio.isChecked())
        self.port_list_widget.setVisible(self.port_list_radio.isChecked())

    def run_tcping_test(self):
        """TCPing 테스트 실행"""
        # 호스트 목록 가져오기
        hosts = []
        if self.host_single_radio.isChecked():
            host = self.single_host_input.text().strip()
            if host:
                hosts.append(host)
        else:  # 복수 호스트
            host_text = self.multiple_hosts_input.toPlainText().strip()
            if host_text:
                for line in host_text.splitlines():
                    host = line.strip()
                    if host:
                        hosts.append(host)
        
        if not hosts:
            self.result_display.append("<font color='red'>Error: 대상 IP/호스트를 입력하세요.</font>")
            return
        
        # 포트 목록 생성
        ports = []
        if self.port_single_radio.isChecked():
            ports = [self.single_port_input.value()]
        elif self.port_range_radio.isChecked():
            start_port = self.port_range_from.value()
            end_port = self.port_range_to.value()
            if start_port > end_port:
                self.result_display.append("<font color='red'>Error: 시작 포트는 종료 포트보다 작아야 합니다.</font>")
                return
            ports = list(range(start_port, end_port + 1))
        elif self.port_list_radio.isChecked():
            try:
                port_text = self.port_list_input.text().strip()
                if not port_text:
                    self.result_display.append("<font color='red'>Error: 포트 목록을 입력하세요.</font>")
                    return
                
                # 쉼표로 구분된 포트 목록 파싱
                port_items = [item.strip() for item in port_text.split(',')]
                for item in port_items:
                    if item:
                        ports.append(int(item))
            except ValueError:
                self.result_display.append("<font color='red'>Error: 잘못된 포트 형식입니다. 숫자만 입력하세요.</font>")
                return
        
        if not ports:
            self.result_display.append("<font color='red'>Error: 포트가 지정되지 않았습니다.</font>")
            return
        
        # 옵션 설정 가져오기
        interval = self.interval_input.value()
        timeout = self.timeout_input.value()
        
        if self.unlimited_repeat.isChecked():
            repeat = 0  # 0은 무제한을 의미
        else:
            repeat = self.repeat_input.value()
        
        # UI 업데이트
        self.tcping_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.result_display.clear()
        self.all_results = []  # 결과 초기화
        
        # 병렬 또는 순차 실행
        parallel = self.parallel_execution.isChecked()
        
        # 진행 상황 표시
        total_tasks = len(hosts) * len(ports) * (repeat if repeat > 0 else 10)  # 무제한인 경우 임의의 값
        self.progress_bar.setRange(0, total_tasks)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.completed_tasks = 0
        
        self.result_display.append(f"<b>TCPing 테스트 시작</b>")
        self.result_display.append(f"<b>대상 호스트:</b> {', '.join(hosts)}")
        self.result_display.append(f"<b>테스트 포트:</b> {', '.join(map(str, ports))}")
        self.result_display.append(f"<b>{'병렬' if parallel else '순차'} 실행 모드</b>")
        self.result_display.append("-" * 50)
        
        # 스레드 관리를 위한 리스트 초기화
        self.tcping_threads = []
        
        if parallel:
            # 병렬 실행 (모든 호스트에 대해 동시에 스레드 생성)
            for host in hosts:
                thread = TCPingThread(host, ports, interval, timeout, repeat)
                thread.result_ready.connect(self.update_result)
                thread.finished.connect(lambda host=host: self.on_host_finished(host))
                self.tcping_threads.append(thread)
                thread.start()
        else:
            # 순차 실행을 위한 호스트 및 파라미터 저장
            self.sequential_hosts = hosts.copy()
            self.sequential_params = {
                "ports": ports,
                "interval": interval,
                "timeout": timeout,
                "repeat": repeat
            }
            # 첫 번째 호스트 테스트 시작
            self.start_next_host_test()

    def start_next_host_test(self):
        """순차 실행 모드에서 다음 호스트 테스트 시작"""
        if not self.sequential_hosts:
            # 모든 호스트 테스트 완료
            self.on_tcping_finished()
            return
        
        # 다음 호스트 가져오기
        host = self.sequential_hosts.pop(0)
        
        # 해당 호스트에 대한 테스트 시작
        thread = TCPingThread(
            host, 
            self.sequential_params["ports"], 
            self.sequential_params["interval"], 
            self.sequential_params["timeout"], 
            self.sequential_params["repeat"]
        )
        thread.result_ready.connect(self.update_result)
        thread.finished.connect(lambda: self.on_sequential_host_finished(host))
        self.tcping_threads.append(thread)
        thread.start()

    def on_sequential_host_finished(self, host):
        """순차 실행 모드에서 호스트 테스트 완료 처리"""
        self.result_display.append(f"<b>호스트 {host} 테스트 완료</b>")
        self.result_display.append("-" * 50)
        
        # 다음 호스트 테스트 시작
        self.start_next_host_test()

    def stop_tcping_test(self):
        """TCPing 테스트 중지"""
        for thread in self.tcping_threads:
            if thread.isRunning():
                thread.stop()
        
        self.result_display.append("<b>TCPing 테스트가 중지되었습니다.</b>")
        self.tcping_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    def on_host_finished(self, host):
        """호스트 테스트 완료 처리"""
        # 모든 스레드가 종료되었는지 확인
        if not any(thread.isRunning() for thread in self.tcping_threads):
            self.on_tcping_finished()

    def on_tcping_finished(self):
        """TCPing 테스트 완료 처리"""
        self.tcping_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.result_display.append("<b>TCPing 테스트가 완료되었습니다.</b>")
        
        # 결과 요약 표시
        self.show_summary()

    def update_result(self, host, port, result, color, time_ms=None):
        """TCPing 결과 업데이트"""
        # 진행 상황 업데이트
        if port is not None:  # 포트 결과인 경우에만
            self.completed_tasks += 1
            self.progress_bar.setValue(self.completed_tasks)
        
        # 결과 저장 (필터링용)
        if port is not None:
            is_open = "Open" in result
            result_item = {
                "host": host,
                "port": port,
                "result": result,
                "color": color,
                "time_ms": time_ms,
                "is_open": is_open
            }
            self.all_results.append(result_item)
        
        # 현재 필터 설정에 따라 결과 표시 여부 결정
        if port is None:
            # 반복 회차 등의 정보는 항상 표시
            self.result_display.append(f"<font color='{color}'>{result}</font>")
        else:
            show_result = True
            if self.show_open_only.isChecked():
                show_result = "Open" in result
            elif self.show_closed_only.isChecked():
                show_result = "Open" not in result
            
            if show_result:
                if time_ms is not None:
                    self.result_display.append(f"<b>{host}:{port}</b> - <font color='{color}'>{result}</font> ({time_ms}ms)")
                else:
                    self.result_display.append(f"<b>{host}:{port}</b> - <font color='{color}'>{result}</font>")

    def apply_result_filter(self):
        """현재 필터 설정에 따라 결과 표시 갱신"""
        # 결과가 없으면 아무 작업도 하지 않음
        if not self.all_results:
            return
        
        # 결과 표시 영역 초기화
        self.result_display.clear()
        
        # 헤더 정보 다시 표시
        self.result_display.append("<b>TCPing 테스트 결과</b> (필터 적용됨)")
        
        # 필터 적용하여 결과 표시
        for item in self.all_results:
            show_result = True
            if self.show_open_only.isChecked():
                show_result = item["is_open"]
            elif self.show_closed_only.isChecked():
                show_result = not item["is_open"]
            
            if show_result:
                host = item["host"]
                port = item["port"]
                result = item["result"]
                color = item["color"]
                time_ms = item["time_ms"]
                
                if time_ms is not None:
                    self.result_display.append(f"<b>{host}:{port}</b> - <font color='{color}'>{result}</font> ({time_ms}ms)")
                else:
                    self.result_display.append(f"<b>{host}:{port}</b> - <font color='{color}'>{result}</font>")

    def show_summary(self):
        """테스트 결과 요약 표시"""
        if not self.all_results:
            return
        
        self.result_display.append("\n<b>== 테스트 결과 요약 ==</b>")
        
        # 호스트별 통계
        host_stats = {}
        for item in self.all_results:
            host = item["host"]
            port = item["port"]
            is_open = item["is_open"]
            
            if host not in host_stats:
                host_stats[host] = {"total": 0, "open": 0, "closed": 0, "open_ports": []}
            
            host_stats[host]["total"] += 1
            if is_open:
                host_stats[host]["open"] += 1
                if port not in host_stats[host]["open_ports"]:
                    host_stats[host]["open_ports"].append(port)
            else:
                host_stats[host]["closed"] += 1
        
        # 요약 정보 표시
        for host, stats in host_stats.items():
            total = stats["total"]
            open_count = stats["open"]
            open_percent = (open_count / total) * 100 if total > 0 else 0
            
            self.result_display.append(f"<b>호스트:</b> {host}")
            self.result_display.append(f"총 테스트 포트: {total}개")
            self.result_display.append(f"열린 포트: {open_count}개 ({open_percent:.1f}%)")
            
            if open_count > 0:
                open_ports = ", ".join(map(str, sorted(stats["open_ports"])))
                self.result_display.append(f"열린 포트 목록: {open_ports}")
            
            self.result_display.append("")

    def clear_results(self):
        """결과 표시 영역 초기화"""
        self.result_display.clear()
        self.all_results = []

    def save_results(self):
        """테스트 결과를 파일로 저장"""
        if not self.all_results:
            QMessageBox.warning(self, "저장 오류", "저장할 결과가 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "결과 저장", "", "텍스트 파일 (*.txt);;HTML 파일 (*.html);;CSV 파일 (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # 파일 확장자에 따라 저장 방식 결정
            if file_path.endswith('.html'):
                self.save_as_html(file_path)
            elif file_path.endswith('.csv'):
                self.save_as_csv(file_path)
            else:  # 기본 텍스트 파일
                self.save_as_text(file_path)
                
            QMessageBox.information(self, "저장 완료", f"테스트 결과가 {file_path}에 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류가 발생했습니다: {e}")

    def save_as_text(self, file_path):
        """결과를 텍스트 파일로 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("TCPing 테스트 결과\n")
            f.write("=" * 50 + "\n\n")
            
            # 결과 요약
            f.write("== 테스트 결과 요약 ==\n")
            
            # 호스트별 통계
            host_stats = {}
            for item in self.all_results:
                host = item["host"]
                port = item["port"]
                is_open = item["is_open"]
                
                if host not in host_stats:
                    host_stats[host] = {"total": 0, "open": 0, "closed": 0, "open_ports": []}
                
                host_stats[host]["total"] += 1
                if is_open:
                    host_stats[host]["open"] += 1
                    if port not in host_stats[host]["open_ports"]:
                        host_stats[host]["open_ports"].append(port)
                else:
                    host_stats[host]["closed"] += 1
            
            # 요약 정보 표시
            for host, stats in host_stats.items():
                total = stats["total"]
                open_count = stats["open"]
                open_percent = (open_count / total) * 100 if total > 0 else 0
                
                f.write(f"호스트: {host}\n")
                f.write(f"총 테스트 포트: {total}개\n")
                f.write(f"열린 포트: {open_count}개 ({open_percent:.1f}%)\n")
                
                if open_count > 0:
                    open_ports = ", ".join(map(str, sorted(stats["open_ports"])))
                    f.write(f"열린 포트 목록: {open_ports}\n")
                
                f.write("\n")
            
            # 상세 결과
            f.write("\n== 상세 테스트 결과 ==\n")
            
            # 현재 선택된 필터에 따라 결과 출력
            show_open = not self.show_closed_only.isChecked()
            show_closed = not self.show_open_only.isChecked()
            
            for item in self.all_results:
                host = item["host"]
                port = item["port"]
                result = item["result"]
                time_ms = item["time_ms"]
                is_open = item["is_open"]
                
                if (is_open and show_open) or (not is_open and show_closed):
                    result_line = f"{host}:{port} - {result}"
                    if time_ms is not None:
                        result_line += f" ({time_ms}ms)"
                    f.write(result_line + "\n")

    def save_as_html(self, file_path):
        """결과를 HTML 파일로 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TCPing 테스트 결과</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #0066cc; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .open { color: green; }
        .closed { color: red; }
        .summary { margin-bottom: 30px; }
    </style>
</head>
<body>
    <h1>TCPing 테스트 결과</h1>
""")
            
            # 결과 요약
            f.write("<h2>테스트 결과 요약</h2>")
            f.write("<div class='summary'>")
            
            # 호스트별 통계
            host_stats = {}
            for item in self.all_results:
                host = item["host"]
                port = item["port"]
                is_open = item["is_open"]
                
                if host not in host_stats:
                    host_stats[host] = {"total": 0, "open": 0, "closed": 0, "open_ports": []}
                
                host_stats[host]["total"] += 1
                if is_open:
                    host_stats[host]["open"] += 1
                    if port not in host_stats[host]["open_ports"]:
                        host_stats[host]["open_ports"].append(port)
                else:
                    host_stats[host]["closed"] += 1
            
            # 요약 테이블
            f.write("<table>")
            f.write("<tr><th>호스트</th><th>총 테스트 포트</th><th>열린 포트</th><th>열린 포트 목록</th></tr>")
            
            for host, stats in host_stats.items():
                total = stats["total"]
                open_count = stats["open"]
                open_percent = (open_count / total) * 100 if total > 0 else 0
                
                f.write(f"<tr>")
                f.write(f"<td>{host}</td>")
                f.write(f"<td>{total}개</td>")
                f.write(f"<td>{open_count}개 ({open_percent:.1f}%)</td>")
                
                if open_count > 0:
                    open_ports = ", ".join(map(str, sorted(stats["open_ports"])))
                    f.write(f"<td>{open_ports}</td>")
                else:
                    f.write("<td>-</td>")
                
                f.write("</tr>")
            
            f.write("</table>")
            f.write("</div>")
            
            # 상세 결과
            f.write("<h2>상세 테스트 결과</h2>")
            
            # 현재 선택된 필터에 따른 안내
            show_open = not self.show_closed_only.isChecked()
            show_closed = not self.show_open_only.isChecked()
            
            if not show_open:
                f.write("<p><i>열린 포트 결과는 제외되었습니다.</i></p>")
            elif not show_closed:
                f.write("<p><i>닫힌 포트 결과는 제외되었습니다.</i></p>")
            
            # 결과 테이블
            f.write("<table>")
            f.write("<tr><th>호스트</th><th>포트</th><th>결과</th><th>응답 시간</th></tr>")
            
            for item in self.all_results:
                host = item["host"]
                port = item["port"]
                result = item["result"]
                time_ms = item["time_ms"]
                is_open = item["is_open"]
                
                if (is_open and show_open) or (not is_open and show_closed):
                    f.write("<tr>")
                    f.write(f"<td>{host}</td>")
                    f.write(f"<td>{port}</td>")
                    
                    result_class = "open" if is_open else "closed"
                    f.write(f"<td class='{result_class}'>{result}</td>")
                    
                    if time_ms is not None:
                        f.write(f"<td>{time_ms}ms</td>")
                    else:
                        f.write("<td>-</td>")
                    
                    f.write("</tr>")
            
            f.write("</table>")
            
            f.write("""
</body>
</html>
""")

    def save_as_csv(self, file_path):
        """결과를 CSV 파일로 저장"""
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            import csv
            
            writer = csv.writer(f)
            writer.writerow(["호스트", "포트", "결과", "상태", "응답시간(ms)"])
            
            # 현재 선택된 필터에 따라 결과 출력
            show_open = not self.show_closed_only.isChecked()
            show_closed = not self.show_open_only.isChecked()
            
            for item in self.all_results:
                host = item["host"]
                port = item["port"]
                result = item["result"]
                time_ms = item["time_ms"] if item["time_ms"] is not None else ""
                is_open = item["is_open"]
                status = "Open" if is_open else "Closed"
                
                if (is_open and show_open) or (not is_open and show_closed):
                    writer.writerow([host, port, result, status, time_ms])