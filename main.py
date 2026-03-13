import sys
import os
import logging
from datetime import datetime

# PyInstaller 환경 감지 및 경로 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 실행 파일인 경우
    base_dir = sys._MEIPASS
    executable_dir = os.path.dirname(sys.executable)
else:
    # 개발 환경인 경우
    base_dir = os.path.dirname(os.path.abspath(__file__))
    executable_dir = base_dir

print("PyInstaller 환경:", getattr(sys, 'frozen', False))
print("기본 디렉토리:", base_dir)
print("실행 파일 디렉토리:", executable_dir)

# Python 경로 설정
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'ui'))
sys.path.insert(0, os.path.join(base_dir, 'core'))
sys.path.insert(0, os.path.join(base_dir, 'core', 'log_analyzer'))

print("Python 경로:")
for i, path in enumerate(sys.path[:8]):  # 처음 8개 경로만 출력
    print(f"  {i}: {path}")

# PyQt5 라이브러리
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import Qt
    print("PyQt5 import 성공")
except ImportError as e:
    print(f"PyQt5 import 실패: {e}")
    sys.exit(1)

def setup_logging():
    """로깅 환경 설정"""
    try:
        # 로그 디렉토리 생성 (실행 파일과 같은 디렉토리)
        if getattr(sys, 'frozen', False):
            log_dir = os.path.join(executable_dir, 'logs')
        else:
            log_dir = os.path.join(base_dir, 'logs')
        
        os.makedirs(log_dir, exist_ok=True)

        # 로그 파일 이름 (날짜 포함)
        log_filename = os.path.join(log_dir, f'network_automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()  # 콘솔 출력도 유지
            ]
        )
        logging.info(f"로그 파일 생성: {log_filename}")
        
    except Exception as e:
        print(f"로깅 설정 실패: {e}")

def show_error_dialog(title, message):
    """오류 다이얼로그 표시"""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setDetailedText(f"Python Path:\n" + "\n".join(sys.path[:5]))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
    except Exception as e:
        print(f"오류 다이얼로그 표시 실패: {e}")

def main():
    """메인 애플리케이션 실행"""
    try:
        # 로깅 설정
        setup_logging()

        # === 여기에 추가하세요 ===
        # paramiko 초기화 (workers.py에서 import)
        try:
            from core.workers import ensure_paramiko_initialized
            ensure_paramiko_initialized()
            logging.info("네트워크 라이브러리 초기화 완료")
        except Exception as e:
            logging.warning(f"네트워크 라이브러리 초기화 실패: {e}")
        # === 추가 끝 ===
        

        logging.info("네트워크 자동화 애플리케이션 시작")
        logging.info(f"Python 버전: {sys.version}")
        logging.info(f"PyInstaller 환경: {getattr(sys, 'frozen', False)}")
        logging.info(f"작업 디렉토리: {os.getcwd()}")
        logging.info(f"실행 파일 디렉토리: {executable_dir}")
        logging.info(f"기본 디렉토리: {base_dir}")

        # PyQt 애플리케이션 생성
        app = QApplication(sys.argv)
        app.setApplicationName("Network Automation")
        app.setApplicationVersion("6.1")

        # 애플리케이션 아이콘 설정 (선택적)
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, 'icons', 'app_icon.ico')
            else:
                icon_path = os.path.join(base_dir, 'icons', 'app_icon.ico')
            
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                app.setWindowIcon(app_icon)
                logging.info(f"아이콘 로드 성공: {icon_path}")
            else:
                logging.warning(f"아이콘 파일을 찾을 수 없음: {icon_path}")
                
        except Exception as icon_error:
            logging.warning(f"애플리케이션 아이콘 로드 실패: {icon_error}")

        # main_window import 및 생성 시도
        try:
            # 여러 방법으로 import 시도
            logging.info("main_window 모듈 import 시도 중...")
            
            try:
                # 방법 1: ui.main_window로 import
                from ui.main_window import NetworkAutomationApp
                logging.info("ui.main_window에서 import 성공")
            except ImportError as e1:
                logging.warning(f"ui.main_window import 실패: {e1}")
                try:
                    # 방법 2: main_window로 직접 import
                    from main_window import NetworkAutomationApp
                    logging.info("main_window에서 직접 import 성공")
                except ImportError as e2:
                    logging.warning(f"main_window 직접 import 실패: {e2}")
                    # 방법 3: 파일 경로 확인 후 수동 import
                    ui_path = os.path.join(base_dir, 'ui')
                    main_window_path = os.path.join(ui_path, 'main_window.py')
                    
                    logging.info(f"UI 경로 확인: {ui_path}")
                    logging.info(f"main_window.py 파일 확인: {os.path.exists(main_window_path)}")
                    
                    if os.path.exists(main_window_path):
                        # ui 디렉토리를 sys.path 맨 앞에 추가
                        if ui_path not in sys.path:
                            sys.path.insert(0, ui_path)
                        from main_window import NetworkAutomationApp
                        logging.info("수동 경로 설정 후 import 성공")
                    else:
                        raise ImportError(f"main_window.py 파일을 찾을 수 없습니다: {main_window_path}")
            
            # 메인 윈도우 생성 및 표시
            logging.info("메인 윈도우 생성 중...")
            main_window = NetworkAutomationApp()
            main_window.show()
            logging.info("메인 윈도우 생성 및 표시 완료")
            
        except ImportError as import_error:
            error_msg = f"main_window 모듈 import 실패:\n{import_error}\n\n현재 Python 경로:\n" + "\n".join(sys.path[:5])
            logging.critical(error_msg)
            show_error_dialog("Import 오류", error_msg)
            return 1
            
        except Exception as window_error:
            error_msg = f"메인 윈도우 생성 실패: {window_error}"
            logging.critical(error_msg, exc_info=True)
            show_error_dialog("윈도우 생성 오류", error_msg)
            return 1

        # 애플리케이션 실행
        logging.info("애플리케이션 이벤트 루프 시작")
        return app.exec_()

    except Exception as e:
        error_msg = f"애플리케이션 실행 중 심각한 오류 발생: {e}"
        logging.critical(error_msg, exc_info=True)
        show_error_dialog("심각한 오류", error_msg)
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logging.info("사용자에 의해 프로그램이 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        sys.exit(1)