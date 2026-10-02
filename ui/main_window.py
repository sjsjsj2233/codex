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
def _config_path() -> str:
    d = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'NetworkAutomation')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'config.json')


def _xlsx_safe(value) -> str:
    """Excel(XML)에서 허용하지 않는 제어문자 제거.

    PAN-OS의 'show system resources'/'show running resource-monitor' 같은
    라이브 갱신형 명령은 캡처된 원문에 ANSI 이스케이프(ESC 0x1B 등) 제어문자가
    섞여 들어오는데, openpyxl은 이 문자를 만나면 IllegalCharacterError를 던져
    Excel 저장 단계에서 앱이 그대로 죽는다. 셀에 쓰기 전 항상 이 필터를 거친다.
    """
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    return ILLEGAL_CHARACTERS_RE.sub('', str(value))

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
        self._excel_results = {}  # device_index -> {ip, hostname, output_data}
        self.init_ui()
        self.load_configuration()
        self.center_on_screen()
        # 업데이트 체크 (3초 후 백그라운드 실행)
        QTimer.singleShot(3000, self._start_update_check)

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
        self.setWindowTitle(self.translate("네트워크 운영 콘솔") + "  |  Network Automation v9.9")
        self.setMinimumSize(960, 640)
        self.setGeometry(100, 100, 1280, 820)



        # 메뉴바 생성
        self.create_menu_bar()
        
        # 상태바 생성
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(self.translate("작업 준비 완료"))
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        brand_bar = QFrame()
        brand_bar.setObjectName("brandBar")
        brand_bar.setFixedHeight(70)
        brand_bar.setStyleSheet("#brandBar{background:#ffffff;border-bottom:1px solid #e7edf5}")
        brand_row = QHBoxLayout(brand_bar)
        brand_row.setContentsMargins(26, 0, 28, 0)
        brand_row.setSpacing(12)
        mark = QLabel("N")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet("background:#152945;color:#78d5f4;border-radius:9px;font-size:17px;font-weight:800")
        brand_row.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_title = QLabel("NETWORK AUTOMATION")
        brand_title.setStyleSheet("color:#152945;font-size:12px;font-weight:800;letter-spacing:1px")
        brand_subtitle = QLabel(self.translate("Cisco 네트워크 운영 워크스페이스"))
        brand_subtitle.setStyleSheet("color:#8293a9;font-size:9px")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_subtitle)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        version_label = QLabel("v9.9  /  DESKTOP")
        version_label.setStyleSheet("color:#7d8fa5;background:#f3f6fb;border-radius:6px;padding:6px 10px;font-size:9px;font-weight:700")
        brand_row.addWidget(version_label)
        main_layout.addWidget(brand_bar)
        
        # 탭 위젯 생성
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.setDocumentMode(True)   # 탭 아래 경계선 제거 (더 깔끔)
        
        # 메인 탭 생성
        self.network_tab = NetworkTab(self)
        
        # 네트워크 진단 탭
        self.diagnostic_tab = MonitoringTab()

        # 콘솔 탭
        self.console_tab = ConsoleTab()





        
        self.about_tab = AboutTab(self)

        # 통합 도구 탭
        self.dogu_tab = DoguTab(self)

        # 홈 탭
        self.home_tab = HomeTab(switch_tab_fn=self._switch_to)

        # 메인 탭 추가 (0:홈 1:자동화 2:콘솔 3:진단 4:도구 5:정보)
        self.tabs.addTab(self.home_tab,       self.translate("개요"))
        self.tabs.addTab(self.network_tab,    self.translate("장비 자동화"))
        self.tabs.addTab(self.console_tab,    self.translate("실시간 콘솔"))
        self.tabs.addTab(self.diagnostic_tab, self.translate("연결 진단"))
        self.tabs.addTab(self.dogu_tab,       self.translate("분석 · 보고서"))
        self.tabs.addTab(self.about_tab,      self.translate("앱 정보"))
  


                
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

        # 🛠 도구 메뉴
        tools_menu = menu_bar.addMenu(self.translate("화면"))

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
        lang_menu = menu_bar.addMenu(self.translate("언어"))

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
        vendor = self.network_tab.get_vendor()
        output_format = self.network_tab.get_output_format()
        txt_fmt = self.network_tab.get_config_txt_format()
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
        self._excel_results = {}         # Excel 결과 초기화
        self.network_tab.start_counter(self.total_tasks)

        # TXT "통합 파일" 모드: 실행 전에 공유 파일 + 락을 준비 (동시 실행 시 장비 블록이 섞이지 않도록)
        shared_txt_path = None
        shared_txt_lock = None
        if output_format in ("txt", "both") and txt_fmt == "single":
            import threading
            from datetime import datetime
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            shared_txt_path = os.path.join(save_path, f"네트워크_수집결과_통합_{ts}.txt")
            open(shared_txt_path, 'w', encoding='utf-8').close()
            shared_txt_lock = threading.Lock()

        # 상태바 업데이트
        self.statusBar.showMessage(f"명령어 실행 시작... ({len(ip_list)}개 장비)")

        # 동시 실행 또는 순차 실행
        if self.network_tab.concurrent_radio.isChecked():
            self.execute_concurrently(ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port,
                                      use_serial=use_serial, serial_params=serial_params, vendor=vendor,
                                      shared_txt_path=shared_txt_path, shared_txt_lock=shared_txt_lock)
        else:
            self.execute_sequentially(ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port,
                                      use_serial=use_serial, serial_params=serial_params, vendor=vendor,
                                      shared_txt_path=shared_txt_path, shared_txt_lock=shared_txt_lock)

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
                             use_serial=False, serial_params=None, vendor='cisco',
                             shared_txt_path=None, shared_txt_lock=None):
        """여러 장비에 대해 동시에 명령어 실행 (최대 50개 동시 스레드 제한)"""
        MAX_CONCURRENT = 50
        filename_format = self.network_tab.get_filename_format()
        output_format = self.network_tab.get_output_format()
        serial_params = serial_params or {}

        # 50개 초과 시 경고
        if len(ip_list) > MAX_CONCURRENT:
            logging.warning(f"[WARN] 장비 수({len(ip_list)})가 동시 실행 한계({MAX_CONCURRENT})를 초과. "
                            f"처음 {MAX_CONCURRENT}개만 즉시 실행, 나머지는 순차 대기.")

        for idx, ip in enumerate(ip_list[:MAX_CONCURRENT], 1):
            com_port = ip if use_serial else serial_params.get('com_port', 'COM1')
            worker = NetworkWorker(ip, username, password, enable_password, use_ssh, save_path, commands, ssh_port,
                                   use_serial=use_serial, com_port=com_port,
                                   baud_rate=serial_params.get('baud_rate', 9600),
                                   device_index=idx, output_format=output_format, vendor=vendor,
                                   shared_txt_path=shared_txt_path, shared_txt_lock=shared_txt_lock)
            worker.filename_format = filename_format
            worker.task_completed.connect(self.handle_task_completed)
            worker.error_occurred.connect(self.handle_error)
            worker.status_update.connect(self.update_execution_status)
            worker.result_data_ready.connect(self.handle_result_data)

            # SSH 디버그 대화상자 연결 추가
            if use_ssh:
                self.network_tab.start_ssh_debug_dialog(worker)

            # Worker 시작
            self.workers.append(worker)
            worker.start()
            logging.info(f"[INFO] 작업 시작: {ip} (순번 {idx})")

        # 50개 초과분은 순차 처리로 연계
        if len(ip_list) > MAX_CONCURRENT:
            self._overflow_ip_list = ip_list[MAX_CONCURRENT:]
            self._overflow_params = dict(
                username=username, password=password, enable_password=enable_password,
                use_ssh=use_ssh, save_path=save_path, commands=commands, ssh_port=ssh_port,
                use_serial=use_serial, serial_params=serial_params, vendor=vendor,
                shared_txt_path=shared_txt_path, shared_txt_lock=shared_txt_lock,
            )
        else:
            self._overflow_ip_list = []

    def execute_sequentially(self, ip_list, username, password, enable_password, use_ssh, save_path, commands, ssh_port=22,
                             use_serial=False, serial_params=None, vendor='cisco',
                             shared_txt_path=None, shared_txt_lock=None):
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
            "output_format": self.network_tab.get_output_format(),
            "vendor": vendor,
            "shared_txt_path": shared_txt_path,
            "shared_txt_lock": shared_txt_lock,
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
            device_index = self.sequential_index + 1  # 1-based 순번
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
                device_index=device_index,
                output_format=sp.get("output_format", "txt"),
                vendor=sp.get("vendor", "cisco"),
                shared_txt_path=sp.get("shared_txt_path"),
                shared_txt_lock=sp.get("shared_txt_lock"),
            )
            worker.filename_format = sp["filename_format"]

            worker.task_completed.connect(self.handle_sequential_task_completed)
            worker.error_occurred.connect(self.handle_error)
            worker.status_update.connect(self.update_execution_status)
            worker.result_data_ready.connect(self.handle_result_data)

            # SSH 디버그 대화상자 연결 추가
            if sp["use_ssh"] and not use_serial:
                self.network_tab.start_ssh_debug_dialog(worker)

            self.workers.append(worker)
            worker.start()
            self.statusBar.showMessage(f"작업 진행 중: {ip} ({self.sequential_index + 1}/{len(self.sequential_execution_list)})")
            logging.info(f"[INFO] 순차 실행 작업 시작: {ip} (순번 {device_index})")
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

    def handle_result_data(self, device_index, ip, hostname, output_data):
        """Excel 저장용 결과 데이터 수집"""
        self._excel_results[device_index] = {
            'ip': ip,
            'hostname': hostname,
            'output_data': output_data,
        }

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

        # Excel 저장 (excel 또는 both 형식 선택 시)
        output_format = self.network_tab.get_output_format()
        if output_format in ("excel", "both") and self._excel_results:
            self._save_excel_results()

        QMessageBox.information(self, self.translate("작업 완료"), "모든 작업이 완료되었습니다!")
        logging.info("[INFO] 모든 작업 완료됨.")
        self.toggle_inputs(True)
        self.statusBar.showMessage("모든 작업이 완료되었습니다.")
        self.save_configuration()
        self.cleanup_workers()

    def _save_excel_results(self):
        """수집된 결과 데이터를 Excel 파일로 저장 — 시트 구성 방식에 따라 분기"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            from datetime import datetime
        except ImportError:
            QMessageBox.warning(self, "라이브러리 오류", "openpyxl 라이브러리가 없어 Excel 저장을 건너뜁니다.")
            return

        save_path  = self.network_tab.save_path_input.text().strip()
        cfg_fmt    = self.network_tab.get_config_excel_format()   # per_device / single / by_cmd
        timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')

        fmt_label = {'per_device': '장비별', 'single': '통합', 'by_cmd': '명령어별'}.get(cfg_fmt, cfg_fmt)
        excel_path = os.path.join(save_path, f"네트워크_수집결과_{fmt_label}_{timestamp}.xlsx")

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        # ── 공통 스타일 ────────────────────────────────────────────────────
        S = {
            'title':  Font(bold=True, size=10, color="FFFFFF"),
            'fill_navy':   PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid"),
            'fill_blue':   PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid"),
            'fill_gray':   PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid"),
            'fill_green':  PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid"),
            'fill_hdr':    PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid"),
            'cmd_font':    Font(bold=True, size=9, color="2563EB"),
            'body_font':   Font(name='Consolas', size=9),
            'bold10':      Font(bold=True, size=10),
            'bold9':       Font(bold=True, size=9),
            'al_center':   Alignment(horizontal='center', vertical='center'),
            'al_wrap':     Alignment(wrap_text=True, vertical='top'),
        }
        sorted_keys = sorted(self._excel_results.keys())

        try:
            if cfg_fmt == 'single':
                self._excel_single_sheet(wb, sorted_keys, S, datetime)
            elif cfg_fmt == 'by_cmd':
                self._excel_by_cmd(wb, sorted_keys, S, datetime)
            else:
                self._excel_per_device(wb, sorted_keys, S, datetime)
        except Exception as e:
            QMessageBox.warning(
                self, "Excel 저장 오류",
                f"수집된 결과를 Excel 시트로 만드는 중 오류가 발생해 Excel 저장을 건너뜁니다:\n{e}\n\n"
                "TXT 결과 파일은 정상적으로 저장되어 있습니다."
            )
            logging.error(f"[ERROR] Excel 시트 생성 실패: {e}")
            return

        try:
            wb.save(excel_path)
            logging.info(f"[INFO] Excel 저장 완료: {excel_path}")
        except Exception as e:
            QMessageBox.warning(self, "Excel 저장 오류", f"Excel 파일을 저장할 수 없습니다:\n{e}")
            logging.error(f"[ERROR] Excel 저장 실패: {e}")

    # ── 모드 1: 장비별 시트 ────────────────────────────────────────────────────
    def _excel_per_device(self, wb, sorted_keys, S, datetime):
        """장비마다 독립 시트 — 명령어 블록을 차례로 출력"""
        from openpyxl.styles import Font, PatternFill, Alignment
        for idx in sorted_keys:
            data        = self._excel_results[idx]
            ip          = data['ip']
            hostname    = data['hostname'] or 'N/A'
            output_data = data['output_data']

            raw_name  = f"{idx:03d}_{hostname}"
            sheet_name = raw_name[:31]
            ws = wb.create_sheet(title=sheet_name)
            ws.column_dimensions['A'].width = 110

            for text in [
                f"장비 순번: {idx}",
                f"IP 주소: {ip}",
                f"Hostname: {hostname}",
                f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]:
                ws.append([text])
                c = ws.cell(row=ws.max_row, column=1)
                c.font = S['title']
                c.fill = S['fill_navy']
            ws.append([])

            for cmd, output in output_data.items():
                ws.append([f"▶  Command: {cmd}   [Host: {hostname}]"])
                c = ws.cell(row=ws.max_row, column=1)
                c.font = S['cmd_font']
                c.fill = S['fill_blue']
                for line in _xlsx_safe(output).splitlines():
                    ws.append([line])
                    out_c = ws.cell(row=ws.max_row, column=1)
                    out_c.font = S['body_font']
                    out_c.alignment = Alignment(horizontal='left')
                ws.append(["─" * 80])
                ws.cell(row=ws.max_row, column=1).fill = S['fill_gray']
                ws.append([])

    # ── 모드 2: 통합 시트 (한 장) ────────────────────────────────────────────
    def _excel_single_sheet(self, wb, sorted_keys, S, datetime):
        """모든 장비의 출력을 한 시트에 순서대로 쌓음"""
        from openpyxl.styles import Font, PatternFill, Alignment
        ws = wb.create_sheet(title="전체_통합")
        ws.column_dimensions['A'].width = 110

        for idx in sorted_keys:
            data        = self._excel_results[idx]
            ip          = data['ip']
            hostname    = data['hostname'] or 'N/A'
            output_data = data['output_data']

            # 장비 구분 헤더 (2행)
            ws.append([f"{'━' * 40}  장비 {idx:03d}  {'━' * 40}"])
            c = ws.cell(row=ws.max_row, column=1)
            c.font = S['title']
            c.fill = S['fill_navy']

            ws.append([f"  IP: {ip}   |   Hostname: {hostname}   |   수집: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            c = ws.cell(row=ws.max_row, column=1)
            c.font  = Font(bold=True, size=9, color="1E3A5F")
            c.fill  = S['fill_hdr']
            ws.append([])

            for cmd, output in output_data.items():
                ws.append([f"▶  {cmd}   [Host: {hostname}]"])
                c = ws.cell(row=ws.max_row, column=1)
                c.font = S['cmd_font']
                c.fill = S['fill_blue']
                for line in _xlsx_safe(output).splitlines():
                    ws.append([line])
                    out_c = ws.cell(row=ws.max_row, column=1)
                    out_c.font = S['body_font']
                    out_c.alignment = Alignment(horizontal='left')
                ws.append(["─" * 80])
                ws.cell(row=ws.max_row, column=1).fill = S['fill_gray']
                ws.append([])

            ws.append([])  # 장비 간격

    # ── 모드 3: 명령어별 시트 (★추천) ────────────────────────────────────────
    def _excel_by_cmd(self, wb, sorted_keys, S, datetime):
        """명령어 1개 = 시트 1개.  각 행 = 장비 → 같은 명령어를 여러 장비에서 한눈에 비교"""
        import re
        from openpyxl.styles import Font, PatternFill, Alignment

        # ── 요약 시트 (맨 앞) ────────────────────────────────────────────
        ws_sum = wb.create_sheet(title="00_요약")
        ws_sum.column_dimensions['A'].width = 8
        ws_sum.column_dimensions['B'].width = 18
        ws_sum.column_dimensions['C'].width = 22
        ws_sum.column_dimensions['D'].width = 14
        ws_sum.column_dimensions['E'].width = 14

        hdr_cols = ["순번", "IP 주소", "Hostname", "명령어 수", "수집 시간"]
        ws_sum.append(hdr_cols)
        for col_i, _ in enumerate(hdr_cols, 1):
            c = ws_sum.cell(row=1, column=col_i)
            c.font = S['title']
            c.fill = S['fill_navy']
            c.alignment = S['al_center']
        ws_sum.row_dimensions[1].height = 22

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for idx in sorted_keys:
            data     = self._excel_results[idx]
            hostname = data['hostname'] or 'N/A'
            n_cmds   = len(data['output_data'])
            ws_sum.append([idx, data['ip'], hostname, n_cmds, now_str])
            r = ws_sum.max_row
            for col_i in range(1, 6):
                ws_sum.cell(r, col_i).font = Font(size=9)
                ws_sum.cell(r, col_i).alignment = Alignment(horizontal='center' if col_i in (1,4) else 'left', vertical='center')
            ws_sum.row_dimensions[r].height = 18

        # ── 모든 명령어 수집 (순서 유지) ────────────────────────────────
        seen_cmds = {}
        for idx in sorted_keys:
            for cmd in self._excel_results[idx]['output_data']:
                if cmd not in seen_cmds:
                    seen_cmds[cmd] = []
                seen_cmds[cmd].append(idx)

        def _safe_sheet_name(cmd, n):
            name = re.sub(r'[\\/*?:\[\]]', '_', cmd)
            name = name.strip()[:24]
            return f"{n:02d}_{name}"

        for sheet_n, (cmd, _) in enumerate(seen_cmds.items(), 1):
            sname = _safe_sheet_name(cmd, sheet_n)
            ws = wb.create_sheet(title=sname)

            # 시트 제목 행
            ws.append([f"Command:  {cmd}"])
            c = ws.cell(row=1, column=1)
            c.font = Font(bold=True, size=11, color="FFFFFF")
            c.fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
            ws.row_dimensions[1].height = 24
            ws.append([])

            # 컬럼 설정: A=순번(5), B=IP(16), C=Hostname(22), D=출력내용(100)
            ws.column_dimensions['A'].width = 6
            ws.column_dimensions['B'].width = 16
            ws.column_dimensions['C'].width = 20
            ws.column_dimensions['D'].width = 100

            # 헤더 행
            ws.append(["순번", "IP", "Hostname", "출력 내용"])
            hdr_r = ws.max_row
            for col_i, _ in enumerate(["순번","IP","Hostname","출력 내용"], 1):
                c = ws.cell(hdr_r, col_i)
                c.font  = Font(bold=True, size=9, color="1E3A5F")
                c.fill  = S['fill_hdr']
                c.alignment = S['al_center']
            ws.row_dimensions[hdr_r].height = 20

            # 장비별 한 행 — 출력이 여러 줄이면 개행 포함해서 한 셀에
            for row_n, idx in enumerate(sorted_keys):
                data        = self._excel_results[idx]
                hostname    = data['hostname'] or 'N/A'
                output_data = data['output_data']
                output_text = _xlsx_safe(output_data.get(cmd, '(이 장비에서 실행되지 않음)'))

                ws.append([idx, data['ip'], hostname, output_text])
                r = ws.max_row

                # 셀 스타일
                ws.cell(r, 1).font = Font(bold=True, size=9)
                ws.cell(r, 1).alignment = Alignment(horizontal='center', vertical='top')
                ws.cell(r, 2).font = Font(size=9)
                ws.cell(r, 2).alignment = Alignment(vertical='top')
                ws.cell(r, 3).font = Font(bold=True, size=9)
                ws.cell(r, 3).alignment = Alignment(vertical='top')

                # 출력 셀: Consolas, wrap
                out_cell = ws.cell(r, 4)
                out_cell.font = Font(name='Consolas', size=8)
                out_cell.alignment = Alignment(horizontal='left', wrap_text=True, vertical='top')

                # 홀짝 행 배경 교차
                row_fill = S['fill_blue'] if row_n % 2 == 0 else S['fill_green']
                for col_i in range(1, 5):
                    ws.cell(r, col_i).fill = row_fill

                # 행 높이: 줄 수 기반 (최대 150pt)
                n_lines = min(output_text.count('\n') + 1, 20)
                ws.row_dimensions[r].height = max(18, min(n_lines * 12, 150))

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
