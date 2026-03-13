import sys
import os
import json
import logging
import subprocess

# PyQt5 라이브러리
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
    QMessageBox, QDesktopWidget, QStatusBar, QFileDialog,
    QLabel, QLineEdit, QPushButton, QCheckBox, QRadioButton,
    QSpinBox, QTextEdit, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QAction, QMenu, QSplitter, QFontDialog, QDialog, QApplication
)
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtCore import Qt, QTimer

from ui.theme import ModernTheme

# 내부 모듈 import
from ui.network_tab import NetworkTab
from ui.monitoring_tab import EnhancedPingTestTab, EnhancedPingViewTab, TCPingTab
from ui.report_tab import EnhancedInspectionReportGenerator, EnhancedNexusReportGenerator
from ui.dogu_tab import FileViewerTab
from ui.about_tab import AboutTab
from ui.log_analyzer_tab import LogAnalyzerTab

# 기존 import 문들 아래에 추가
from core.workers import NetworkWorker

# 메인 애플리케이션 클래스 수정
class NetworkAutomationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.workers = []
        self.completed_tasks = 0
        self.total_tasks = 0
        self.init_ui()
        self.load_configuration()
        self.center_on_screen()



    def translate(self, text):
        """텍스트 그대로 반환 (다국어 기능 제거됨)"""
        return text

        
    def center_on_screen(self):
        """화면 중앙에 애플리케이션 위치 조정"""
        screen_geo = QDesktopWidget().availableGeometry()
        win_geo = self.geometry()
        center_point = screen_geo.center()
        x = center_point.x() - win_geo.width() // 2
        y = center_point.y() - win_geo.height() // 2
        self.move(x, y)

    def init_ui(self):
        self.setGeometry(100, 100, 1200, 800)



        # 메뉴바 생성
        self.create_menu_bar()
        
        # 상태바 생성
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.translate("Ready")
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 탭 위젯 생성
        self.tabs = QTabWidget()
        
        # 폰트 크기 축소
        tab_font = self.tabs.font()
        tab_font.setPointSize(9)  # 글자 크기 감소
        self.tabs.setFont(tab_font)
        
        # 메인 탭 생성
        self.network_tab = NetworkTab(self)
        
        # 네트워크 진단 및 모니터링 탭 그룹화
        self.diagnostic_tabs = QTabWidget()
        self.diagnostic_tabs.setTabPosition(QTabWidget.North)  # 위쪽으로 변경
        self.ping_test_tab = EnhancedPingTestTab()
        self.ping_view_tab = EnhancedPingViewTab()
        self.tcping_tab = TCPingTab()


        
        self.diagnostic_tabs.addTab(self.ping_test_tab, self.translate("Ping 테스트"))
        self.diagnostic_tabs.addTab(self.ping_view_tab, self.translate("Ping 모니터링"))
        self.diagnostic_tabs.addTab(self.tcping_tab, self.translate("TCPing 테스트"))





        
        # 보고서 탭 그룹화
        self.report_tabs = QTabWidget()
        self.report_tabs.setTabPosition(QTabWidget.North)  # 위쪽으로 변경
        self.iosxe_tab = EnhancedInspectionReportGenerator()
        self.nexus_tab = EnhancedNexusReportGenerator()
        
        self.report_tabs.addTab(self.iosxe_tab, self.translate("IOS-XE 보고서"))
        self.report_tabs.addTab(self.nexus_tab, self.translate("NX-OS 보고서"))
        
        self.about_tab = AboutTab(self)
        
        
        # 메인 탭에 추가
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                margin-right: 8px;  /* 탭 사이의 간격 늘리기 */
                padding: 8px 16px;  /* 탭 내부 여백 늘리기 */
                min-width: 120px;   /* 탭의 최소 너비 설정 */
            }
        """)

        # 도구 탭 그룹 생성 (먼저 선언)
        self.tools_tabs = QTabWidget()
        self.tools_tabs.setTabPosition(QTabWidget.North)  # 위쪽으로 변경

        # 각 도구 탭 추가
        self.file_viewer_tab = FileViewerTab(self)
        self.log_analyzer_tab = LogAnalyzerTab(self)


        self.tools_tabs.addTab(self.file_viewer_tab, self.translate("파일 뷰어"))
        # 로그 분석은 메인 탭으로 이동


        # 🔽 메인 탭 추가 (로그 분석을 도구 옆에 배치)
        self.tabs.addTab(self.network_tab, self.translate("네트워크 자동화"))
        self.tabs.addTab(self.diagnostic_tabs, self.translate("네트워크 진단"))
        self.tabs.addTab(self.report_tabs, self.translate("보고서"))
        self.tabs.addTab(self.tools_tabs, self.translate("도구"))
        self.tabs.addTab(self.log_analyzer_tab.as_widget(), self.translate("로그 분석"))  # 도구 옆에 배치
        self.tabs.addTab(self.about_tab, self.translate("정보"))
  


                
        main_layout.addWidget(self.tabs)
        

        # 스타일 적용
        self.apply_styles()


    








    def create_menu_bar(self):
        """메뉴바 생성 (언어 설정 제외)"""
        menu_bar = self.menuBar()

        # 📁 파일 메뉴
        file_menu = menu_bar.addMenu(self.translate("파일"))

        load_config_action = QAction(self.translate("설정 불러오기"), self)
        load_config_action.setShortcut("Ctrl+O")
        load_config_action.triggered.connect(self.load_configuration)
        file_menu.addAction(load_config_action)

        save_config_action = QAction(self.translate("설정 저장"), self)
        save_config_action.setShortcut("Ctrl+S")
        save_config_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_config_action)

        file_menu.addSeparator()

        open_folder_action = QAction(self.translate("결과 폴더 열기"), self)
        open_folder_action.triggered.connect(self.open_save_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        exit_action = QAction(self.translate("종료"), self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 🛠 도구 메뉴 (언어 설정 제외)
        tools_menu = menu_bar.addMenu(self.translate("도구"))

        view_log_action = QAction(self.translate("로그 파일 보기"), self)
        view_log_action.triggered.connect(self.view_log_file)
        tools_menu.addAction(view_log_action)

        font_action = QAction(self.translate("폰트 설정"), self)
        font_action.triggered.connect(self.set_application_font)
        tools_menu.addAction(font_action)

        refresh_action = QAction(self.translate("UI 새로고침"), self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_ui)
        tools_menu.addAction(refresh_action)



        about_action = QAction(self.translate("프로그램 정보"), self)
        about_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.about_tab))

        # 🌙 테마 초기화
        self.current_theme = "dark"
        self.apply_styles()



    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_styles()



    def apply_styles(self):
        """현대적인 테마 적용"""
        self.setStyleSheet(ModernTheme.get_stylesheet())
    def set_application_font(self):
        """애플리케이션 폰트 설정"""
        current_font = QApplication.font()
        font, ok = QFontDialog.getFont(current_font, self, "폰트 선택")
        if ok:
            QApplication.setFont(font)
            self.statusBar.showMessage(f"폰트가 변경되었습니다: {font.family()} {font.pointSize()}pt", 3000)
    
    def refresh_ui(self):
        """UI 새로고침"""
        self.statusBar.showMessage("UI 새로고침 중...", 1000)
        QApplication.processEvents()
        
        # 스타일 재적용
        self.apply_styles()
        
        # 각 위젯 업데이트
        self.update()
        
        self.statusBar.showMessage("UI 새로고침 완료", 3000)

    def view_log_file(self):
        """로그 파일 보기"""
        log_path = "network_automation.log"
        
        if not os.path.exists(log_path):
            QMessageBox.information(self, self.translate("알림"), "로그 파일이 아직 생성되지 않았습니다.")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(log_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", log_path])
            else:  # Linux
                subprocess.call(["xdg-open", log_path])
                
            self.statusBar.showMessage(f"로그 파일 열기: {log_path}", 3000)
        except Exception as e:
            QMessageBox.warning(self, self.translate("오류"), f"로그 파일을 열 수 없습니다: {e}")
            logging.error(f"[ERROR] 로그 파일 열기 실패: {e}")


        
        # 레이아웃 설정
        layout = QVBoxLayout()
        
        # 스크롤 가능한 텍스트 영역
        text_area = QTextEdit()
        text_area.setReadOnly(True)

        



        


    def select_save_path(self):
        """저장 경로 선택"""
        directory = QFileDialog.getExistingDirectory(self, "저장 경로 선택", "", QFileDialog.ShowDirsOnly)
        if directory:
            self.network_tab.save_path_input.setText(directory)
            self.statusBar.showMessage(f"저장 경로가 설정되었습니다: {directory}", 3000)
            logging.info(f"[INFO] 저장 경로 설정됨: {directory}")

    def open_save_folder(self):
        """저장 폴더 열기"""
        save_path = self.network_tab.save_path_input.text().strip()
        
        if not save_path:
            QMessageBox.warning(self, self.translate("경고"), "저장 경로가 설정되지 않았습니다. 먼저 경로를 선택하세요.")
            return
            
        if not os.path.exists(save_path):
            reply = QMessageBox.question(
                self, "폴더 생성", 
                f"지정된 경로가 존재하지 않습니다: {save_path}\n\n폴더를 생성하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                try:
                    os.makedirs(save_path)
                    logging.info(f"[INFO] 저장 경로 생성됨: {save_path}")
                except Exception as e:
                    QMessageBox.warning(self, self.translate("오류"), f"폴더를 생성할 수 없습니다: {e}")
                    logging.error(f"[ERROR] 폴더 생성 실패: {e}")
                    return
            else:
                return
                
        try:
            if sys.platform == "win32":
                os.startfile(save_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", save_path])
            else:  # Linux
                subprocess.call(["xdg-open", save_path])
                
            self.statusBar.showMessage(self.translate(f"폴더 열기: {save_path}"), 3000)
            logging.info(f"[INFO] 폴더 열기: {save_path}")
        except Exception as e:
            QMessageBox.warning(self, self.translate("오류"), f"폴더를 열 수 없습니다: {e}")
            logging.error(f"[ERROR] 폴더 열기 실패: {e}")

    def start_execution(self):
        """명령어 실행 시작"""
        ip_list = [ip.strip() for ip in self.network_tab.ip_list_text.toPlainText().splitlines() if ip.strip()]
        username = self.network_tab.username_input.text().strip()
        password = self.network_tab.password_input.text()  # 공백 포함하여 그대로 사용
        enable_password = None
        if self.network_tab.enable_checkbox.isChecked():
            enable_password = self.network_tab.enable_password_input.text()  # 공백 포함하여 그대로 사용
        save_path = self.network_tab.save_path_input.text().strip()
        use_ssh = self.network_tab.ssh_radio.isChecked()
        ssh_port = int(self.network_tab.ssh_port_input.text()) if use_ssh and self.network_tab.ssh_port_input.text().isdigit() else 22
        commands = [cmd.strip() for cmd in self.network_tab.command_input.toPlainText().splitlines() if cmd.strip()]

        # 입력 검증
        if not ip_list:
            QMessageBox.warning(self, self.translate("입력 오류"), self.translate("IP 리스트를 입력해주세요!"))
            return
        # Username은 선택적 (일부 장비는 password만 요구)
        # if not username:
        #     QMessageBox.warning(self, self.translate("입력 오류"), "사용자명을 입력해주세요!")
        #     return
        if not password:
            QMessageBox.warning(self, self.translate("입력 오류"), "비밀번호를 입력해주세요!")
            return
        if not commands:
            QMessageBox.warning(self, self.translate("입력 오류"), "실행할 명령어를 입력해주세요!")
            return
        if not save_path:
            QMessageBox.warning(self, self.translate("입력 오류"), "저장 경로를 선택해주세요!")
            return

        # 저장 경로 존재 여부 확인, 없으면 생성
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
                logging.info(f"[INFO] 저장 경로 생성됨: {save_path}")
            except Exception as e:
                QMessageBox.warning(self, self.translate("오류"), f"저장 경로를 생성할 수 없습니다: {e}")
                logging.error(f"[ERROR] 저장 경로 생성 실패: {e}")
                return

        # 입력 필드 비활성화
        self.toggle_inputs(False)

        # 진행 상태 초기화
        self.progress_bar = self.network_tab.progress_bar
        self.progress_bar.setValue(0)
        self.workers = []
        self.completed_tasks = 0
        self.total_tasks = len(ip_list)

        # 상태바 업데이트
        self.statusBar.showMessage(f"명령어 실행 시작... ({len(ip_list)}개 장비)")

        # 동시 실행 또는 순차 실행
        if self.network_tab.concurrent_radio.isChecked():
            self.execute_concurrently(ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port)
        else:
            self.execute_sequentially(ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port)

    def toggle_inputs(self, enable=True):
        """입력 필드 활성화/비활성화"""
        # 네트워크 탭 입력 필드
        self.network_tab.ip_list_text.setEnabled(enable)
        self.network_tab.username_input.setEnabled(enable)
        self.network_tab.password_input.setEnabled(enable)
        self.network_tab.enable_password_input.setEnabled(enable and self.network_tab.enable_checkbox.isChecked())
        self.network_tab.enable_checkbox.setEnabled(enable)
        self.network_tab.ssh_radio.setEnabled(enable)
        self.network_tab.telnet_radio.setEnabled(enable)
        self.network_tab.concurrent_radio.setEnabled(enable)
        self.network_tab.sequential_radio.setEnabled(enable)
        self.network_tab.save_path_input.setEnabled(enable)
        self.network_tab.command_input.setEnabled(enable)
        self.network_tab.command_template.setEnabled(enable)

        # 버튼 상태 설정
        self.network_tab.execute_btn.setEnabled(enable)
        self.network_tab.stop_btn.setEnabled(not enable)

    def execute_concurrently(self, ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22):
        """여러 장비에 대해 동시에 명령어 실행"""
        for ip in ip_list:
            worker = NetworkWorker(ip, username, password, enable_password, use_ssh, save_path, commands, ssh_port)
            worker.progress_updated.connect(self.update_progress)
            worker.task_completed.connect(self.handle_task_completed)
            worker.error_occurred.connect(self.handle_error)
            worker.status_update.connect(self.update_execution_status)  # 실행 상태 업데이트 연결


            # SSH 디버그 대화상자 연결 추가
            if use_ssh:
                self.network_tab.start_ssh_debug_dialog(worker)

            # Worker 시작
            self.workers.append(worker)
            worker.start()
            logging.info(f"[INFO] 작업 시작: {ip}")

    def execute_sequentially(self, ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22):
        """장비별로 순차적으로 명령어 실행"""
        self.sequential_execution_list = ip_list
        self.sequential_index = 0
        self.sequential_params = {
            "username": username,
            "password": password,
            "enable_password": enable_password,
            "use_ssh": use_ssh,
            "save_path": save_path,
            "commands": commands,
            "ssh_port": ssh_port
        }
        self.start_sequential_execution()

    def start_sequential_execution(self):
        """순차 실행의 다음 장비 처리"""
        if self.sequential_index < len(self.sequential_execution_list):
            ip = self.sequential_execution_list[self.sequential_index]
            worker = NetworkWorker(
                ip,
                self.sequential_params["username"],
                self.sequential_params["password"],
                self.sequential_params["enable_password"],
                self.sequential_params["use_ssh"],
                self.sequential_params["save_path"],
                self.sequential_params["commands"],
                self.sequential_params["ssh_port"]
            )

            worker.progress_updated.connect(self.update_progress)
            worker.task_completed.connect(self.handle_sequential_task_completed)
            worker.error_occurred.connect(self.handle_error)
            worker.status_update.connect(self.update_execution_status)  # 실행 상태 업데이트 연결

            # SSH 디버그 대화상자 연결 추가
            if self.sequential_params["use_ssh"]:
                self.network_tab.start_ssh_debug_dialog(worker)
            
            self.workers.append(worker)
            worker.start()
            self.statusBar.showMessage(f"작업 진행 중: {ip} ({self.sequential_index + 1}/{len(self.sequential_execution_list)})")
            logging.info(f"[INFO] 순차 실행 작업 시작: {ip}")
        else:
            self.execution_finished()

    def handle_sequential_task_completed(self, message):
        """순차 실행 시 작업 완료 처리"""
        logging.info(f"[INFO] {message}")
        self.completed_tasks += 1
        self.update_progress()
        self.sequential_index += 1
        self.cleanup_workers()
        self.start_sequential_execution()

    def handle_task_completed(self, message):
        """작업 완료 처리"""
        logging.info(f"[INFO] {message}")
        self.completed_tasks += 1
        self.update_progress()
        if self.completed_tasks == self.total_tasks:
            self.execution_finished()

    def handle_error(self, message):
        """오류 처리"""
        logging.error(message)
        QMessageBox.critical(self, self.translate("작업 오류"), message)
        self.completed_tasks += 1
        self.update_progress()
        if self.completed_tasks == self.total_tasks:
            self.execution_finished()

    def update_execution_status(self, ip, status):
        """실행 상태 업데이트 - 빠른 체크 패널에 표시 (스크롤 가능)"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_text = f"[{timestamp}] {ip} - {status}"

        # 대기 중이면 초기화
        current_text = self.network_tab.execution_status_label.toPlainText()
        if current_text == "대기 중...":
            self.network_tab.execution_status_label.clear()

        # 새 상태 추가
        self.network_tab.execution_status_label.append(status_text)

        # 자동으로 맨 아래로 스크롤
        scrollbar = self.network_tab.execution_status_label.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 스타일 업데이트 (실행 중 표시)
        self.network_tab.execution_status_label.setStyleSheet("""
            QTextEdit {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 4px;
                padding: 8px;
                color: #1e40af;
                font-size: 9pt;
            }
        """)

    def update_progress(self):
        """진행 상태 업데이트"""
        if self.total_tasks > 0:
            progress = int((self.completed_tasks / self.total_tasks) * 100)
            self.progress_bar.setValue(progress)
            self.statusBar.showMessage(f"작업 진행 중: {self.completed_tasks}/{self.total_tasks} 완료 ({progress}%)")

    def cleanup_workers(self):
        """완료된 작업자 정리"""
        for worker in self.workers[:]:
            if not worker.isRunning():
                self.workers.remove(worker)
                worker.deleteLater()

    def execution_finished(self):
        """모든 작업 완료 후 처리"""
        QMessageBox.information(self, self.translate("작업 완료"), "모든 작업이 완료되었습니다!")
        logging.info("[INFO] 모든 작업 완료됨.")
        self.toggle_inputs(True)
        self.statusBar.showMessage("모든 작업이 완료되었습니다.")
        self.save_configuration()
        self.cleanup_workers()

    def stop_execution(self):
        """실행 중인 작업 중지"""
        logging.info("[INFO] 중지 버튼이 눌렸습니다.")
        
        if not self.workers:
            QMessageBox.information(self, self.translate("알림"), "중지할 작업이 없습니다.")
            return
            
        reply = QMessageBox.question(self, self.translate("작업 중지 확인"), 
                                    "실행 중인 모든 작업을 중지하시겠습니까?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for worker in self.workers:
                worker.stop()
                
            self.statusBar.showMessage("작업 중지 요청됨...")
            logging.info("[INFO] 모든 작업 중지 요청됨.")
            
            # 입력 필드 활성화 (타이머로 지연시켜 작업이 모두 중지될 때까지 기다림)
            QTimer.singleShot(2000, lambda: self.toggle_inputs(True))
            QTimer.singleShot(2000, lambda: self.statusBar.showMessage("작업이 중지되었습니다."))

    def save_configuration(self):
        """설정 저장"""
        config = {
            "ip_list": self.network_tab.ip_list_text.toPlainText(),
            "username": self.network_tab.username_input.text(),
            "save_path": self.network_tab.save_path_input.text(),
            "commands": self.network_tab.command_input.toPlainText(),
            "use_ssh": self.network_tab.ssh_radio.isChecked(),
            "concurrent_execution": self.network_tab.concurrent_radio.isChecked(),
            "ssh_port": self.network_tab.ssh_port_input.text()
        }
        
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.statusBar.showMessage("설정이 저장되었습니다.", 3000)
            logging.info("[INFO] 설정 저장됨.")
        except Exception as e:
            QMessageBox.warning(self, self.translate("설정 저장 오류"), f"설정을 저장하는 중 오류가 발생했습니다: {e}")
            logging.error(f"[ERROR] 설정 저장 실패: {e}")

    def load_configuration(self):
            """설정 불러오기"""
            if os.path.exists('config.json'):
                try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 설정 적용
                    if "ip_list" in config:
                        self.network_tab.ip_list_text.setPlainText(config["ip_list"])
                    if "username" in config:
                        self.network_tab.username_input.setText(config["username"])
                    if "save_path" in config:
                        self.network_tab.save_path_input.setText(config["save_path"])
                    if "commands" in config:
                        self.network_tab.command_input.setPlainText(config["commands"])
                    if "use_ssh" in config:
                        self.network_tab.ssh_radio.setChecked(config["use_ssh"])
                        self.network_tab.telnet_radio.setChecked(not config["use_ssh"])
                    if "concurrent_execution" in config:
                        self.network_tab.concurrent_radio.setChecked(config["concurrent_execution"])
                        self.network_tab.sequential_radio.setChecked(not config["concurrent_execution"])
                    if "ssh_port" in config:
                        self.network_tab.ssh_port_input.setText(config["ssh_port"])
                    
                    self.statusBar.showMessage("설정을 불러왔습니다.", 3000)
                    logging.info("[INFO] 설정 불러오기 성공.")
                except Exception as e:
                    QMessageBox.warning(self, self.translate("설정 불러오기 오류"), f"설정을 불러오는 중 오류가 발생했습니다: {e}")
                    logging.error(f"[ERROR] 설정 불러오기 실패: {e}")
            else:
                self.statusBar.showMessage("저장된 설정 파일이 없습니다.", 3000)
                logging.info("[INFO] 저장된 설정 파일이 없음.")