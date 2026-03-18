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
    QComboBox, QAction, QMenu, QSplitter, QFontDialog, QDialog, QApplication,
    QProgressBar, QFrame,
)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QTextCursor
from PyQt5.QtCore import Qt, QTimer

from ui.theme import ModernTheme
from core.license_manager import LicenseManager

def _config_path() -> str:
    d = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'NetworkAutomation')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'config.json')

# 내부 모듈 import
from ui.network_tab import NetworkTab
from ui.monitoring_tab import MonitoringTab
from ui.console_tab import ConsoleTab
from ui.dogu_tab import DoguTab
from ui.about_tab import AboutTab
from ui.home_tab import HomeTab

# 기존 import 문들 아래에 추가
from core.workers import NetworkWorker
from core.i18n import tr, set_language, get_language
from core.updater import UpdateChecker, AutoUpdater, CURRENT_VERSION

# 메인 애플리케이션 클래스 수정
class NetworkAutomationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.workers = []
        self.completed_tasks = 0
        self.total_tasks = 0
        self.failed_tasks = 0
        self._update_download_url = ''
        self.license_manager = LicenseManager()
        self.init_ui()
        self.load_configuration()
        self.center_on_screen()
        # 면책 조항 → 라이센스 순서로 표시
        QTimer.singleShot(200, self._check_startup_dialogs)
        # 업데이트 체크 (3초 후 백그라운드 실행)
        QTimer.singleShot(3000, self._start_update_check)

    def _check_startup_dialogs(self):
        from ui.disclaimer_dialog import DisclaimerDialog, has_agreed
        if not has_agreed():
            dlg = DisclaimerDialog(self)
            if dlg.exec_() != DisclaimerDialog.Accepted:
                import sys
                sys.exit(0)



    def translate(self, text):
        return tr(text)

        
    def center_on_screen(self):
        """화면 중앙에 애플리케이션 위치 조정"""
        screen_geo = QDesktopWidget().availableGeometry()
        win_geo = self.geometry()
        center_point = screen_geo.center()
        x = center_point.x() - win_geo.width() // 2
        y = center_point.y() - win_geo.height() // 2
        self.move(x, y)

    def init_ui(self):
        self.setWindowTitle("Network Automation v8.0")
        self.setMinimumSize(960, 640)
        self.setGeometry(100, 100, 1280, 820)



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
        self.tabs.setObjectName("mainTabs")
        self.tabs.setDocumentMode(True)   # 탭 아래 경계선 제거 (더 깔끔)
        main_layout.setContentsMargins(8, 4, 8, 4)
        
        # 메인 탭 생성
        self.network_tab = NetworkTab(self, license_manager=self.license_manager)
        
        # 네트워크 진단 탭
        self.diagnostic_tab = MonitoringTab()

        # 콘솔 탭
        self.console_tab = ConsoleTab()





        
        self.about_tab = AboutTab(self, license_manager=self.license_manager)

        # 통합 도구 탭
        self.dogu_tab = DoguTab(self, license_manager=self.license_manager)

        # 홈 탭
        self.home_tab = HomeTab(switch_tab_fn=self._switch_to)

        # 메인 탭 추가 (0:홈 1:자동화 2:콘솔 3:진단 4:도구 5:정보)
        self.tabs.addTab(self.home_tab,       self.translate("🏠 홈"))
        self.tabs.addTab(self.network_tab,    self.translate("네트워크 자동화"))
        self.tabs.addTab(self.console_tab,    self.translate("콘솔"))
        self.tabs.addTab(self.diagnostic_tab, self.translate("네트워크 진단"))
        self.tabs.addTab(self.dogu_tab,       self.translate("도구"))
        self.tabs.addTab(self.about_tab,      self.translate("정보"))
  


                
        # ── 업데이트 배너 (평소엔 숨김) ─────────────────────────────────────────
        self._update_banner = QWidget()
        self._update_banner.setStyleSheet(
            'QWidget{background:#fef3c7;border-bottom:1px solid #fcd34d}'
        )
        banner_row = QHBoxLayout(self._update_banner)
        banner_row.setContentsMargins(16, 6, 16, 6)
        banner_row.setSpacing(10)

        self._banner_icon = QLabel('🆕')
        self._banner_icon.setFont(QFont('맑은 고딕', 11))
        self._banner_icon.setStyleSheet('background:transparent;border:none')
        banner_row.addWidget(self._banner_icon)

        self._banner_msg = QLabel('')
        self._banner_msg.setFont(QFont('맑은 고딕', 9))
        self._banner_msg.setStyleSheet('color:#92400e;background:transparent;border:none')
        banner_row.addWidget(self._banner_msg, 1)

        self._banner_dl_btn = QPushButton('⬇  다운로드')
        self._banner_dl_btn.setFixedHeight(26)
        self._banner_dl_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        self._banner_dl_btn.setStyleSheet(
            'QPushButton{background:#d97706;color:#fff;border:none;border-radius:5px;padding:0 12px}'
            'QPushButton:hover{background:#b45309}'
        )
        banner_row.addWidget(self._banner_dl_btn)

        self._banner_close_btn = QPushButton('✕')
        self._banner_close_btn.setFixedSize(22, 22)
        self._banner_close_btn.setFont(QFont('맑은 고딕', 9))
        self._banner_close_btn.setStyleSheet(
            'QPushButton{background:transparent;color:#92400e;border:none}'
            'QPushButton:hover{color:#78350f}'
        )
        self._banner_close_btn.clicked.connect(self._update_banner.hide)
        banner_row.addWidget(self._banner_close_btn)

        self._update_banner.hide()
        main_layout.addWidget(self._update_banner)
        main_layout.addWidget(self.tabs)

        # 탭 전환 시 라이센스 체크
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # 스타일 적용
        self.apply_styles()


    








    def _switch_to(self, tab_idx, dogu_sub=None):
        """홈 카드 클릭 시 메인 탭 + 도구 서브탭 동시 이동"""
        self.tabs.setCurrentIndex(tab_idx)
        if dogu_sub is not None:
            self.dogu_tab._select(dogu_sub)


    def _on_tab_changed(self, index):
        pass

    def create_menu_bar(self):
        """메뉴바 생성 (언어 설정 제외)"""
        menu_bar = self.menuBar()

        # 📁 파일 메뉴
        file_menu = menu_bar.addMenu("File")

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

        # 🛠 도구 메뉴
        tools_menu = menu_bar.addMenu("Tools")

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

        tools_menu.addSeparator()
        about_action = QAction(self.translate("프로그램 정보"), self)
        about_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.about_tab))
        tools_menu.addAction(about_action)

        # 🌐 언어 메뉴
        lang_menu = menu_bar.addMenu("Language")

        ko_action = QAction('한국어', self)
        ko_action.setCheckable(True)
        ko_action.setChecked(get_language() == 'ko')
        ko_action.triggered.connect(lambda: self._change_language('ko'))
        lang_menu.addAction(ko_action)

        en_action = QAction('English', self)
        en_action.setCheckable(True)
        en_action.setChecked(get_language() == 'en')
        en_action.triggered.connect(lambda: self._change_language('en'))
        lang_menu.addAction(en_action)

        # 🌙 테마 초기화
        self.current_theme = "dark"
        self.apply_styles()



    # ── 업데이트 체크 ────────────────────────────────────────────────────────
    def _start_update_check(self):
        # config.json 의 auto_update 설정이 False 면 건너뜀
        try:
            _cp = _config_path()
            if os.path.exists(_cp):
                with open(_cp, encoding='utf-8') as _f:
                    if not json.load(_f).get('auto_update', True):
                        return
        except Exception:
            pass
        self._update_checker = UpdateChecker()
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.start()

    def _on_update_available(self, info: dict):
        ver  = info.get('version', '?')
        lang = get_language()
        msg  = info.get('message_en' if lang == 'en' else 'message', '')
        date = info.get('release_date', '')
        self._update_download_url = info.get('download_url', 'https://auto-network.co.kr')

        if lang == 'en':
            text = f'New version {ver} available ({date})  —  {msg}'
            btn_text = '⬇  Download'
        else:
            text = f'새 버전 {ver} 업데이트가 있습니다 ({date})  —  {msg}'
            btn_text = '⬇  다운로드'

        self._banner_msg.setText(text)
        self._banner_dl_btn.setText(btn_text)
        # 시그널 중복 연결 방지
        try:
            self._banner_dl_btn.clicked.disconnect()
        except TypeError:
            pass
        self._banner_dl_btn.clicked.connect(self._start_auto_update)
        self._update_banner.show()
        logging.info(f'[Updater] 새 버전 감지: {ver}')

    def _start_auto_update(self):
        """다운로드 진행 다이얼로그 띄우고 AutoUpdater 스레드 시작"""
        if not self._update_download_url:
            return

        lang = get_language()
        title = 'Updating...' if lang == 'en' else '업데이트 중...'

        self._update_dlg = QDialog(self)
        self._update_dlg.setWindowTitle(title)
        self._update_dlg.setFixedSize(400, 130)
        self._update_dlg.setWindowFlags(
            self._update_dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        v = QVBoxLayout(self._update_dlg)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)

        self._update_status_lbl = QLabel('다운로드 준비 중...' if lang != 'en' else 'Preparing download...')
        self._update_status_lbl.setFont(QFont('맑은 고딕', 9))
        v.addWidget(self._update_status_lbl)

        self._update_progress_bar = QProgressBar()
        self._update_progress_bar.setRange(0, 100)
        self._update_progress_bar.setValue(0)
        self._update_progress_bar.setFixedHeight(18)
        v.addWidget(self._update_progress_bar)

        cancel_btn = QPushButton('취소' if lang != 'en' else 'Cancel')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setFont(QFont('맑은 고딕', 9))
        cancel_btn.clicked.connect(self._cancel_update)
        v.addWidget(cancel_btn, 0, Qt.AlignRight)

        self._auto_updater = AutoUpdater(self._update_download_url)
        self._auto_updater.progress.connect(self._on_update_progress)
        self._auto_updater.finished.connect(self._on_update_finished)
        self._auto_updater.start()

        self._update_dlg.exec_()

    def _cancel_update(self):
        if hasattr(self, '_auto_updater') and self._auto_updater.isRunning():
            self._auto_updater.terminate()
        if hasattr(self, '_update_dlg'):
            self._update_dlg.reject()

    def _on_update_progress(self, pct: int, msg: str):
        if hasattr(self, '_update_progress_bar'):
            self._update_progress_bar.setValue(pct)
        if hasattr(self, '_update_status_lbl'):
            self._update_status_lbl.setText(msg)

    def _on_update_finished(self, success: bool, result: str):
        if hasattr(self, '_update_dlg'):
            self._update_dlg.accept()

        if success:
            bat_path = result
            lang = get_language()
            msg = ('Update downloaded. The program will restart now.' if lang == 'en'
                   else '업데이트 다운로드 완료.\n프로그램을 재시작하여 업데이트를 적용합니다.')
            QMessageBox.information(self, '업데이트' if lang != 'en' else 'Update', msg)
            try:
                subprocess.Popen(['cmd', '/c', bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            except Exception as e:
                logging.error(f'[Updater] 배치 실행 실패: {e}')
            QApplication.quit()
        else:
            lang = get_language()
            err_title = '업데이트 실패' if lang != 'en' else 'Update Failed'
            err_msg = f'다운로드 중 오류가 발생했습니다:\n{result}' if lang != 'en' else f'Download error:\n{result}'
            QMessageBox.warning(self, err_title, err_msg)

    def _change_language(self, lang: str):
        if get_language() == lang:
            return
        set_language(lang)
        msg = 'Language changed. Please restart the program to apply.' if lang == 'en' \
              else '언어가 변경되었습니다. 프로그램을 재시작하면 적용됩니다.'
        QMessageBox.information(self, tr('언어 변경'), msg)

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
        """로그 파일 보기 — FileViewerTab 다이얼로그 (검색·구문 강조·필터 포함)"""
        import glob
        from ui.file_viewer_tab import FileViewerTab

        log_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'logs')
        if not os.path.isdir(log_dir):
            log_dir = os.path.join(os.getcwd(), 'logs')

        log_files = sorted(glob.glob(os.path.join(log_dir, 'network_automation_*.log')))
        if not log_files:
            QMessageBox.information(self, self.translate("알림"), "로그 파일이 아직 생성되지 않았습니다.")
            return

        latest = log_files[-1]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"로그 파일 뷰어 — {os.path.basename(latest)}")
        dlg.resize(1100, 680)
        dlg.setMinimumSize(800, 500)

        v = QVBoxLayout(dlg)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # FileViewerTab 임베드
        viewer = FileViewerTab(dlg)
        v.addWidget(viewer, 1)

        # 하단 닫기 버튼
        btn_bar = QFrame()
        btn_bar.setFixedHeight(40)
        btn_bar.setStyleSheet('background:#0f172a;border-top:1px solid #1e293b')
        bh = QHBoxLayout(btn_bar)
        bh.setContentsMargins(12, 4, 12, 4)
        bh.addStretch()
        close_btn = QPushButton('✕  닫기')
        close_btn.setFixedHeight(28)
        close_btn.setStyleSheet(
            'QPushButton{background:#2a0000;color:#ff7070;border:1px solid #7f1d1d;'
            'border-radius:4px;padding:0 16px;font-size:9pt}'
            'QPushButton:hover{background:#450a0a}'
        )
        close_btn.clicked.connect(dlg.accept)
        bh.addWidget(close_btn)
        v.addWidget(btn_bar)

        # logs 폴더 자동 로드 + 최신 파일 열기
        viewer._open_folder_path(log_dir)
        viewer._load_file(latest)
        # 맨 아래로 스크롤 (최신 로그 바로 보기)
        viewer._ed.moveCursor(QTextCursor.End)

        dlg.exec_()
        self.statusBar.showMessage(f"로그 파일: {os.path.basename(latest)}", 3000)

        



        


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
        use_serial = self.network_tab.serial_radio.isChecked()
        ssh_port = int(self.network_tab.ssh_port_input.text()) if use_ssh and self.network_tab.ssh_port_input.text().isdigit() else 22
        serial_params = self.network_tab.get_serial_params() if use_serial else {}
        commands = [cmd.strip() for cmd in self.network_tab.command_input.toPlainText().splitlines() if cmd.strip()]

        # 입력 검증
        if not ip_list:
            label = "COM 포트 리스트를 입력해주세요!" if use_serial else "IP 리스트를 입력해주세요!"
            QMessageBox.warning(self, self.translate("입력 오류"), label)
            return
        if not use_serial and not password:
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

        # 실제 쓰기 권한 테스트
        _test_file = os.path.join(save_path, '.write_test')
        try:
            with open(_test_file, 'w') as _f:
                _f.write('')
            os.remove(_test_file)
        except OSError:
            _safe_path = os.path.join(os.path.expanduser('~'), 'Documents', 'NetworkAutomation')
            reply = QMessageBox.warning(
                self, "저장 경로 권한 오류",
                f"선택한 경로에 파일을 저장할 수 없습니다 (권한 없음):\n{save_path}\n\n"
                f"다음 경로로 변경하시겠습니까?\n{_safe_path}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                save_path = _safe_path
                self.network_tab.save_path_input.setText(_safe_path)
                os.makedirs(_safe_path, exist_ok=True)
                logging.info(f"[INFO] 저장 경로 자동 변경됨: {_safe_path}")
            else:
                return

        # 입력 필드 비활성화
        self.toggle_inputs(False)

        # 진행 상태 초기화
        self.workers = []
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_tasks = len(ip_list)
        self._execution_stopped = False  # 중지 플래그 초기화
        self.network_tab.start_counter(self.total_tasks)

        # 상태바 업데이트
        self.statusBar.showMessage(f"명령어 실행 시작... ({len(ip_list)}개 장비)")

        # 동시 실행 또는 순차 실행
        if self.network_tab.concurrent_radio.isChecked():
            self.execute_concurrently(ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port,
                                      use_serial=use_serial, serial_params=serial_params)
        else:
            self.execute_sequentially(ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port,
                                      use_serial=use_serial, serial_params=serial_params)

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

    def execute_concurrently(self, ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22,
                             use_serial=False, serial_params=None):
        """여러 장비에 대해 동시에 명령어 실행 (최대 50개 동시 스레드 제한)"""
        MAX_CONCURRENT = 50
        filename_format = self.network_tab.get_filename_format()
        serial_params = serial_params or {}

        # 50개 초과 시 경고
        if len(ip_list) > MAX_CONCURRENT:
            logging.warning(f"[WARN] 장비 수({len(ip_list)})가 동시 실행 한계({MAX_CONCURRENT})를 초과. "
                            f"처음 {MAX_CONCURRENT}개만 즉시 실행, 나머지는 순차 대기.")

        for ip in ip_list[:MAX_CONCURRENT]:
            com_port = ip if use_serial else serial_params.get('com_port', 'COM1')
            worker = NetworkWorker(ip, username, password, enable_password, use_ssh, save_path, commands, ssh_port,
                                   use_serial=use_serial, com_port=com_port,
                                   baud_rate=serial_params.get('baud_rate', 9600))
            worker.filename_format = filename_format
            worker.task_completed.connect(self.handle_task_completed)
            worker.error_occurred.connect(self.handle_error)
            worker.status_update.connect(self.update_execution_status)

            # SSH 디버그 대화상자 연결 추가
            if use_ssh:
                self.network_tab.start_ssh_debug_dialog(worker)

            # Worker 시작
            self.workers.append(worker)
            worker.start()
            logging.info(f"[INFO] 작업 시작: {ip}")

        # 50개 초과분은 순차 처리로 연계
        if len(ip_list) > MAX_CONCURRENT:
            self._overflow_ip_list = ip_list[MAX_CONCURRENT:]
            self._overflow_params = dict(
                username=username, password=password, enable_password=enable_password,
                use_ssh=use_ssh, save_path=save_path, commands=commands, ssh_port=ssh_port,
                use_serial=use_serial, serial_params=serial_params
            )
        else:
            self._overflow_ip_list = []

    def execute_sequentially(self, ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22,
                             use_serial=False, serial_params=None):
        """장비별로 순차적으로 명령어 실행"""
        self.sequential_execution_list = ip_list
        self.sequential_index = 0
        self.sequential_params = {
            "username": username,
            "password": password,
            "enable_password": enable_password,
            "use_ssh": use_ssh,
            "use_serial": use_serial,
            "serial_params": serial_params or {},
            "save_path": save_path,
            "commands": commands,
            "ssh_port": ssh_port,
            "filename_format": self.network_tab.get_filename_format(),
        }
        self.start_sequential_execution()

    def start_sequential_execution(self):
        """순차 실행의 다음 장비 처리"""
        if self.sequential_index < len(self.sequential_execution_list):
            ip = self.sequential_execution_list[self.sequential_index]
            sp = self.sequential_params
            use_serial = sp.get("use_serial", False)
            serial_p = sp.get("serial_params", {})
            com_port = ip if use_serial else serial_p.get('com_port', 'COM1')
            worker = NetworkWorker(
                ip,
                sp["username"],
                sp["password"],
                sp["enable_password"],
                sp["use_ssh"],
                sp["save_path"],
                sp["commands"],
                sp["ssh_port"],
                use_serial=use_serial,
                com_port=com_port,
                baud_rate=serial_p.get('baud_rate', 9600),
            )
            worker.filename_format = sp["filename_format"]

            worker.task_completed.connect(self.handle_sequential_task_completed)
            worker.error_occurred.connect(self.handle_error)
            worker.status_update.connect(self.update_execution_status)

            # SSH 디버그 대화상자 연결 추가
            if sp["use_ssh"] and not use_serial:
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
        # 완료된 worker의 신호 연결 해제
        sender = self.sender()
        if sender is not None:
            try:
                sender.task_completed.disconnect(self.handle_task_completed)
                sender.error_occurred.disconnect(self.handle_error)
                sender.status_update.disconnect(self.update_execution_status)
            except Exception:
                pass
        if self.completed_tasks == self.total_tasks:
            self.execution_finished()

    def handle_error(self, message, failed_ip=''):
        """오류 처리"""
        logging.error(message)
        QMessageBox.critical(self, self.translate("작업 오류"), message)
        self.failed_tasks += 1
        self.completed_tasks += 1
        self.update_progress(failed_ip=failed_ip)
        # 완료된 worker의 신호 연결 해제
        sender = self.sender()
        if sender is not None:
            try:
                sender.task_completed.disconnect(self.handle_task_completed)
                sender.error_occurred.disconnect(self.handle_error)
                sender.status_update.disconnect(self.update_execution_status)
            except Exception:
                pass
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

        # 최대 500줄 유지 (대규모 실행 시 메모리 방지)
        doc = self.network_tab.execution_status_label.document()
        MAX_LINES = 500
        while doc.blockCount() > MAX_LINES:
            cursor = self.network_tab.execution_status_label.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 줄 끝 개행 제거

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

    def update_progress(self, failed_ip=''):
        """진행 상태 업데이트"""
        if self.total_tasks > 0:
            ip = failed_ip if isinstance(failed_ip, str) else ''
            self.network_tab.update_counter(self.completed_tasks, self.total_tasks, self.failed_tasks, ip)
            self.statusBar.showMessage(f"작업 진행 중: {self.completed_tasks}/{self.total_tasks} 완료")

    def cleanup_workers(self):
        """완료된 작업자 정리"""
        for worker in self.workers[:]:
            if not worker.isRunning():
                self.workers.remove(worker)
                worker.deleteLater()

    def execution_finished(self):
        """모든 작업 완료 후 처리"""
        # 중지 버튼으로 멈춘 경우 완료 팝업 생략 (이미 stop_execution에서 처리)
        if getattr(self, '_execution_stopped', False):
            return
        self.network_tab.stop_counter()
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
            self._execution_stopped = True  # 완료 팝업 방지 플래그
            for worker in self.workers:
                worker.stop()

            self.statusBar.showMessage("작업 중지 요청됨...")
            logging.info("[INFO] 모든 작업 중지 요청됨.")

            # 2초 후 UI 재활성화 + workers 정리
            def _after_stop():
                self.toggle_inputs(True)
                self.statusBar.showMessage("작업이 중지되었습니다.")
                self.network_tab.stop_counter()
                self.cleanup_workers()
                self.workers = []

            QTimer.singleShot(2000, _after_stop)

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
            with open(_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.statusBar.showMessage("설정이 저장되었습니다.", 3000)
            logging.info("[INFO] 설정 저장됨.")
        except Exception as e:
            QMessageBox.warning(self, self.translate("설정 저장 오류"), f"설정을 저장하는 중 오류가 발생했습니다: {e}")
            logging.error(f"[ERROR] 설정 저장 실패: {e}")

    def load_configuration(self):
            """설정 불러오기"""
            _cp = _config_path()
            if os.path.exists(_cp):
                try:
                    with open(_cp, 'r', encoding='utf-8') as f:
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