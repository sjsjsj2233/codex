import sys
import os
import re
from datetime import datetime, timedelta
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QMainWindow,  # QMainWindow 추가
                            QPushButton, QLabel, QLineEdit, QComboBox, QFileDialog, 
                            QTextEdit, QTableWidget, QTableWidgetItem, QTabWidget, 
                            QCheckBox, QGroupBox, QFormLayout, QMessageBox, QSplitter,
                            QProgressBar, QHeaderView, QDateTimeEdit,
                            QRadioButton, QButtonGroup, QMenu, QAction,QToolBar,QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCharFormat

# 내부 분석 모듈들
from core.log_analyzer.constants import (SYSLOG_LEVELS, LOG_PATTERNS, SERIES_TO_OS,
                                         SEVERITY_COLORS, NETWORK_EVENTS, SECURITY_EVENTS)
from core.log_analyzer.parser import LogParserThread

class LogAnalyzerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_variables()
        self.init_ui()
        self.update_ui_state(False)

    def init_variables(self):
        self.log_data = []
        self.filtered_data = []
        self.parser_thread = None
        self.current_files = []
        self.device_type = None
        self.current_file = None

    def init_ui(self):
        self.setWindowTitle("Cisco 네트워크 장비 로그 분석기")
        self.main_layout = QVBoxLayout(self)

        self.create_toolbar()
        self.create_file_section()
        self.create_filter_section()
        self.create_tabs()
        self.create_status_area()

    def create_toolbar(self):
        toolbar = QToolBar("기본 도구")
        toolbar.setMovable(False)

        open_action = QAction("로그 파일 열기", self)
        open_action.triggered.connect(self.open_log_file)
        toolbar.addAction(open_action)

        save_action = QAction("분석 결과 저장", self)
        save_action.triggered.connect(self.save_analysis)
        toolbar.addAction(save_action)

        refresh_action = QAction("새로고침", self)
        refresh_action.triggered.connect(self.refresh_view)
        toolbar.addAction(refresh_action)

        clear_filter_action = QAction("필터 초기화", self)
        clear_filter_action.triggered.connect(self.clear_filters)
        toolbar.addAction(clear_filter_action)

        info_action = QAction("프로그램 정보", self)
        info_action.triggered.connect(self.show_about)
        toolbar.addAction(info_action)

        self.main_layout.addWidget(toolbar)

    def create_status_area(self):
        self.status_label = QLabel("준비됨")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_bar)

        wrapper = QWidget()
        wrapper.setLayout(status_layout)
        self.main_layout.addWidget(wrapper)

    def create_file_section(self):
        file_group = QGroupBox("로그 파일")
        layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("로그 파일을 선택하세요...")
        layout.addWidget(self.file_path_edit, 7)

        browse_button = QPushButton("찾기...")
        browse_button.clicked.connect(self.open_log_file)
        layout.addWidget(browse_button, 1)

        self.device_type_combo = QComboBox()
        self.device_type_combo.addItem("자동 감지", None)
        
        # 모든 장비 유형 추가
        for series, os_type in sorted(SERIES_TO_OS.items()):
            self.device_type_combo.addItem(f"{series} ({os_type})", os_type)
        
        # 리스트 직접 추가 (중복 제거)
        for os_type in sorted(set(LOG_PATTERNS.keys())):
            # 기존 항목이 없는 경우에만 추가
            if self.device_type_combo.findData(os_type) == -1:
                self.device_type_combo.addItem(f"{os_type} (일반)", os_type)
        
        layout.addWidget(QLabel("장비 유형:"), 0)
        layout.addWidget(self.device_type_combo, 2)

        self.parse_button = QPushButton("로그 분석")
        self.parse_button.clicked.connect(self.start_parsing)
        layout.addWidget(self.parse_button, 1)

        file_group.setLayout(layout)
        self.main_layout.addWidget(file_group)
        
    def create_filter_section(self):
        """필터링 섹션 생성"""
        filter_group = QGroupBox("로그 필터")
        filter_layout = QHBoxLayout()
        
        # 시간 범위 필터
        time_filter_layout = QFormLayout()
        self.time_filter_enabled = QCheckBox("시간 범위")
        self.time_filter_enabled.stateChanged.connect(self.apply_filters)
        
        self.start_time = QDateTimeEdit()
        self.start_time.setCalendarPopup(True)
        self.start_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time.setDateTime(QDateTime.currentDateTime().addDays(-1))
        
        self.end_time = QDateTimeEdit()
        self.end_time.setCalendarPopup(True)
        self.end_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time.setDateTime(QDateTime.currentDateTime())
        
        time_filter_layout.addRow(self.time_filter_enabled)
        time_filter_layout.addRow("시작:", self.start_time)
        time_filter_layout.addRow("종료:", self.end_time)
        
        time_widget = QWidget()
        time_widget.setLayout(time_filter_layout)
        filter_layout.addWidget(time_widget, 1)
        
        # 키워드 필터
        keyword_filter_layout = QFormLayout()
        self.keyword_filter_enabled = QCheckBox("키워드")
        self.keyword_filter_enabled.stateChanged.connect(self.apply_filters)
        
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("검색할 키워드 입력...")
        self.keyword_edit.returnPressed.connect(self.apply_filters)
        
        self.regex_checkbox = QCheckBox("정규식 사용")
        
        keyword_filter_layout.addRow(self.keyword_filter_enabled)
        keyword_filter_layout.addRow("검색어:", self.keyword_edit)
        keyword_filter_layout.addRow(self.regex_checkbox)
        
        keyword_widget = QWidget()
        keyword_widget.setLayout(keyword_filter_layout)
        filter_layout.addWidget(keyword_widget, 1)
        
        # 심각도 필터
        severity_filter_layout = QFormLayout()
        self.severity_filter_enabled = QCheckBox("심각도 수준")
        self.severity_filter_enabled.stateChanged.connect(self.apply_filters)
        
        self.severity_group = QButtonGroup()
        severity_options = QHBoxLayout()
        

        # 파일 필터 추가
        file_filter_layout = QFormLayout()
        self.file_filter_enabled = QCheckBox("파일 필터")
        self.file_filter_enabled.stateChanged.connect(self.apply_filters)
        
        self.file_combo = QComboBox()
        self.file_combo.addItem("모든 파일", "all")
        self.file_combo.currentIndexChanged.connect(self.apply_filters)
        
        file_filter_layout.addRow(self.file_filter_enabled)
        file_filter_layout.addRow("파일:", self.file_combo)
        
        file_widget = QWidget()
        file_widget.setLayout(file_filter_layout)
        filter_layout.addWidget(file_widget, 1)




        # 심각도 라디오 버튼
        self.severity_critical = QRadioButton("중요")
        self.severity_warning = QRadioButton("경고")
        self.severity_info = QRadioButton("정보")
        self.severity_all = QRadioButton("모두")
        
        self.severity_group.addButton(self.severity_critical, 1)
        self.severity_group.addButton(self.severity_warning, 2)
        self.severity_group.addButton(self.severity_info, 3)
        self.severity_group.addButton(self.severity_all, 4)
        
        self.severity_all.setChecked(True)
        
        severity_options.addWidget(self.severity_critical)
        severity_options.addWidget(self.severity_warning)
        severity_options.addWidget(self.severity_info)
        severity_options.addWidget(self.severity_all)
        
        severity_filter_layout.addRow(self.severity_filter_enabled)
        severity_filter_layout.addRow(severity_options)
        
        severity_widget = QWidget()
        severity_widget.setLayout(severity_filter_layout)
        filter_layout.addWidget(severity_widget, 1)
        
        # 이벤트 유형 필터
        event_filter_layout = QFormLayout()
        self.event_filter_enabled = QCheckBox("이벤트 유형")
        self.event_filter_enabled.stateChanged.connect(self.apply_filters)
        
        self.event_combo = QComboBox()
        self.event_combo.addItem("모든 이벤트", "all")
        
        # 네트워크 이벤트 추가
        self.event_combo.addItem("--- 네트워크 이벤트 ---", None)
        for event_type in sorted(NETWORK_EVENTS.keys()):
            self.event_combo.addItem(f"네트워크: {event_type}", f"network_{event_type}")
        
        # 보안 이벤트 추가
        self.event_combo.addItem("--- 보안 이벤트 ---", None)
        for event_type in sorted(SECURITY_EVENTS.keys()):
            self.event_combo.addItem(f"보안: {event_type}", f"security_{event_type}")
        
        self.event_combo.currentIndexChanged.connect(self.apply_filters)
        
        event_filter_layout.addRow(self.event_filter_enabled)
        event_filter_layout.addRow("이벤트:", self.event_combo)
        
        # 필터 적용 버튼
        self.apply_filter_button = QPushButton("필터 적용")
        self.apply_filter_button.clicked.connect(self.apply_filters)
        event_filter_layout.addRow(self.apply_filter_button)
        
        event_widget = QWidget()
        event_widget.setLayout(event_filter_layout)
        filter_layout.addWidget(event_widget, 1)
        
        filter_group.setLayout(filter_layout)
        self.main_layout.addWidget(filter_group)


    def update_file_filters(self):
        """파일 필터 콤보박스 업데이트"""
        # 기존 항목 저장
        current_selection = self.file_combo.currentData()
        
        # 콤보박스 초기화
        self.file_combo.clear()
        self.file_combo.addItem("모든 파일", "all")
        
        # 고유한 파일 이름 추출
        files = set()
        for log in self.log_data:
            if 'source_file' in log and log['source_file']:
                files.add(log['source_file'])
        
        # 파일 이름으로 정렬하여 추가
        for filename in sorted(files):
            self.file_combo.addItem(filename, filename)
        
        # 이전 선택 항목 복원 시도
        index = self.file_combo.findData(current_selection)
        if index >= 0:
            self.file_combo.setCurrentIndex(index)


        
    def create_tabs(self):
        """탭 섹션 생성"""
        self.tab_widget = QTabWidget()
        
        # 1. 로그 테이블 탭
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)  # 컬럼 수 6으로 변경 (파일 정보 추가)
        self.log_table.setHorizontalHeaderLabels(["시간", "파일", "심각도", "시설", "메시지", "이벤트 유형"])
        self.log_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # 메시지 컬럼 확장
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setSelectionMode(QTableWidget.SingleSelection)
        self.log_table.itemSelectionChanged.connect(self.show_selected_log_detail)
        self.tab_widget.addTab(self.log_table, "로그 테이블")
        
        # 2. 요약 통계 탭
        self.stats_widget = QWidget()
        stats_layout = QVBoxLayout(self.stats_widget)
        
        # 요약 통계 테이블
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["항목", "값"])
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        stats_layout.addWidget(self.stats_table)
        self.tab_widget.addTab(self.stats_widget, "요약 통계")
        
        # 3. 이벤트 분석 탭
        self.events_widget = QWidget()
        events_layout = QVBoxLayout(self.events_widget)
        
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(["이벤트 유형", "카테고리", "발생 횟수", "최근 발생 시간"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.events_table.setSelectionMode(QTableWidget.SingleSelection)
        self.events_table.itemSelectionChanged.connect(self.show_event_details)
        
        events_layout.addWidget(self.events_table)
        self.tab_widget.addTab(self.events_widget, "이벤트 분석")
        
        # 4. 상세 로그 보기 탭
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        
        detail_layout.addWidget(self.detail_text)
        self.tab_widget.addTab(self.detail_widget, "상세 로그")
        
        # 메인 레이아웃에 탭 추가
        self.main_layout.addWidget(self.tab_widget, 10)  # 탭이 대부분의 공간 차지
        
    def create_status_bar(self):
        """상태 표시줄 생성"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 진행 표시기
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("준비됨")


    def as_widget(self):
        """도구 탭에 삽입할 QWidget 반환"""
        return self



    def update_ui_state(self, file_loaded=False):
        """UI 상태 업데이트 (파일 로드 여부에 따라)"""
        is_parsing = self.parser_thread is not None and self.parser_thread.isRunning()
        
        # 파일 로드 관련 컨트롤
        self.parse_button.setEnabled(file_loaded and not is_parsing)
        
        # 필터 관련 컨트롤
        filter_widgets = [
            self.time_filter_enabled, self.start_time, self.end_time,
            self.keyword_filter_enabled, self.keyword_edit, self.regex_checkbox,
            self.severity_filter_enabled, self.severity_critical, self.severity_warning,
            self.severity_info, self.severity_all, self.event_filter_enabled,
            self.event_combo, self.apply_filter_button
        ]
        
        for widget in filter_widgets:
            widget.setEnabled(file_loaded and not is_parsing)
        
        # 파싱 진행 상태 표시
        self.progress_bar.setVisible(is_parsing)
        
        # 상태 메시지 업데이트
        if is_parsing:
            self.status_label.setText("로그 파싱 중...")
        elif file_loaded:
            if self.log_data:
                self.status_label.setText(f"로그 {len(self.log_data)}개 항목 로드됨")
            else:
                self.status_label.setText("파일 로드됨, 분석 준비 완료")
        else:
            self.status_label.setText("준비됨")
        
    # 1. CiscoLogAnalyzerGUI 클래스의 open_log_file 메서드 수정
    def open_log_file(self):
        """로그 파일 열기 대화상자 - 다중 파일 선택 지원"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "로그 파일 열기", "", "모든 파일 (*);;텍스트 파일 (*.txt);;로그 파일 (*.log)"
        )
        
        if file_paths:
            # 파일 경로 텍스트 상자 업데이트
            if len(file_paths) == 1:
                self.file_path_edit.setText(file_paths[0])
            else:
                self.file_path_edit.setText(f"{file_paths[0]} 외 {len(file_paths)-1}개 파일")
            
            # 파일 유효성 검사
            valid_files = []
            invalid_files = []
            
            for file_path in file_paths:
                try:
                    # 파일 읽기 시도
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # 간단한 파일 내용 확인
                        f.read(100)
                    valid_files.append(file_path)
                except Exception as e:
                    invalid_files.append((file_path, str(e)))
            
            # 유효하지 않은 파일 처리
            if invalid_files:
                error_message = "다음 파일들을 열 수 없습니다:\n"
                for file, error in invalid_files:
                    error_message += f"{file}: {error}\n"
                
                QMessageBox.warning(self, "파일 열기 오류", error_message)
            
            # 유효한 파일만 사용
            self.current_files = valid_files
            self.log_data = []  # 기존 데이터 초기화
            
            if valid_files:
                self.update_ui_state(True)
                # 자동으로 파싱 시작
                self.start_parsing()
            else:
                QMessageBox.warning(self, "오류", "유효한 로그 파일이 없습니다.")
            
    # 2. CiscoLogAnalyzerGUI 클래스의 start_parsing 메서드 수정
    def start_parsing(self):
        """로그 파싱 시작 - 다중 파일 지원"""
        if not hasattr(self, 'current_files') or not self.current_files:
            QMessageBox.warning(self, "경고", "파일을 먼저 선택하세요.")
            return
            
        # 진행 상태 초기화
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 장비 유형 가져오기
        device_index = self.device_type_combo.currentIndex()
        self.device_type = self.device_type_combo.itemData(device_index)
        
        # 전체 파싱된 로그를 저장할 리스트
        self.all_parsed_logs = []
        self.files_completed = 0
        self.total_files = len(self.current_files)
        
        # 첫 번째 파일 파싱 시작
        self.parse_next_file()


    def parse_next_file(self):
        """다음 파일 파싱 - 순차적으로 모든 파일 처리"""
        if self.files_completed >= len(self.current_files):
            # 모든 파일 파싱 완료
            self.all_files_completed()
            return
        
        current_file = self.current_files[self.files_completed]
        # status_bar 대신 status_label 사용
        self.status_label.setText(f"파일 파싱 중: {os.path.basename(current_file)} ({self.files_completed+1}/{self.total_files})")
        
        # 파싱 쓰레드 시작
        self.parser_thread = LogParserThread(current_file, self.device_type)
        
        # 시그널 연결
        self.parser_thread.progress_update.connect(self.update_file_progress)
        self.parser_thread.parsing_complete.connect(self.file_parsing_completed)
        self.parser_thread.error_occurred.connect(self.parsing_error)
        
        # 쓰레드 시작
        self.parser_thread.start()

    # 4. CiscoLogAnalyzerGUI 클래스에 새로운 메서드 추가
    def update_file_progress(self, value):
        """개별 파일 파싱 진행 상태 업데이트"""
        # 전체 진행률 = (완료된 파일 수 / 전체 파일 수) * 100 + (현재 파일 진행률 / 전체 파일 수)
        overall_progress = int((self.files_completed / self.total_files) * 100 + (value / self.total_files))
        self.progress_bar.setValue(min(100, overall_progress))

    # 5. CiscoLogAnalyzerGUI 클래스에 새로운 메서드 추가
    def file_parsing_completed(self, log_data):
        """개별 파일 파싱 완료 처리"""
        # 파일 경로 정보 추가
        current_file = self.current_files[self.files_completed]
        filename = os.path.basename(current_file)
        
        # 각 로그 항목에 파일 출처 정보 추가
        for log in log_data:
            log['source_file'] = filename
        
        # 전체 로그 데이터에 추가
        self.all_parsed_logs.extend(log_data)
        
        # 다음 파일로 진행
        self.files_completed += 1
        if self.files_completed < len(self.current_files):
            self.parse_next_file()
        else:
            self.all_files_completed()

    # 6. CiscoLogAnalyzerGUI 클래스에 새로운 메서드 추가
    def all_files_completed(self):
        """모든 파일 파싱 완료 처리"""
        # 시간순으로 정렬
        self.all_parsed_logs.sort(
            key=lambda x: x.get('timestamp_obj', datetime.min) 
            if x.get('timestamp_obj') is not None else datetime.min
        )
        
        # 파일 필터 콤보박스 업데이트
        self.update_file_filters()

        # 최종 로그 데이터 설정
        self.log_data = self.all_parsed_logs
        self.filtered_data = self.log_data.copy()
        
        # 필터 적용
        self.apply_filters()
        
        # 통계 업데이트
        self.update_statistics()
        
        # 이벤트 분석 업데이트
        self.update_event_analysis()
        
        # UI 상태 업데이트
        self.progress_bar.setVisible(False)
        self.update_ui_state(True)
        
        # status_bar 대신 status_label 사용
        self.status_label.setText(f"총 {len(self.current_files)}개 파일 파싱 완료: {len(self.log_data)}개 로그 항목 발견")


        
    def update_progress(self, value):
        """파싱 진행 상태 업데이트"""
        self.progress_bar.setValue(value)
        
    def parsing_completed(self, log_data):
        """파싱 완료 처리"""
        self.log_data = log_data
        self.filtered_data = log_data.copy()  # 초기 필터링 결과 = 전체
        
        # 필터 적용
        self.apply_filters()
        
        # 통계 업데이트
        self.update_statistics()
        
        # 이벤트 분석 업데이트
        self.update_event_analysis()
        
        # UI 상태 업데이트
        self.progress_bar.setVisible(False)
        self.update_ui_state(True)
        
        # status_bar 대신 status_label 사용
        self.status_label.setText(f"로그 파싱 완료: {len(log_data)}개 항목 발견")
        
    def parsing_error(self, error_message):
        """파싱 오류 처리"""
        self.progress_bar.setVisible(False)
        self.update_ui_state(True)
        
        QMessageBox.critical(self, "파싱 오류", error_message)
        # status_bar 대신 status_label 사용
        self.status_label.setText("파싱 오류 발생")
        
    def apply_filters(self):
        """필터 조건에 따라 로그 필터링 - 파일 필터 추가"""
        if not self.log_data:
            return
                
        # 원본 데이터로 시작
        filtered_data = self.log_data.copy()
        

        # 파일 필터 적용
        if self.file_filter_enabled.isChecked():
            file_filter = self.file_combo.currentData()
            
            if file_filter and file_filter != 'all':
                filtered_data = [
                    log for log in filtered_data
                    if log.get('source_file') == file_filter
            ]



        # 1. 시간 범위 필터
        if self.time_filter_enabled.isChecked():
            start_time = self.start_time.dateTime().toPython()
            end_time = self.end_time.dateTime().toPython()
            
            filtered_data = [
                log for log in filtered_data
                if 'timestamp_obj' in log and log['timestamp_obj'] is not None
                and start_time <= log['timestamp_obj'] <= end_time
            ]
        
        # 2. 키워드 필터
        if self.keyword_filter_enabled.isChecked() and self.keyword_edit.text().strip():
            keyword = self.keyword_edit.text().strip()
            
            if self.regex_checkbox.isChecked():
                # 정규식 검색
                try:
                    pattern = re.compile(keyword, re.IGNORECASE)
                    filtered_data = [
                        log for log in filtered_data
                        if pattern.search(log.get('raw', '')) or 
                        pattern.search(log.get('message', ''))
                    ]
                except re.error:
                    # 정규식 오류 시 일반 텍스트 검색으로 폴백
                    QMessageBox.warning(self, "정규식 오류", "잘못된 정규식입니다. 일반 텍스트 검색을 수행합니다.")
                    filtered_data = [
                        log for log in filtered_data
                        if keyword.lower() in log.get('raw', '').lower() or 
                        keyword.lower() in log.get('message', '').lower()
                    ]
            else:
                # 일반 텍스트 검색
                filtered_data = [
                    log for log in filtered_data
                    if keyword.lower() in log.get('raw', '').lower() or 
                    keyword.lower() in log.get('message', '').lower()
                ]
        
        # 3. 심각도 필터
        if self.severity_filter_enabled.isChecked():
            severity_button_id = self.severity_group.checkedId()
            
            if severity_button_id == 1:  # 중요
                filtered_data = [
                    log for log in filtered_data
                    if log.get('severity') in ['EMERGENCY', 'ALERT', 'CRITICAL', 'ERROR']
                ]
            elif severity_button_id == 2:  # 경고
                filtered_data = [
                    log for log in filtered_data
                    if log.get('severity') in ['WARNING', 'NOTICE']
                ]
            elif severity_button_id == 3:  # 정보
                filtered_data = [
                    log for log in filtered_data
                    if log.get('severity') in ['INFO', 'DEBUG']
                ]
            # 4(모두)는 필터링 하지 않음
        
        # 4. 이벤트 유형 필터
        if self.event_filter_enabled.isChecked():
            event_type = self.event_combo.currentData()
            
            if event_type and event_type != 'all':
                if event_type.startswith('network_'):
                    # 네트워크 이벤트 필터링
                    event_name = event_type[8:]  # "network_" 제거
                    filtered_data = [
                        log for log in filtered_data
                        if log.get('event_category') == 'network' and log.get('event_type') == event_name
                    ]
                elif event_type.startswith('security_'):
                    # 보안 이벤트 필터링
                    event_name = event_type[9:]  # "security_" 제거
                    filtered_data = [
                        log for log in filtered_data
                        if log.get('event_category') == 'security' and log.get('event_type') == event_name
                    ]
        
        # 필터링된 결과 저장 및 UI 업데이트
        self.filtered_data = filtered_data
        self.update_log_table()
        
        # 상태 메시지 업데이트
        self.status_label.setText(f"필터링됨: {len(filtered_data)}/{len(self.log_data)} 항목 표시")
        
    def update_log_table(self):
        """로그 테이블 업데이트 - 파일 정보 포함"""
        self.log_table.setRowCount(0)  # 테이블 초기화
        
        if not self.filtered_data:
            return
            
        # 테이블에 데이터 추가
        for row, log in enumerate(self.filtered_data):
            self.log_table.insertRow(row)
            
            # 시간
            timestamp_item = QTableWidgetItem(log.get('timestamp', ''))
            self.log_table.setItem(row, 0, timestamp_item)
            
            # 파일 (인덱스 1)
            file_item = QTableWidgetItem(log.get('source_file', ''))
            self.log_table.setItem(row, 1, file_item)
            
            # 심각도 (인덱스 2)
            severity = log.get('severity', 'INFO')
            severity_item = QTableWidgetItem(severity)
            
            # 심각도별 색상 적용
            if severity in SEVERITY_COLORS:
                severity_item.setForeground(SEVERITY_COLORS[severity])
                
                # EMERGENCY, ALERT, CRITICAL, ERROR는 배경색도 설정
                if severity in ['EMERGENCY', 'ALERT', 'CRITICAL', 'ERROR']:
                    severity_item.setBackground(QColor(255, 220, 220))  # 연한 빨강
            
            self.log_table.setItem(row, 2, severity_item)
            
            # 시설 (인덱스 3)
            facility_item = QTableWidgetItem(log.get('facility', ''))
            self.log_table.setItem(row, 3, facility_item)
            
            # 메시지 (인덱스 4)
            message_item = QTableWidgetItem(log.get('message', ''))
            self.log_table.setItem(row, 4, message_item)
            
            # 이벤트 유형 (인덱스 5)
            event_type = ''
            if 'event_type' in log and 'event_category' in log:
                event_type = f"{log['event_category']}: {log['event_type']}"
            
            event_item = QTableWidgetItem(event_type)
            self.log_table.setItem(row, 5, event_item)
        
        # 테이블 정렬
        self.log_table.setSortingEnabled(True)
        
    def update_statistics(self):
        """요약 통계 업데이트"""
        if not self.log_data:
            return
            
        # 통계 테이블 초기화
        self.stats_table.setRowCount(0)
        
        # 1. 기본 통계
        basic_stats = [
            ("총 로그 수", len(self.log_data)),
            ("필터링된 로그 수", len(self.filtered_data)),
        ]
        
        # 2. 시간 범위
        timestamps = [log['timestamp_obj'] for log in self.log_data if 'timestamp_obj' in log and log['timestamp_obj']]
        
        if timestamps:
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration = end_time - start_time
            
            time_stats = [
                ("로그 시작 시간", start_time.strftime("%Y-%m-%d %H:%M:%S")),
                ("로그 종료 시간", end_time.strftime("%Y-%m-%d %H:%M:%S")),
                ("시간 범위", f"{duration.days}일 {duration.seconds//3600}시간 {(duration.seconds//60)%60}분"),
            ]
        else:
            time_stats = [
                ("로그 시간 정보", "시간 정보 없음"),
            ]
        
        # 3. 심각도 통계
        severity_counts = {}
        for log in self.log_data:
            severity = log.get('severity', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        severity_stats = [
            (f"심각도: {severity}", count)
            for severity, count in sorted(severity_counts.items(), 
                                        key=lambda x: list(SEVERITY_COLORS.keys()).index(x[0]) 
                                        if x[0] in SEVERITY_COLORS else 999)
        ]
        
        # 4. 이벤트 유형 통계
        event_counts = {}
        for log in self.log_data:
            if 'event_type' in log and 'event_category' in log:
                event_key = f"{log['event_category']}: {log['event_type']}"
                event_counts[event_key] = event_counts.get(event_key, 0) + 1
        
        event_stats = [
            (f"이벤트: {event_type}", count)
            for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]  # 상위 10개
        ]
        
        # 5. 추가 모든 통계 결합
        all_stats = basic_stats + time_stats + severity_stats + event_stats
        
        # 테이블에 통계 추가
        for row, (label, value) in enumerate(all_stats):
            self.stats_table.insertRow(row)
            self.stats_table.setItem(row, 0, QTableWidgetItem(str(label)))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(value)))
    
    def update_event_analysis(self):
        """이벤트 분석 테이블 업데이트"""
        if not self.log_data:
            return
            
        # 이벤트 테이블 초기화
        self.events_table.setRowCount(0)
        
        # 이벤트 통계 계산
        event_stats = {}
        
        for log in self.log_data:
            if 'event_type' in log and 'event_category' in log:
                event_key = (log['event_category'], log['event_type'])
                
                if event_key not in event_stats:
                    event_stats[event_key] = {
                        'count': 0,
                        'last_time': None,
                        'logs': []
                    }
                
                event_stats[event_key]['count'] += 1
                event_stats[event_key]['logs'].append(log)
                
                # 가장 최근 발생 시간 업데이트
                if ('timestamp_obj' in log and log['timestamp_obj'] and 
                    (event_stats[event_key]['last_time'] is None or 
                     log['timestamp_obj'] > event_stats[event_key]['last_time'])):
                    event_stats[event_key]['last_time'] = log['timestamp_obj']
        
        # 이벤트 횟수 기준 내림차순 정렬
        sorted_events = sorted(
            event_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        # 테이블에 이벤트 추가
        for row, ((category, event_type), stats) in enumerate(sorted_events):
            self.events_table.insertRow(row)
            
            # 이벤트 유형
            self.events_table.setItem(row, 0, QTableWidgetItem(event_type))
            
            # 카테고리
            self.events_table.setItem(row, 1, QTableWidgetItem(category))
            
            # 발생 횟수
            self.events_table.setItem(row, 2, QTableWidgetItem(str(stats['count'])))
            
            # 최근 발생 시간
            last_time = stats['last_time']
            last_time_str = last_time.strftime("%Y-%m-%d %H:%M:%S") if last_time else "알 수 없음"
            self.events_table.setItem(row, 3, QTableWidgetItem(last_time_str))
            
            # 이벤트 데이터 저장 (보이지 않음)
            for i in range(4):
                item = self.events_table.item(row, i)
                if item:
                    item.setData(Qt.UserRole, {'logs': stats['logs']})
        
        # 테이블 정렬 활성화
        self.events_table.setSortingEnabled(True)
    
    def show_selected_log_detail(self):
        """선택된 로그 항목의 상세 정보 표시"""
        # 선택된 행 가져오기
        selected_rows = self.log_table.selectedIndexes()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        
        # 원본 로그 데이터 검색
        if 0 <= row < len(self.filtered_data):
            log = self.filtered_data[row]
            self.show_log_detail(log)
            
            # 상세 로그 탭으로 전환
            self.tab_widget.setCurrentIndex(3)
    
    def show_event_details(self):
        """선택된 이벤트 유형의 로그 세부 정보 표시"""
        # 선택된 행 가져오기
        selected_rows = self.events_table.selectedIndexes()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        
        # 저장된 로그 데이터 가져오기
        item = self.events_table.item(row, 0)
        if item:
            event_data = item.data(Qt.UserRole)
            
            if event_data and 'logs' in event_data:
                event_logs = event_data['logs']
                
                # 이벤트 요약 생성
                event_type = self.events_table.item(row, 0).text()
                category = self.events_table.item(row, 1).text()
                count = self.events_table.item(row, 2).text()
                
                summary = f"<h2>이벤트 유형: {event_type}</h2>"
                summary += f"<p><b>카테고리:</b> {category}</p>"
                summary += f"<p><b>발생 횟수:</b> {count}</p>"
                summary += "<h3>관련 로그 항목:</h3>"
                
                # 관련 로그 항목 목록
                summary += "<ul>"
                for i, log in enumerate(event_logs[:20]):  # 최대 20개 표시
                    timestamp = log.get('timestamp', '알 수 없음')
                    message = log.get('message', '')
                    summary += f"<li><b>{timestamp}</b>: {message}</li>"
                    
                if len(event_logs) > 20:
                    summary += f"<li>... 외 {len(event_logs) - 20}개 항목</li>"
                    
                summary += "</ul>"
                
                # 상세 정보 표시
                self.detail_text.setHtml(summary)
                
                # 상세 로그 탭으로 전환
                self.tab_widget.setCurrentIndex(3)
    
    def show_log_detail(self, log):
        """로그 항목의 상세 정보 표시"""
        if not log:
            return
            
        # HTML 형식으로 표시
        detail_html = "<html><body style='font-family: Arial; font-size: 10pt;'>"
        
        # 제목
        detail_html += "<h2>로그 상세 정보</h2>"
        
        # 기본 정보 테이블
        detail_html += "<table border='0' cellspacing='5' style='width: 100%;'>"
        
        # 시간
        if 'timestamp' in log:
            detail_html += f"<tr><td style='font-weight: bold; width: 120px;'>시간:</td><td>{log['timestamp']}</td></tr>"

        # 파일 출처 추가
        if 'source_file' in log:
            detail_html += f"<tr><td style='font-weight: bold;'>파일:</td><td>{log['source_file']}</td></tr>"
        
        # 심각도 (색상 적용)
        if 'severity' in log:
            severity = log['severity']
            color = SEVERITY_COLORS.get(severity, QColor(0, 0, 0)).name()
            detail_html += f"<tr><td style='font-weight: bold;'>심각도:</td><td><span style='color: {color};'>{severity}</span></td></tr>"
        
        # 시설
        if 'facility' in log:
            detail_html += f"<tr><td style='font-weight: bold;'>시설:</td><td>{log['facility']}</td></tr>"
        
        # 이벤트 정보
        if 'event_type' in log and 'event_category' in log:
            detail_html += f"<tr><td style='font-weight: bold;'>이벤트 유형:</td><td>{log['event_type']} ({log['event_category']})</td></tr>"
        
        detail_html += "</table>"
        
        # 구분선
        detail_html += "<hr>"
        
        # 메시지
        if 'message' in log:
            detail_html += "<h3>메시지</h3>"
            detail_html += f"<p>{log['message']}</p>"
        
        # 원본 로그
        detail_html += "<h3>원본 로그</h3>"
        detail_html += f"<pre style='background-color: #f5f5f5; padding: 10px; border-radius: 5px;'>{log['raw']}</pre>"
        
        detail_html += "</body></html>"
        
        # 상세 정보 표시
        self.detail_text.setHtml(detail_html)
    
    def save_analysis(self):
        """분석 결과 저장"""
        if not self.log_data:
            QMessageBox.warning(self, "경고", "저장할 분석 결과가 없습니다.")
            return
            
        # 저장 대화상자
        file_path, _ = QFileDialog.getSaveFileName(
            self, "분석 결과 저장", "", "HTML 파일 (*.html);;CSV 파일 (*.csv);;텍스트 파일 (*.txt)"
        )
        
        if not file_path:
            return
        
        # 추가된 부분: 파일 쓰기 권한 확인
        try:
            with open(file_path, 'w', encoding='utf-8') as test_file:
                pass
        except PermissionError:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 권한이 없습니다: {file_path}")
            return
        except IOError as e:
            QMessageBox.critical(self, "저장 오류", f"파일을 저장할 수 없습니다: {e}")
            return
            
        try:
            # 기존 저장 로직
            if file_path.endswith('.html'):
                self.save_as_html(file_path)
            elif file_path.endswith('.csv'):
                self.save_as_csv(file_path)
            else:  # .txt 또는 기타
                self.save_as_text(file_path)
                
            self.status_label.setText(f"분석 결과가 {file_path}에 저장되었습니다.")
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "저장 오류", 
                f"파일 저장 중 오류가 발생했습니다: {str(e)}\n\n{traceback.format_exc()}")
    
    def save_as_html(self, file_path):
        """HTML 형식으로 결과 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            # HTML 헤더
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cisco 네트워크 장비 로그 분석 결과</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #0066cc; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background-color: #f2f2f2; text-align: left; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .emergency, .alert, .critical, .error { color: #cc0000; font-weight: bold; }
        .warning, .notice { color: #ff6600; }
        .info { color: #000000; }
        .debug { color: #666666; }
        .section { margin-top: 30px; }
    </style>
</head>
<body>
    <h1>Cisco 네트워크 장비 로그 분석 결과</h1>
    <p><b>파일:</b> {0}</p>
    <p><b>분석 시간:</b> {1}</p>
""".format(self.current_file, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            # 요약 통계
            f.write("<div class='section'>\n<h2>요약 통계</h2>\n<table>\n")
            f.write("<tr><th>항목</th><th>값</th></tr>\n")
            
            for row in range(self.stats_table.rowCount()):
                label = self.stats_table.item(row, 0).text()
                value = self.stats_table.item(row, 1).text()
                f.write(f"<tr><td>{label}</td><td>{value}</td></tr>\n")
                
            f.write("</table>\n</div>\n")
            
            # 이벤트 분석
            f.write("<div class='section'>\n<h2>이벤트 분석</h2>\n<table>\n")
            f.write("<tr><th>이벤트 유형</th><th>카테고리</th><th>발생 횟수</th><th>최근 발생 시간</th></tr>\n")
            
            for row in range(self.events_table.rowCount()):
                event_type = self.events_table.item(row, 0).text()
                category = self.events_table.item(row, 1).text()
                count = self.events_table.item(row, 2).text()
                last_time = self.events_table.item(row, 3).text()
                
                f.write(f"<tr><td>{event_type}</td><td>{category}</td><td>{count}</td><td>{last_time}</td></tr>\n")
                
            f.write("</table>\n</div>\n")
            
            # 로그 항목
            f.write("<div class='section'>\n<h2>로그 항목</h2>\n<table>\n")
            f.write("<tr><th>시간</th><th>심각도</th><th>시설</th><th>메시지</th><th>이벤트 유형</th></tr>\n")
            
            for log in self.filtered_data:
                timestamp = log.get('timestamp', '')
                severity = log.get('severity', 'INFO')
                facility = log.get('facility', '')
                message = log.get('message', '')
                
                event_type = ''
                if 'event_type' in log and 'event_category' in log:
                    event_type = f"{log['event_category']}: {log['event_type']}"
                
                # 심각도에 따른 스타일 클래스
                severity_class = severity.lower() if severity.lower() in ['emergency', 'alert', 'critical', 'error', 'warning', 'notice', 'info', 'debug'] else 'info'
                
                f.write(f"<tr><td>{timestamp}</td><td class='{severity_class}'>{severity}</td><td>{facility}</td><td>{message}</td><td>{event_type}</td></tr>\n")
                
            f.write("</table>\n</div>\n")
            
            # HTML 푸터
            f.write("""
</body>
</html>
""")
    
    def save_as_csv(self, file_path):
        """CSV 형식으로 결과 저장"""
        try:
            # 로그 데이터를 데이터프레임으로 변환
            logs_df = pd.DataFrame(self.filtered_data)
            
            # 이벤트 정보 추가
            event_info = []
            for log in self.filtered_data:
                event_type = ''
                if 'event_type' in log and 'event_category' in log:
                    event_type = f"{log['event_category']}: {log['event_type']}"
                event_info.append(event_type)
                
            logs_df['event_info'] = event_info
            
            # 필요한 컬럼만 선택
            if 'timestamp' in logs_df.columns and 'severity' in logs_df.columns and 'facility' in logs_df.columns and 'message' in logs_df.columns:
                logs_df = logs_df[['timestamp', 'severity', 'facility', 'message', 'event_info']]
            
            # CSV로 저장
            logs_df.to_csv(file_path, index=False, encoding='utf-8')
        
        except Exception as e:
            raise Exception(f"CSV 파일 저장 오류: {str(e)}")
    
    def save_as_text(self, file_path):
        """텍스트 형식으로 결과 저장"""
        with open(file_path, 'w', encoding='utf-8') as f:
            # 헤더
            f.write("Cisco 네트워크 장비 로그 분석 결과\n")
            f.write(f"파일: {self.current_file}\n")
            f.write(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 요약 통계
            f.write("===== 요약 통계 =====\n")
            
            for row in range(self.stats_table.rowCount()):
                label = self.stats_table.item(row, 0).text()
                value = self.stats_table.item(row, 1).text()
                f.write(f"{label}: {value}\n")
                
            f.write("\n")
            
            # 이벤트 분석
            f.write("===== 이벤트 분석 =====\n")
            f.write("이벤트 유형\t카테고리\t발생 횟수\t최근 발생 시간\n")
            
            for row in range(self.events_table.rowCount()):
                event_type = self.events_table.item(row, 0).text()
                category = self.events_table.item(row, 1).text()
                count = self.events_table.item(row, 2).text()
                last_time = self.events_table.item(row, 3).text()
                
                f.write(f"{event_type}\t{category}\t{count}\t{last_time}\n")
                
            f.write("\n")
            
            # 로그 항목
            f.write("===== 로그 항목 =====\n")
            
            for log in self.filtered_data:
                timestamp = log.get('timestamp', '')
                severity = log.get('severity', 'INFO')
                facility = log.get('facility', '')
                message = log.get('message', '')
                
                event_type = ''
                if 'event_type' in log and 'event_category' in log:
                    event_type = f"{log['event_category']}: {log['event_type']}"
                
                f.write(f"[{timestamp}] {severity} {facility} - {message}")
                if event_type:
                    f.write(f" [{event_type}]")
                f.write("\n")
    
    def refresh_view(self):
        """현재 보기 새로고침"""
        # 현재 선택된 탭에 따라 다른 새로고침 작업 수행
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # 로그 테이블
            self.update_log_table()
        elif current_tab == 1:  # 요약 통계
            self.update_statistics()
        elif current_tab == 2:  # 이벤트 분석
            self.update_event_analysis()
    
    def clear_filters(self):
        """모든 필터 초기화"""
        # 시간 필터 초기화
        self.time_filter_enabled.setChecked(False)
        self.start_time.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.end_time.setDateTime(QDateTime.currentDateTime())
        
        # 키워드 필터 초기화
        self.keyword_filter_enabled.setChecked(False)
        self.keyword_edit.clear()
        self.regex_checkbox.setChecked(False)
        
        # 심각도 필터 초기화
        self.severity_filter_enabled.setChecked(False)
        self.severity_all.setChecked(True)
        
        # 이벤트 필터 초기화
        self.event_filter_enabled.setChecked(False)
        self.event_combo.setCurrentIndex(0)
        
        # 필터 적용
        self.apply_filters()
        
        # status_bar 대신 status_label 사용
        self.status_label.setText("모든 필터가 초기화되었습니다.")
    
    def show_about(self):
        """프로그램 정보 표시"""
        QMessageBox.about(self, "프로그램 정보",
            """<h1>Cisco 네트워크 장비 로그 분석기</h1>
            <p>버전 1.0</p>
            <p>이 프로그램은 다양한 Cisco 네트워크 장비의 로그 파일을 분석하기 위한 도구입니다.</p>
            <p>지원되는 장비 유형:</p>
            <ul>
                <li>IOS/IOS-XE 스위치 (2960X, 3650, 3850, 9200, 9300 등)</li>
                <li>NX-OS 스위치 (93180, 9500 등)</li>
                <li>ASA/FTD 보안 장비</li>
                <li>ISR/ASR 라우터</li>
                <li>무선 컨트롤러 (9800 등)</li>
                <li>SD-WAN (Viptela)</li>
            </ul>
            """
        )