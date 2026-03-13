import sys
import os
import logging
import re
import tempfile
import csv
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QGroupBox, QFormLayout, QProgressBar, QCheckBox,
    QFileDialog, QMessageBox, QComboBox, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QPlainTextEdit, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QColor

# PDF 생성을 위한 라이브러리
try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# 기존 모듈들 import
try:
    from workers import NetworkWorker
except ImportError:
    try:
        from core.workers import NetworkWorker
    except ImportError:
        print("NetworkWorker 모듈을 찾을 수 없습니다. workers.py 파일이 있는지 확인하세요.")


class MultiDeviceAnalysisWorker(QThread):
    """다중 장비 분석을 위한 워커 쓰레드"""
    progress_updated = pyqtSignal(int, str, str)  # 전체진행률, 현재작업, 장비IP
    device_completed = pyqtSignal(dict)           # 개별 장비 분석 완료
    all_completed = pyqtSignal(list)              # 전체 분석 완료
    error_occurred = pyqtSignal(str, str)         # 장비IP, 오류메시지
    
    def __init__(self, device_list, common_credentials, max_workers=10):
        super().__init__()
        self.device_list = device_list  # [{'ip': '...', 'username': '...', 'password': '...', ...}, ...]
        self.common_credentials = common_credentials
        self.max_workers = min(max_workers, len(device_list))
        self._stop_flag = False
        self.results = []
        
        # 분석에 필요한 명령어들
        self.analysis_commands = [
            "terminal length 0",
            "show version",
            "show running-config | include hostname",
            "show processes cpu sorted | head 10",
            "show memory statistics",
            "show ip interface brief",
            "show environment all",
            "show inventory",
            "show clock", 
            "show logging | last 20"  # 로그 수를 줄여서 성능 향상
        ]
    
    def stop(self):
        self._stop_flag = True
    
    def run(self):
        try:
            total_devices = len(self.device_list)
            completed_count = 0
            
            # 병렬 처리로 여러 장비 동시 분석
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 모든 장비에 대해 작업 제출
                future_to_device = {
                    executor.submit(self.analyze_single_device, device): device 
                    for device in self.device_list
                }
                
                # 완료된 작업들 처리
                for future in as_completed(future_to_device):
                    if self._stop_flag:
                        break
                        
                    device = future_to_device[future]
                    completed_count += 1
                    
                    try:
                        result = future.result()
                        if result:
                            self.results.append(result)
                            self.device_completed.emit(result)
                        
                        # 진행률 업데이트
                        progress = int((completed_count / total_devices) * 100)
                        self.progress_updated.emit(
                            progress, 
                            f"분석 완료: {completed_count}/{total_devices}",
                            device['ip']
                        )
                        
                    except Exception as e:
                        self.error_occurred.emit(device['ip'], str(e))
            
            # 전체 분석 완료
            if not self._stop_flag:
                self.all_completed.emit(self.results)
                
        except Exception as e:
            self.error_occurred.emit("전체", f"전체 분석 중 오류: {str(e)}")
    
    def analyze_single_device(self, device):
        """단일 장비 분석"""
        try:
            # 공통 설정과 개별 설정 병합
            config = {**self.common_credentials, **device}
            
            # NetworkWorker를 사용해서 명령어 실행
            temp_dir = tempfile.mkdtemp()
            worker = NetworkWorker(
                config['ip'], 
                config['username'], 
                config['password'], 
                config.get('enable_password', ''),
                config.get('use_ssh', True), 
                temp_dir, 
                self.analysis_commands,
                config.get('ssh_port', 22)
            )
            
            if self._stop_flag:
                return None
            
            # 연결 및 명령어 실행
            if config.get('use_ssh', True):
                output_data = worker.connect_via_ssh()
            else:
                output_data = worker.connect_via_telnet()
            
            if self._stop_flag:
                return None
            
            # 데이터 분석
            analysis_result = self.analyze_output_data(output_data, config['ip'])
            
            # 로그 분석
            log_analysis = self.analyze_logs(output_data.get("show logging | last 20", ""))
            analysis_result['log_analysis'] = log_analysis
            
            return analysis_result
            
        except Exception as e:
            # 실패한 장비도 결과에 포함 (실패 정보와 함께)
            return {
                'ip': device['ip'],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'FAILED',
                'error': str(e),
                'hostname': 'N/A',
                'model': 'N/A',
                'serial_number': 'N/A',
                'os_version': 'N/A',
                'uptime': 'N/A',
                'cpu_usage': 'N/A',
                'memory_usage': 'N/A',
                'interface_up_count': 0,
                'interface_down_count': 0,
                'environment_status': 'N/A',
                'log_issues': 0
            }
    
    def analyze_output_data(self, output_data, ip):
        """출력 데이터를 분석하여 요약 정보 추출 (간결화)"""
        result = {
            'ip': ip,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'SUCCESS',
            'hostname': 'N/A',
            'model': 'N/A',
            'serial_number': 'N/A',
            'os_version': 'N/A',
            'uptime': 'N/A',
            'cpu_usage': 'N/A',
            'memory_usage': 'N/A',
            'interface_up_count': 0,
            'interface_down_count': 0,
            'environment_status': 'N/A',
            'log_issues': 0,
            'raw_data': output_data
        }
        
        # show version 분석
        version_output = output_data.get("show version", "")
        if version_output:
            result.update(self.parse_show_version(version_output))
        
        # hostname 분석
        hostname_output = output_data.get("show running-config | include hostname", "")
        if hostname_output:
            hostname_match = re.search(r"hostname\s+(\S+)", hostname_output)
            if hostname_match:
                result['hostname'] = hostname_match.group(1)
        
        # CPU 분석 (간결화)
        cpu_output = output_data.get("show processes cpu sorted | head 10", "")
        if cpu_output:
            cpu_usage = self.parse_cpu_usage(cpu_output)
            result['cpu_usage'] = cpu_usage if cpu_usage != "N/A" else "N/A"
        
        # 메모리 분석 (간결화)
        memory_output = output_data.get("show memory statistics", "")
        if memory_output:
            memory_info = self.parse_memory_info(memory_output)
            if memory_info and 'usage_percent' in memory_info:
                result['memory_usage'] = f"{memory_info['usage_percent']}%"
        
        # 인터페이스 분석 (카운트만)
        interface_output = output_data.get("show ip interface brief", "")
        if interface_output:
            up_count, down_count = self.count_interfaces(interface_output)
            result['interface_up_count'] = up_count
            result['interface_down_count'] = down_count
        
        # 환경 상태 분석 (간결화)
        env_output = output_data.get("show environment all", "")
        if env_output:
            env_status = self.parse_environment_simple(env_output)
            result['environment_status'] = env_status
        
        return result
    
    def parse_show_version(self, output):
        """show version 출력 파싱 (간결화)"""
        result = {}
        
        # OS 버전
        version_patterns = [
            r"Version\s+([\d\.\(\)A-Z]+)",
            r"IOS\s+Software.*Version\s+([\d\.\(\)A-Z]+)"
        ]
        for pattern in version_patterns:
            version_match = re.search(pattern, output)
            if version_match:
                result['os_version'] = version_match.group(1)
                break
        
        # 모델
        model_patterns = [
            r"Model number\s+:\s+(\S+)",
            r"cisco\s+(\S+)\s+\(",
            r"\b(C\d{4,})\b",
            r"(\w+)\s+processor"
        ]
        for pattern in model_patterns:
            model_match = re.search(pattern, output, re.IGNORECASE)
            if model_match:
                result['model'] = model_match.group(1)
                break
        
        # 시리얼 번호
        serial_patterns = [
            r"Processor board ID\s+(\S+)",
            r"Serial Number\s+:\s+(\S+)",
            r"System serial number\s+:\s+(\S+)"
        ]
        for pattern in serial_patterns:
            serial_match = re.search(pattern, output, re.IGNORECASE)
            if serial_match:
                result['serial_number'] = serial_match.group(1)
                break
        
        # 업타임 (간결화)
        uptime_match = re.search(r"uptime is (.+)", output)
        if uptime_match:
            uptime = uptime_match.group(1).strip()
            # 업타임을 간결하게 표시
            if 'week' in uptime and 'day' in uptime:
                result['uptime'] = re.sub(r'\b\d+ minutes?\b', '', uptime).strip()
            else:
                result['uptime'] = uptime
        
        return result
    
    def parse_cpu_usage(self, output):
        """CPU 사용률 파싱"""
        cpu_patterns = [
            r"CPU utilization for five seconds:\s*(\d+)%",
            r"CPU utilization:\s*(\d+)%"
        ]
        
        for pattern in cpu_patterns:
            cpu_match = re.search(pattern, output)
            if cpu_match:
                return f"{cpu_match.group(1)}%"
        
        return "N/A"
    
    def parse_memory_info(self, output):
        """메모리 정보 파싱 (간결화)"""
        patterns = [
            r"Processor Pool Total:\s+(\d+)\s+Used:\s+(\d+)\s+Free:\s+(\d+)",
            r"System memory\s*:\s*(\d+)K total,\s*(\d+)K used,\s*(\d+)K free"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                total, used, free = map(int, match.groups())
                usage_percent = round((used / total) * 100, 1) if total > 0 else 0
                return {'usage_percent': usage_percent}
        
        return {}
    
    def count_interfaces(self, output):
        """인터페이스 up/down 개수 카운트"""
        lines = output.split('\n')
        up_count = 0
        down_count = 0
        
        for line in lines:
            # 인터페이스 라인 패턴 매칭
            if_match = re.match(r'(\S+)\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)', line.strip())
            if if_match:
                interface, ip, status, protocol = if_match.groups()
                if status.lower() == 'up' and protocol.lower() == 'up':
                    up_count += 1
                else:
                    down_count += 1
        
        return up_count, down_count
    
    def parse_environment_simple(self, output):
        """환경 상태 간단 파싱"""
        if 'fail' in output.lower() or 'critical' in output.lower():
            return 'Critical'
        elif 'warning' in output.lower() or 'warn' in output.lower():
            return 'Warning'
        elif 'ok' in output.lower() or 'good' in output.lower() or 'normal' in output.lower():
            return 'Good'
        else:
            return 'Unknown'
    
    def analyze_logs(self, log_output):
        """개선된 로그 분석 (가중치 시스템)"""
        if not log_output:
            return {'total_issues': 0, 'critical': 0, 'errors': 0, 'warnings': 0, 'summary': 'No logs available'}
        
        # 심각도별 패턴 정의 (실제 Cisco 환경 기반)
        patterns = {
            'critical': [
                r'%SYS-\d-RELOAD',           # 시스템 재부팅
                r'%SYS-\d-RESTART',          # 시스템 재시작  
                r'%TEMP_ALARM-\d-',          # 온도 알람
                r'%FAN_FAILED-\d-',          # 팬 실패
                r'%POWER_ETHERNET-\d-DENY',  # 전원 문제
                r'%EMERGENCY',               # 긴급 상황
                r'%CRITICAL',                # 크리티컬 이벤트
            ],
            'high': [
                r'%LINK-\d-DOWN',            # 인터페이스 다운
                r'%LINEPROTO-\d-DOWN',       # 프로토콜 다운
                r'%OSPF-\d-ADJCHG.*Down',    # OSPF 인접 관계 중단
                r'%BGP-\d-ADJCHANGE.*Down',  # BGP 인접 관계 중단
                r'%SPANTREE-\d-ROOTCHANGE',  # 스패닝 트리 루트 변경
                r'%ERROR',                   # 일반 오류
                r'%FAIL',                    # 실패 이벤트
            ],
            'medium': [
                r'%LINK-\d-UPDOWN',          # 인터페이스 플래핑
                r'%SEC_LOGIN-\d-LOGIN_FAILED', # 로그인 실패
                r'%AUTHMGR-\d-FAIL',         # 인증 실패
                r'%CDP-\d-DUPLEX_MISMATCH',  # 듀플렉스 불일치
                r'%DHCP_SNOOPING-\d-DHCP_SNOOPING_DENY', # DHCP 스누핑 거부
                r'%WARNING',                 # 경고
                r'%WARN',                    # 경고
            ]
        }
        
        # 가중치 시스템
        weights = {'critical': 10, 'high': 7, 'medium': 4}
        
        # 패턴 분석
        counts = {'critical': 0, 'high': 0, 'medium': 0}
        total_score = 0
        
        for severity, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = len(re.findall(pattern, log_output, re.IGNORECASE))
                counts[severity] += matches
                total_score += matches * weights[severity]
        
        # 특별 패턴 분석 (추가 점수)
        special_issues = 0
        
        # 인터페이스 플래핑 (심각도 증가)
        flapping_count = len(re.findall(r'%LINK-\d-UPDOWN.*interface.*changed state', log_output, re.IGNORECASE))
        if flapping_count > 3:
            special_issues += flapping_count * 2  # 플래핑은 심각도 증가
        
        # 반복되는 인증 실패 (보안 위험)
        auth_fails = len(re.findall(r'%SEC_LOGIN-\d-LOGIN_FAILED|%AUTHMGR-\d-FAIL', log_output, re.IGNORECASE))
        if auth_fails > 5:
            special_issues += auth_fails  # 반복 인증 실패는 보안 위험
        
        total_score += special_issues
        
        # 요약 메시지 생성
        if total_score == 0:
            summary = "No significant issues found"
        elif counts['critical'] > 0:
            summary = f"Critical issues detected! Score: {total_score}"
        elif counts['high'] > 0:
            summary = f"High priority issues found. Score: {total_score}"
        elif total_score > 10:
            summary = f"Multiple issues detected. Score: {total_score}"
        else:
            summary = f"Minor issues detected. Score: {total_score}"
        
        return {
            'total_issues': total_score,
            'critical': counts['critical'],
            'errors': counts['high'], 
            'warnings': counts['medium'],
            'summary': summary,
            'flapping_detected': flapping_count > 3,
            'auth_issues': auth_fails > 5
        }


class AutoAnalysisTab(QWidget):
    """향상된 자동 분석 탭 - 다중 장비 지원"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.analysis_worker = None
        self.analysis_results = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # === 입력 방식 선택 ===
        input_group = QGroupBox("장비 입력 방식")
        input_layout = QVBoxLayout()
        
        # 라디오 버튼 그룹
        self.input_mode_group = QButtonGroup()
        
        self.single_mode = QRadioButton("단일 장비")
        self.single_mode.setChecked(True)
        
        self.list_mode = QRadioButton("IP 목록 (한 줄에 하나씩)")
        self.csv_mode = QRadioButton("CSV 파일")
        
        self.input_mode_group.addButton(self.single_mode, 0)
        self.input_mode_group.addButton(self.list_mode, 1)
        self.input_mode_group.addButton(self.csv_mode, 2)
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.single_mode)
        mode_layout.addWidget(self.list_mode)
        mode_layout.addWidget(self.csv_mode)
        mode_layout.addStretch()
        
        input_layout.addLayout(mode_layout)
        
        # === 장비 입력 영역 ===
        # 단일 장비 입력
        self.single_input_widget = QWidget()
        single_layout = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.1")
        single_layout.addRow("장비 IP:", self.ip_input)
        
        self.single_input_widget.setLayout(single_layout)
        
        # IP 목록 입력
        self.list_input_widget = QWidget()
        list_layout = QVBoxLayout()
        list_layout.addWidget(QLabel("IP 목록 (한 줄에 하나씩):"))
        
        self.ip_list_input = QPlainTextEdit()
        self.ip_list_input.setPlaceholderText("192.168.1.1\n192.168.1.2\n192.168.1.3")
        self.ip_list_input.setMaximumHeight(100)
        list_layout.addWidget(self.ip_list_input)
        
        self.list_input_widget.setLayout(list_layout)
        self.list_input_widget.setVisible(False)
        
        # CSV 파일 입력
        self.csv_input_widget = QWidget()
        csv_layout = QHBoxLayout()
        
        self.csv_file_input = QLineEdit()
        self.csv_file_input.setPlaceholderText("CSV 파일 경로")
        self.csv_file_input.setReadOnly(True)
        
        self.browse_button = QPushButton("찾아보기")
        self.browse_button.clicked.connect(self.browse_csv_file)
        
        csv_layout.addWidget(QLabel("CSV 파일:"))
        csv_layout.addWidget(self.csv_file_input)
        csv_layout.addWidget(self.browse_button)
        
        self.csv_input_widget.setLayout(csv_layout)
        self.csv_input_widget.setVisible(False)
        
        # 입력 모드 변경 시그널 연결
        self.input_mode_group.buttonClicked.connect(self.on_input_mode_changed)
        
        input_layout.addWidget(self.single_input_widget)
        input_layout.addWidget(self.list_input_widget)
        input_layout.addWidget(self.csv_input_widget)
        
        input_group.setLayout(input_layout)
        
        # === 공통 인증 정보 ===
        auth_group = QGroupBox("공통 인증 정보")
        auth_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Enable 패스워드
        enable_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("Enable 패스워드 사용")
        self.enable_password_input = QLineEdit()
        self.enable_password_input.setEchoMode(QLineEdit.Password)
        self.enable_password_input.setEnabled(False)
        enable_layout.addWidget(self.enable_checkbox)
        enable_layout.addWidget(self.enable_password_input)
        
        self.enable_checkbox.toggled.connect(self.enable_password_input.setEnabled)
        
        # 프로토콜 선택
        protocol_layout = QHBoxLayout()
        self.ssh_checkbox = QCheckBox("SSH 사용")
        self.ssh_checkbox.setChecked(True)
        self.telnet_checkbox = QCheckBox("Telnet 사용")
        
        # SSH와 Telnet 중 하나만 선택되도록
        self.ssh_checkbox.toggled.connect(lambda checked: self.telnet_checkbox.setChecked(not checked) if checked else None)
        self.telnet_checkbox.toggled.connect(lambda checked: self.ssh_checkbox.setChecked(not checked) if checked else None)
        
        self.ssh_port_input = QSpinBox()
        self.ssh_port_input.setRange(1, 65535)
        self.ssh_port_input.setValue(22)
        
        protocol_layout.addWidget(self.ssh_checkbox)
        protocol_layout.addWidget(self.telnet_checkbox)
        protocol_layout.addWidget(QLabel("포트:"))
        protocol_layout.addWidget(self.ssh_port_input)
        protocol_layout.addStretch()
        
        auth_layout.addRow("사용자명:", self.username_input)
        auth_layout.addRow("패스워드:", self.password_input)
        auth_layout.addRow("Enable 설정:", enable_layout)
        auth_layout.addRow("연결 프로토콜:", protocol_layout)
        
        auth_group.setLayout(auth_layout)
        
        # === 분석 옵션 ===
        options_group = QGroupBox("분석 옵션")
        options_layout = QHBoxLayout()
        
        self.max_workers_input = QSpinBox()
        self.max_workers_input.setRange(1, 50)
        self.max_workers_input.setValue(10)
        self.max_workers_input.setSuffix(" 동시작업")
        
        options_layout.addWidget(QLabel("최대 동시 분석:"))
        options_layout.addWidget(self.max_workers_input)
        options_layout.addStretch()
        
        options_group.setLayout(options_layout)
        
        # === 실행 버튼 ===
        control_layout = QHBoxLayout()
        
        self.analyze_button = QPushButton("🚀 다중 장비 분석 시작")
        self.analyze_button.setMinimumHeight(40)
        self.analyze_button.clicked.connect(self.start_analysis)
        
        self.stop_button = QPushButton("⏹ 중지")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_analysis)
        
        self.export_button = QPushButton("📊 결과 내보내기")
        self.export_button.setMinimumHeight(40)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results)
        
        self.pdf_button = QPushButton("📄 PDF 보고서")
        self.pdf_button.setMinimumHeight(40)
        self.pdf_button.setEnabled(False)
        self.pdf_button.clicked.connect(self.generate_pdf_report)
        
        control_layout.addWidget(self.analyze_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.export_button)
        control_layout.addWidget(self.pdf_button)
        
        # === 진행 상태 ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.status_label = QLabel("대기 중...")
        self.current_device_label = QLabel("")
        
        # === 결과 표시 영역 ===
        results_group = QGroupBox("분석 결과")
        results_layout = QVBoxLayout()
        
        # 결과 테이블
        self.results_table = QTableWidget()
        self.setup_results_table()
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        
        # === 레이아웃 구성 ===
        layout.addWidget(input_group)
        layout.addWidget(auth_group)
        layout.addWidget(options_group)
        layout.addLayout(control_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.current_device_label)
        layout.addWidget(results_group, 1)
        
        self.setLayout(layout)
        
        # PDF 라이브러리 확인
        if not PDF_AVAILABLE:
            self.pdf_button.setEnabled(False)
            self.pdf_button.setToolTip("PDF 생성을 위해 reportlab 라이브러리가 필요합니다")
    
    def setup_results_table(self):
        """결과 테이블 설정 (텍스트 잘림 방지)"""
        headers = [
            "상태", "IP 주소", "호스트명", "모델", "OS 버전", 
            "업타임", "CPU", "메모리", "인터페이스", "환경", "로그점수", "특이사항", "오류"
        ]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        
        # 테이블 설정
        header = self.results_table.horizontalHeader()
        
        # 컬럼별 최소 너비 설정 (픽셀)
        min_widths = [60, 120, 150, 100, 120, 200, 60, 60, 80, 60, 70, 120, 200]
        for i, width in enumerate(min_widths):
            self.results_table.setColumnWidth(i, width)
        
        # 중요한 컬럼들은 고정 너비, 나머지는 내용에 맞춰 조정
        fixed_columns = [0, 1, 6, 7, 8, 9, 10]  # 상태, IP, CPU, 메모리, 인터페이스, 환경, 로그점수
        stretch_columns = [2, 3, 4, 5, 11, 12]  # 호스트명, 모델, OS버전, 업타임, 특이사항, 오류
        
        for i in range(len(headers)):
            if i in fixed_columns:
                header.setSectionResizeMode(i, QHeaderView.Fixed)
            elif i in stretch_columns:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # 테이블 기본 설정
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        self.results_table.setWordWrap(True)  # 텍스트 줄바꿈 허용
        self.results_table.verticalHeader().setDefaultSectionSize(50)  # 행 높이 증가
        self.results_table.setTextElideMode(Qt.ElideNone)  # 텍스트 생략 비활성화
    
    def on_input_mode_changed(self, button):
        """입력 모드 변경 처리"""
        mode = self.input_mode_group.id(button)
        
        self.single_input_widget.setVisible(mode == 0)
        self.list_input_widget.setVisible(mode == 1)
        self.csv_input_widget.setVisible(mode == 2)
    
    def browse_csv_file(self):
        """CSV 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CSV 파일 선택", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.csv_file_input.setText(file_path)
    
    def get_device_list(self):
        """입력 모드에 따라 장비 목록 생성"""
        mode = self.input_mode_group.checkedId()
        devices = []
        
        if mode == 0:  # 단일 장비
            ip = self.ip_input.text().strip()
            if ip:
                devices.append({'ip': ip})
        
        elif mode == 1:  # IP 목록
            ip_text = self.ip_list_input.toPlainText().strip()
            for line in ip_text.split('\n'):
                ip = line.strip()
                if ip:
                    devices.append({'ip': ip})
        
        elif mode == 2:  # CSV 파일
            csv_path = self.csv_file_input.text().strip()
            if csv_path and os.path.exists(csv_path):
                try:
                    with open(csv_path, 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            if 'ip' in row and row['ip'].strip():
                                devices.append(row)
                except Exception as e:
                    QMessageBox.warning(self, "CSV 오류", f"CSV 파일 읽기 오류: {str(e)}")
                    return []
        
        return devices
    
    def start_analysis(self):
        """다중 장비 분석 시작"""
        # 입력 검증
        device_list = self.get_device_list()
        if not device_list:
            QMessageBox.warning(self, "입력 오류", "분석할 장비를 입력하세요.")
            return
        
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "입력 오류", "사용자명을 입력하세요.")
            return
        
        if not self.password_input.text().strip():
            QMessageBox.warning(self, "입력 오류", "패스워드를 입력하세요.")
            return
        
        # 공통 인증 정보
        common_credentials = {
            'username': self.username_input.text().strip(),
            'password': self.password_input.text().strip(),
            'enable_password': self.enable_password_input.text() if self.enable_checkbox.isChecked() else "",
            'use_ssh': self.ssh_checkbox.isChecked(),
            'ssh_port': self.ssh_port_input.value()
        }
        
        # UI 상태 변경
        self.analyze_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.pdf_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 결과 테이블 초기화
        self.results_table.setRowCount(0)
        self.analysis_results = []
        
        # 분석 시작 메시지
        total_devices = len(device_list)
        self.status_label.setText(f"총 {total_devices}대 장비 분석 시작...")
        
        # 워커 쓰레드 시작
        self.analysis_worker = MultiDeviceAnalysisWorker(
            device_list=device_list,
            common_credentials=common_credentials,
            max_workers=self.max_workers_input.value()
        )
        
        # 시그널 연결
        self.analysis_worker.progress_updated.connect(self.update_progress)
        self.analysis_worker.device_completed.connect(self.device_analysis_completed)
        self.analysis_worker.all_completed.connect(self.all_analysis_completed)
        self.analysis_worker.error_occurred.connect(self.analysis_error)
        
        self.analysis_worker.start()
    
    def stop_analysis(self):
        """분석 중지"""
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.stop()
            self.analysis_worker.wait(5000)  # 5초 대기
        
        self.analyze_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("분석이 중지되었습니다.")
        self.current_device_label.setText("")
    
    def update_progress(self, value, message, current_ip):
        """진행 상태 업데이트"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.current_device_label.setText(f"현재 처리: {current_ip}")
    
    def device_analysis_completed(self, result):
        """개별 장비 분석 완료"""
        self.analysis_results.append(result)
        self.add_result_to_table(result)
    
    def all_analysis_completed(self, results):
        """전체 분석 완료"""
        self.analyze_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(True)
        if PDF_AVAILABLE:
            self.pdf_button.setEnabled(True)
        
        success_count = len([r for r in results if r.get('status') == 'SUCCESS'])
        total_count = len(results)
        
        self.status_label.setText(f"분석 완료! 성공: {success_count}/{total_count}")
        self.current_device_label.setText("")
    
    def analysis_error(self, device_ip, error_message):
        """분석 오류 처리"""
        print(f"Error analyzing {device_ip}: {error_message}")
    
    def add_result_to_table(self, result):
        """결과를 테이블에 추가 (긴 텍스트 처리 개선)"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # 상태에 따른 색상 설정
        status = result.get('status', 'UNKNOWN')
        status_item = QTableWidgetItem(status)
        
        if status == 'SUCCESS':
            status_item.setBackground(QColor(144, 238, 144))  # 연한 초록
        elif status == 'FAILED':
            status_item.setBackground(QColor(255, 182, 193))  # 연한 빨강
        
        # 로그 분석 결과에서 특이사항 추출
        log_analysis = result.get('log_analysis', {})
        special_issues = []
        
        if log_analysis.get('flapping_detected', False):
            special_issues.append("플래핑")
        if log_analysis.get('auth_issues', False):
            special_issues.append("인증실패")
        if log_analysis.get('critical', 0) > 0:
            special_issues.append("Critical")
        
        special_text = ", ".join(special_issues) if special_issues else "-"
        
        # 로그 점수 색상 설정
        log_score = log_analysis.get('total_issues', 0)
        log_score_item = QTableWidgetItem(str(log_score))
        
        if log_score >= 50:
            log_score_item.setBackground(QColor(255, 182, 193))  # 빨강 (심각)
        elif log_score >= 20:
            log_score_item.setBackground(QColor(255, 255, 0))    # 노랑 (주의)
        elif log_score > 0:
            log_score_item.setBackground(QColor(255, 235, 59))   # 연한 노랑 (경미)
        
        # 긴 텍스트 처리를 위한 함수
        def create_item_with_tooltip(text, tooltip=None):
            item = QTableWidgetItem(str(text) if text else "N/A")
            if tooltip and len(str(tooltip)) > 20:
                item.setToolTip(str(tooltip))  # 마우스 오버시 전체 텍스트 표시
            return item
        
        # 테이블 데이터 설정 (툴팁 포함)
        hostname = result.get('hostname', 'N/A')
        model = result.get('model', 'N/A')
        os_version = result.get('os_version', 'N/A')
        uptime = result.get('uptime', 'N/A')
        error_msg = result.get('error', '') if status == 'FAILED' else ''
        
        items = [
            status_item,
            create_item_with_tooltip(result.get('ip', '')),
            create_item_with_tooltip(hostname, hostname),  # 긴 호스트명은 툴팁으로
            create_item_with_tooltip(model, model),
            create_item_with_tooltip(os_version, os_version),
            create_item_with_tooltip(uptime, uptime),      # 긴 업타임은 툴팁으로
            create_item_with_tooltip(result.get('cpu_usage', 'N/A')),
            create_item_with_tooltip(result.get('memory_usage', 'N/A')),
            create_item_with_tooltip(f"{result.get('interface_up_count', 0)}↑/{result.get('interface_down_count', 0)}↓"),
            create_item_with_tooltip(result.get('environment_status', 'N/A')),
            log_score_item,
            create_item_with_tooltip(special_text, special_text),
            create_item_with_tooltip(error_msg, error_msg)  # 긴 오류 메시지는 툴팁으로
        ]
        
        for col, item in enumerate(items):
            self.results_table.setItem(row, col, item)
        
        # 행 높이 자동 조정 (내용에 맞춰)
        self.results_table.resizeRowToContents(row)
        
        # 자동 스크롤
        self.results_table.scrollToBottom()
    
    def export_results(self):
        """결과를 CSV로 내보내기"""
        if not self.analysis_results:
            QMessageBox.warning(self, "내보내기 오류", "내보낼 결과가 없습니다.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Network_Analysis_Results_{timestamp}.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "결과 저장", default_filename, "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'status', 'ip', 'hostname', 'model', 'os_version', 'uptime',
                    'cpu_usage', 'memory_usage', 'interface_up_count', 'interface_down_count',
                    'environment_status', 'log_score', 'log_critical', 'log_errors', 'log_warnings',
                    'flapping_detected', 'auth_issues', 'log_summary', 'error', 'timestamp'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in self.analysis_results:
                    log_analysis = result.get('log_analysis', {})
                    
                    # 필요한 필드만 추출하고 로그 분석 상세 정보 포함
                    row_data = {
                        'status': result.get('status', ''),
                        'ip': result.get('ip', ''),
                        'hostname': result.get('hostname', ''),
                        'model': result.get('model', ''),
                        'os_version': result.get('os_version', ''),
                        'uptime': result.get('uptime', ''),
                        'cpu_usage': result.get('cpu_usage', ''),
                        'memory_usage': result.get('memory_usage', ''),
                        'interface_up_count': result.get('interface_up_count', 0),
                        'interface_down_count': result.get('interface_down_count', 0),
                        'environment_status': result.get('environment_status', ''),
                        'log_score': log_analysis.get('total_issues', 0),
                        'log_critical': log_analysis.get('critical', 0),
                        'log_errors': log_analysis.get('errors', 0),
                        'log_warnings': log_analysis.get('warnings', 0),
                        'flapping_detected': log_analysis.get('flapping_detected', False),
                        'auth_issues': log_analysis.get('auth_issues', False),
                        'log_summary': log_analysis.get('summary', ''),
                        'error': result.get('error', ''),
                        'timestamp': result.get('timestamp', '')
                    }
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "내보내기 완료", f"결과가 저장되었습니다:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "내보내기 오류", f"파일 저장 중 오류 발생:\n{str(e)}")
    
    def generate_pdf_report(self):
        """간결한 PDF 보고서 생성"""
        if not self.analysis_results:
            QMessageBox.warning(self, "PDF 생성 오류", "생성할 결과가 없습니다.")
            return
        
        if not PDF_AVAILABLE:
            QMessageBox.warning(self, "PDF 생성 오류", "PDF 생성을 위해 reportlab 라이브러리를 설치하세요.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Network_Analysis_Summary_{timestamp}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "PDF 보고서 저장", default_filename, "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            self.create_summary_pdf_report(file_path)
            QMessageBox.information(self, "PDF 생성 완료", f"보고서가 생성되었습니다:\n{file_path}")
            
            # 파일 열기 여부 확인
            reply = QMessageBox.question(self, "파일 열기", "생성된 PDF 파일을 열까요?", 
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                os.startfile(file_path) if sys.platform == "win32" else os.system(f"open '{file_path}'")
                
        except Exception as e:
            QMessageBox.critical(self, "PDF 생성 오류", f"PDF 생성 중 오류 발생:\n{str(e)}")
    
    def create_summary_pdf_report(self, file_path):
        """요약 PDF 보고서 생성 (텍스트 잘림 방지)"""
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # 제목
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1
        )
        story.append(Paragraph("Network Equipment Analysis Summary Report", title_style))
        
        # 요약 통계
        total_devices = len(self.analysis_results)
        success_devices = len([r for r in self.analysis_results if r.get('status') == 'SUCCESS'])
        failed_devices = total_devices - success_devices
        
        # 로그 분석 통계
        high_risk_devices = len([r for r in self.analysis_results 
                               if r.get('log_analysis', {}).get('total_issues', 0) >= 50])
        medium_risk_devices = len([r for r in self.analysis_results 
                                 if 20 <= r.get('log_analysis', {}).get('total_issues', 0) < 50])
        
        summary_text = f"""
        <b>Analysis Summary:</b><br/>
        • Total Devices: {total_devices}<br/>
        • Successful: {success_devices}<br/>
        • Failed: {failed_devices}<br/>
        • High Risk (Log Score ≥50): {high_risk_devices}<br/>
        • Medium Risk (Log Score 20-49): {medium_risk_devices}<br/>
        • Analysis Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # 결과 테이블 - 개선된 컬럼 너비와 텍스트 처리
        table_data = [['Status', 'IP Address', 'Hostname', 'Model', 'OS Version', 'CPU', 'Mem', 'IF', 'Env', 'Log']]
        
        for result in self.analysis_results:
            log_score = result.get('log_analysis', {}).get('total_issues', 0)
            
            # 긴 텍스트 처리 - 줄바꿈 허용
            hostname = result.get('hostname', 'N/A')
            if len(hostname) > 18:
                # 긴 호스트명은 줄바꿈으로 처리
                hostname_parts = [hostname[i:i+18] for i in range(0, len(hostname), 18)]
                hostname = '<br/>'.join(hostname_parts)
            
            model = result.get('model', 'N/A')
            if len(model) > 10:
                model = model[:10] + '...'
            
            os_version = result.get('os_version', 'N/A')
            if len(os_version) > 12:
                os_version = os_version[:12] + '...'
            
            row = [
                result.get('status', 'N/A')[:4],  # 길이 제한
                result.get('ip', 'N/A'),
                Paragraph(hostname, styles['Normal']),  # Paragraph로 줄바꿈 허용
                model,
                os_version,
                result.get('cpu_usage', 'N/A')[:5],
                result.get('memory_usage', 'N/A')[:5],
                f"{result.get('interface_up_count', 0)}/{result.get('interface_down_count', 0)}",
                result.get('environment_status', 'N/A')[:6],
                str(log_score)
            ]
            table_data.append(row)
        
        # 개선된 컬럼 너비 - 호스트명을 더 넓게
        col_widths = [0.5*inch, 1.0*inch, 1.4*inch, 0.7*inch, 0.9*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.5*inch, 0.4*inch]
        
        # 테이블 생성
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # 헤더 스타일
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            
            # 데이터 행 스타일
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            
            # 호스트명 컬럼은 왼쪽 정렬 (긴 텍스트이므로)
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            
            # 수직 정렬을 중앙으로
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # 셀 패딩 증가 (텍스트 여유 공간)
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(table)
        
        # 고위험 장비가 있으면 별도 표시
        high_risk_results = [r for r in self.analysis_results 
                           if r.get('log_analysis', {}).get('total_issues', 0) >= 50]
        
        if high_risk_results:
            story.append(Spacer(1, 20))
            story.append(Paragraph("High Risk Devices (Log Score ≥50):", styles['Heading3']))
            
            risk_data = [['IP Address', 'Hostname', 'Log Score', 'Issues']]
            for result in high_risk_results:
                log_analysis = result.get('log_analysis', {})
                issues = []
                if log_analysis.get('critical', 0) > 0:
                    issues.append(f"Critical:{log_analysis['critical']}")
                if log_analysis.get('flapping_detected', False):
                    issues.append("Flapping")
                if log_analysis.get('auth_issues', False):
                    issues.append("Auth Fail")
                
                # 긴 호스트명 처리
                hostname = result.get('hostname', 'N/A')
                if len(hostname) > 20:
                    hostname_para = Paragraph(hostname, styles['Normal'])
                else:
                    hostname_para = hostname
                
                risk_data.append([
                    result.get('ip', 'N/A'),
                    hostname_para,
                    str(log_analysis.get('total_issues', 0)),
                    ", ".join(issues) if issues else "Multiple"
                ])
            
            risk_table = Table(risk_data, colWidths=[1.3*inch, 2.2*inch, 0.8*inch, 2.2*inch])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(risk_table)
        
        # 실패한 장비가 있으면 오류 요약 추가
        failed_results = [r for r in self.analysis_results if r.get('status') == 'FAILED']
        if failed_results:
            story.append(PageBreak())  # 새 페이지에 표시
            story.append(Paragraph("Failed Devices:", styles['Heading3']))
            
            failed_data = [['IP Address', 'Hostname', 'Error Message']]
            for result in failed_results:
                error_msg = result.get('error', 'Unknown error')
                # 긴 오류 메시지는 줄바꿈 처리
                if len(error_msg) > 60:
                    error_para = Paragraph(error_msg, styles['Normal'])
                else:
                    error_para = error_msg
                
                hostname = result.get('hostname', 'N/A')
                if len(hostname) > 20:
                    hostname_para = Paragraph(hostname, styles['Normal'])
                else:
                    hostname_para = hostname
                
                failed_data.append([
                    result.get('ip', 'N/A'), 
                    hostname_para,
                    error_para
                ])
            
            if len(failed_data) > 1:  # 헤더 외에 데이터가 있으면
                failed_table = Table(failed_data, colWidths=[1.2*inch, 2.0*inch, 3.3*inch])
                failed_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(failed_table)
        
        # PDF 생성
        doc.build(story)