import sys
import os
import logging
import json
import subprocess

# PyQt5 라이브러리
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QLineEdit, 
    QCheckBox, QRadioButton, QPushButton, QFormLayout, 
    QGroupBox, QHBoxLayout, QSpinBox, QProgressBar, 
    QMessageBox, QFileDialog, QComboBox, QDialog, QDesktopWidget, QButtonGroup, QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# 필요한 내부 모듈 import
from core.workers import NetworkWorker


# SimpleLogViewer 클래스 수정
class SimpleLogViewer(QDialog):
    """독립적인 로그 뷰어 창"""
    def __init__(self, title=None):
        # parent 없이 초기화
        super(SimpleLogViewer, self).__init__(None)
        
        # 창 설정
        self.setWindowTitle(title if title else self.tr("로그 뷰어"))
        self.resize(600, 400)  # 더 작은 크기로 변경 (기존: 800, 600)
        
        # 창 위치 설정 (화면 오른쪽 아래)
        self.position_window()
        
        # 레이아웃
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 로그 텍스트 영역
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))  # 폰트 크기 줄임
        layout.addWidget(self.log_text)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 창 크기 조절 버튼 추가
        size_btn = QPushButton(self.tr("크기 조절"))
        size_btn.clicked.connect(self.toggle_size)
        
        # 닫기 버튼
        close_button = QPushButton(self.tr("닫기"))
        close_button.clicked.connect(self.hide)
        
        # 버튼 추가
        button_layout.addWidget(size_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # 초기 메시지
        self.log_text.append(self.tr("=== 로그 세션 시작 ==="))
        
        # 창 크기 상태 저장
        self.is_expanded = False
        self.small_size = (600, 400)
        self.large_size = (800, 600)
        
    def position_window(self):
        """창 위치 설정 (화면 오른쪽 아래)"""
        desktop = QDesktopWidget()
        screen = desktop.availableGeometry()
        
        # 창 크기
        size = self.size()
        
        # 오른쪽 아래에 위치하되, 약간의 간격 유지
        x = screen.width() - size.width() - 20
        y = screen.height() - size.height() - 40
        
        self.move(x, y)
        
    def toggle_size(self):
        """창 크기 전환"""
        if self.is_expanded:
            self.resize(*self.small_size)
            self.is_expanded = False
        else:
            self.resize(*self.large_size)
            self.is_expanded = True
        
        # 위치 재조정
        self.position_window()
        
    def add_log(self, message):
        """로그 메시지 추가"""
        self.log_text.append(message)
        # 스크롤을 최신 위치로 유지
        self.log_text.moveCursor(QTextCursor.End)
        
    def closeEvent(self, event):
        """사용자가 로그 창을 닫을 때 호출됨"""
        # 실제로 닫는 대신 창 숨기기
        event.ignore()
        self.hide()
        
        # 메인 윈도우의 SSH 로그 버튼 상태 업데이트 (가능한 경우)
        try:
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, NetworkAutomationApp):
                    main_window = widget
                    break
                    
            if main_window:
                network_tab = main_window.network_tab
                if hasattr(network_tab, 'ssh_log_btn'):
                    network_tab.ssh_network_tab.ssh_log_btn.setChecked(False)
                    network_tab.ssh_log_btn.setText(network_tab.translate("SSH 로그 보기"))
        except:
            pass  # 오류 발생시 무시

        
        # 완전히 새로운 클래스명을 사용 (기존 충돌 방지)
class SSHLogViewer(QDialog):
    def __init__(self):  # parent 매개변수 없이 정의
        super().__init__()  # parent 없이 초기화
        self.setWindowTitle(self.tr("SSH 로그 뷰어"))
        self.resize(800, 600)
        
        # 레이아웃 설정
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 로그 표시 영역
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))  # 가독성 좋은 폰트
        layout.addWidget(self.log_view)
        
        # 닫기 버튼
        close_btn = QPushButton(self.tr("닫기"))
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        # 초기 메시지
        self.log_view.append(self.tr("==== SSH 로그 세션 시작 ===="))
    
    def add_log(self, message):
        """로그 메시지 추가"""
        self.log_view.append(message)
        # 스크롤을 항상 최신 내용으로 유지
        self.log_view.moveCursor(QTextCursor.End)


class SSHLogWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("SSH 로그 뷰어"))
        self.resize(800, 600)
        
        # 레이아웃 설정
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 텍스트 영역
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_area)
        
        # 닫기 버튼
        close_button = QPushButton(self.tr("닫기"))
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        # 초기 메시지
        self.text_area.append(self.tr("=== SSH 로그 뷰어 시작됨 ==="))
    
    def add_log(self, message):
        """로그 메시지 추가"""
        if hasattr(self, 'text_area'):
            self.text_area.append(message)
            # 스크롤 유지
            self.text_area.moveCursor(QTextCursor.End)


# 네트워크 탭 클래스
class NetworkTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def translate(self, text):
        """부모의 번역 메서드를 사용"""
        if self.parent and hasattr(self.parent, 'translate'):
            return self.parent.translate(text)
        return text

    def start_ssh_debug_dialog(self, worker):
        """SSH 로그 뷰어 시작"""
        try:
            # 로그 뷰어 인스턴스 생성
            title = self.translate(f"SSH 로그: {worker.ip}")
            
            # 이미 로그 뷰어가 있는지 확인
            if not hasattr(self, '_log_viewers') or not self._log_viewers:
                log_viewer = SimpleLogViewer(title)
                
                # 가비지 컬렉션 방지를 위해 저장
                if not hasattr(self, '_log_viewers'):
                    self._log_viewers = []
                self._log_viewers.append(log_viewer)
                
                # 버튼 상태에 따라 로그 창 표시/숨김 설정
                if hasattr(self, 'ssh_log_btn') and self.ssh_log_btn.isChecked():
                    log_viewer.show()
                else:
                    log_viewer.hide()
            else:
                # 기존 로그 뷰어 사용
                log_viewer = self._log_viewers[-1]  # 마지막 생성된 뷰어 사용
                log_viewer.setWindowTitle(title)
                
                # 제목 업데이트
                log_viewer.add_log(self.translate(f"\n=== 새 세션: {worker.ip} ==="))
                
                # 버튼 상태에 따라 로그 창 표시/숨김 설정
                if hasattr(self, 'ssh_log_btn') and self.ssh_log_btn.isChecked():
                    log_viewer.show()
            
            # 시그널 연결
            worker.debug_log.connect(log_viewer.add_log)
            
            log_viewer.add_log(self.translate(f"호스트: {worker.ip} - 로그 모니터링 시작"))
            
        except Exception as e:
            print(self.translate(f"로그 뷰어 시작 오류: {e}"))
            # 오류 시 콘솔 로깅으로 대체
            worker.debug_log.connect(lambda msg: print(self.translate(f"SSH 디버그: {msg}")))

    def toggle_ssh_log(self):
        """SSH 로그 창 토글"""
        if self.ssh_log_btn.isChecked():
            self.show_ssh_logs()
            self.ssh_log_btn.setText(self.translate("SSH 로그 닫기"))
        else:
            self.hide_ssh_logs()
            self.ssh_log_btn.setText(self.translate("SSH 로그 보기"))

    def show_ssh_logs(self):
        """SSH 로그 창 표시"""
        # 활성 로그 창이 있는지 확인
        if hasattr(self, '_log_viewers') and self._log_viewers:
            # 기존 창들 표시
            for viewer in self._log_viewers:
                if viewer.isHidden():
                    viewer.show()
            if self.parent and self.parent.statusBar:
                self.parent.statusBar.showMessage(self.translate("SSH 로그 창이 표시되었습니다."), 3000)
        else:
            # 활성 로그 창이 없는 경우
            title = self.translate("SSH 로그 뷰어")
            log_viewer = SimpleLogViewer(title)
            
            # 객체 저장
            if not hasattr(self, '_log_viewers'):
                self._log_viewers = []
            self._log_viewers.append(log_viewer)
            
            # 로그 창 표시
            log_viewer.show()
            log_viewer.add_log(self.translate("SSH 로그 뷰어가 활성화되었습니다. SSH 연결 시 로그가 여기에 표시됩니다."))
            
            if self.parent and self.parent.statusBar:
                self.parent.statusBar.showMessage(self.translate("새 SSH 로그 창이 열렸습니다."), 3000)

    def hide_ssh_logs(self):
        """SSH 로그 창 숨기기"""
        if hasattr(self, '_log_viewers') and self._log_viewers:
            for viewer in self._log_viewers:
                viewer.hide()
            if self.parent and self.parent.statusBar:
                self.parent.statusBar.showMessage(self.translate("SSH 로그 창이 숨겨졌습니다."), 3000)




    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 작업 설정 그룹
        config_group = QGroupBox(self.translate("작업 설정"))
        config_layout = QHBoxLayout()
        
        # 왼쪽 패널: IP 리스트
        left_panel = QVBoxLayout()
        ip_label = QLabel(self.translate("장비 IP 리스트:"))
        self.ip_list_text = QTextEdit()
        self.ip_list_text.setPlaceholderText(self.translate("IP 주소를 각 줄에 하나씩 입력하세요"))
        left_panel.addWidget(ip_label)
        left_panel.addWidget(self.ip_list_text)
        
        # 오른쪽 패널: 장비 접속 정보
        right_panel = QVBoxLayout()
        
        # 인증 정보 그룹
        auth_group = QGroupBox(self.translate("인증 정보"))
        auth_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        enable_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox()
        self.enable_password_input = QLineEdit()
        self.enable_password_input.setEchoMode(QLineEdit.Password)
        self.enable_password_input.setEnabled(False)
        enable_layout.addWidget(self.enable_checkbox)
        enable_layout.addWidget(self.enable_password_input)
        self.enable_checkbox.toggled.connect(lambda checked: self.enable_password_input.setEnabled(checked))
        
        auth_layout.addRow(self.translate("사용자명:"), self.username_input)
        auth_layout.addRow(self.translate("비밀번호:"), self.password_input)
        auth_layout.addRow(self.translate("Enable 비밀번호:"), enable_layout)
        auth_group.setLayout(auth_layout)
        
        # 접속 방식 그룹
        conn_group = QGroupBox(self.translate("접속 설정"))
        conn_layout = QFormLayout()
        
        # 접속 방식 라디오 버튼
        conn_type_layout = QHBoxLayout()
        self.conn_type_group = QButtonGroup(self)
        self.ssh_radio = QRadioButton(self.translate("SSH"))
        self.ssh_radio.setChecked(True)
        self.conn_type_group.addButton(self.ssh_radio)
        self.telnet_radio = QRadioButton(self.translate("Telnet"))
        self.conn_type_group.addButton(self.telnet_radio)
        conn_type_layout.addWidget(self.ssh_radio)
        conn_type_layout.addWidget(self.telnet_radio)
        
        # SSH 포트 설정
        port_layout = QHBoxLayout()
        port_label = QLabel(self.translate("포트:"))
        self.ssh_port_input = QLineEdit("22")
        self.ssh_port_input.setFixedWidth(80)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.ssh_port_input)
        port_layout.addStretch()
        
        # SSH가 선택되었을 때만, SSH 포트 입력 활성화
        self.ssh_radio.toggled.connect(lambda checked: self.ssh_port_input.setEnabled(checked))
        
        # 실행 방식 라디오 버튼
        exec_type_layout = QHBoxLayout()
        self.exec_type_group = QButtonGroup(self)
        self.concurrent_radio = QRadioButton(self.translate("동시 실행"))
        self.concurrent_radio.setChecked(True)
        self.exec_type_group.addButton(self.concurrent_radio)
        self.sequential_radio = QRadioButton(self.translate("순차 실행"))
        self.exec_type_group.addButton(self.sequential_radio)
        exec_type_layout.addWidget(self.concurrent_radio)
        exec_type_layout.addWidget(self.sequential_radio)
        
        conn_layout.addRow(self.translate("접속 방식:"), conn_type_layout)
        conn_layout.addRow(self.translate("SSH 설정:"), port_layout)
        conn_layout.addRow(self.translate("실행 방식:"), exec_type_layout)
        conn_group.setLayout(conn_layout)
        
        # 저장 경로 그룹
        path_group = QGroupBox(self.translate("출력 저장"))
        path_layout = QHBoxLayout()
        
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText(self.translate("결과가 저장될 경로를 선택하세요"))
        select_path_btn = QPushButton(self.translate("경로 선택"))
        select_path_btn.clicked.connect(self.parent.select_save_path)
        open_folder_btn = QPushButton(self.translate("폴더 열기"))
        open_folder_btn.clicked.connect(self.parent.open_save_folder)
        
        path_layout.addWidget(self.save_path_input)
        path_layout.addWidget(select_path_btn)
        path_layout.addWidget(open_folder_btn)
        
        path_group.setLayout(path_layout)
        
        # 오른쪽 패널에 그룹 추가
        right_panel.addWidget(auth_group)
        right_panel.addWidget(conn_group)
        right_panel.addWidget(path_group)
        
        # 좌우 패널 배치
        config_layout.addLayout(left_panel, 1)
        config_layout.addLayout(right_panel, 1)
        config_group.setLayout(config_layout)
        
        # 명령어 그룹
        command_group = QGroupBox(self.translate("명령어 입력"))
        command_layout = QVBoxLayout()
        
        command_label = QLabel(self.translate("실행할 명령어: (한 줄에 하나씩 입력)"))
        self.command_input = QTextEdit()
        self.command_input.setMinimumHeight(150)
        self.command_input.setPlaceholderText(self.translate("예시:\nshow version\nshow running-config\nshow ip interface brief"))
        
        # 템플릿 선택 + SSH 로그 + 테마 버튼 (한 줄로 깔끔하게)
        template_layout = QHBoxLayout()
        template_label = QLabel(self.translate("템플릿:"))
        self.command_template = QComboBox()
        # 템플릿 옵션 번역
        self.command_template.addItems([
            self.translate("선택하세요..."),
            self.translate("기본 정보 수집"),
            self.translate("인터페이스 정보"),
            self.translate("라우팅 정보"),
            self.translate("보안 설정 확인")
        ])
        self.command_template.currentIndexChanged.connect(self.apply_template)

        # SSH 로그 버튼
        self.ssh_log_btn = QPushButton(self.translate("SSH 로그 보기"))
        self.ssh_log_btn.setFixedHeight(28)
        self.ssh_log_btn.setStyleSheet("font-size: 9pt; padding: 4px 8px;")
        self.ssh_log_btn.setIcon(QIcon("icons/log.png"))
        self.ssh_log_btn.setCheckable(True)
        self.ssh_log_btn.clicked.connect(self.toggle_ssh_log)
        self.ssh_log_btn.setToolTip(self.translate("SSH 연결 로그 창을 표시하거나 숨깁니다"))

        # 템플릿 라인에 위젯 추가
        template_layout.addWidget(template_label)
        template_layout.addWidget(self.command_template)
        template_layout.addStretch()
        template_layout.addWidget(self.ssh_log_btn)
        
        # 실행 제어 버튼
        button_layout = QHBoxLayout()
        self.execute_btn = QPushButton(self.translate("실행"))
        self.execute_btn.setFixedHeight(28)
        self.execute_btn.setStyleSheet("font-size: 9pt; padding: 4px 8px;")
        self.execute_btn.setIcon(QIcon("icons/play.png"))
        self.execute_btn.clicked.connect(self.parent.start_execution)
        
        self.stop_btn = QPushButton(self.translate("중지"))
        self.stop_btn.setFixedHeight(28)
        self.stop_btn.setStyleSheet("font-size: 9pt; padding: 4px 8px;")
        self.stop_btn.setIcon(QIcon("icons/stop.png"))
        self.stop_btn.clicked.connect(self.parent.stop_execution)
        
        clear_btn = QPushButton(self.translate("초기화"))
        clear_btn.setIcon(QIcon("icons/clear.png"))
        clear_btn.clicked.connect(self.clear_inputs)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(clear_btn)
        
        # 진행 상태 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(self.translate("%p% 완료"))
        
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        command_layout.addLayout(template_layout)
        command_layout.addLayout(button_layout)
        command_layout.addWidget(self.progress_bar)
        
        command_group.setLayout(command_layout)
        
        # 메인 레이아웃에 추가
        main_layout.addWidget(config_group, 10)
        main_layout.addWidget(command_group, 1)
        
        self.setLayout(main_layout)
    
    def apply_template(self, index):
        """명령어 템플릿 적용"""
        if index == 0:  # "선택하세요..."
            return
            
        templates = {
            1: [  # 기본 정보 수집
                "terminal length 0",
                "show version",
                "show inventory",
                "show running-config",
                "show ip interface brief",
                "show interfaces status",
                "show environment all",
                "show processes cpu sorted",
                "show memory statistics"
            ],
            2: [  # 인터페이스 정보
                "terminal length 0",
                "show interfaces",
                "show interfaces status",
                "show interfaces description",
                "show ip interface brief",
                "show cdp neighbors detail",
                "show lldp neighbors detail"
            ],
            3: [  # 라우팅 정보
                "terminal length 0",
                "show ip route",
                "show ip protocols",
                "show ip ospf neighbor",
                "show ip ospf database",
                "show ip bgp summary",
                "show ip bgp"
            ],
            4: [  # 보안 설정 확인
                "terminal length 0",
                "show access-lists",
                "show ip access-lists",
                "show running-config | include access-list",
                "show crypto isakmp policy",
                "show crypto ipsec sa",
                "show ip nat translations"
            ]
        }
        
        if index in templates:
            # 현재 입력된 명령어에 템플릿 추가 (기존 명령어 유지)
            current_text = self.command_input.toPlainText().strip()
            template_text = "\n".join(templates[index])
            
            if current_text:
                # 중복 제거를 위해 기존 명령어 분석
                existing_commands = set(current_text.splitlines())
                new_commands = []
                
                for cmd in templates[index]:
                    if cmd not in existing_commands:
                        new_commands.append(cmd)
                
                if new_commands:
                    combined_text = current_text + "\n" + "\n".join(new_commands)
                    self.command_input.setPlainText(combined_text)
                    if self.parent and hasattr(self.parent, 'statusBar'):
                        self.parent.statusBar.showMessage(self.translate(f"{len(new_commands)}개 명령어가 추가되었습니다."), 3000)
                else:
                    if self.parent and hasattr(self.parent, 'statusBar'):
                        self.parent.statusBar.showMessage(self.translate("추가할 새 명령어가 없습니다."), 3000)
            else:
                self.command_input.setPlainText(template_text)
                if self.parent and hasattr(self.parent, 'statusBar'):
                    self.parent.statusBar.showMessage(self.translate(f"{len(templates[index])}개 명령어가 추가되었습니다."), 3000)
            
            # 선택 상자를 기본으로 리셋
            self.command_template.setCurrentIndex(0)

    def clear_inputs(self):
        """입력 필드 초기화"""
        reply = QMessageBox.question(
            self, self.translate("초기화 확인"), 
            self.translate("모든 입력 필드를 초기화하시겠습니까?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.command_input.clear()
            self.command_template.setCurrentIndex(0)
            self.progress_bar.setValue(0)
            
            if self.parent and hasattr(self.parent, 'statusBar'):
                self.parent.statusBar.showMessage(self.translate("입력이 초기화되었습니다."), 3000)