"""
업데이트 체크 / 자동 업데이트 모듈
- UpdateChecker  : 앱 시작 시 백그라운드 버전 체크
- AutoUpdater    : 새 버전 다운로드 + 배치 파일로 자동 교체
"""
import os
import sys
import json
import logging
import tempfile
import urllib.request
import urllib.error

from PyQt5.QtCore import QThread, pyqtSignal

CURRENT_VERSION = "8.0"
VERSION_URL     = "https://auto-network.co.kr/version.json"


def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in str(v).strip().split('.'))
    except Exception:
        return (0,)


def is_newer(remote: str, current: str = CURRENT_VERSION) -> bool:
    return _parse_version(remote) > _parse_version(current)


def get_exe_path() -> str:
    """현재 실행 파일 경로 반환 (PyInstaller exe / 일반 스크립트 모두 처리)"""
    if getattr(sys, 'frozen', False):
        return sys.executable          # PyInstaller exe
    return os.path.abspath(sys.argv[0])  # 개발 환경


# ── 버전 체크 스레드 ──────────────────────────────────────────────────────────
class UpdateChecker(QThread):
    update_available = pyqtSignal(dict)
    check_failed     = pyqtSignal(str)

    def run(self):
        try:
            req = urllib.request.Request(
                VERSION_URL,
                headers={'User-Agent': f'NetworkAutomation/{CURRENT_VERSION}'},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            remote_ver = str(data.get('version', '0'))
            if is_newer(remote_ver):
                self.update_available.emit(data)
            else:
                logging.debug(f'[Updater] 최신 버전 사용 중 ({CURRENT_VERSION})')

        except urllib.error.URLError as e:
            logging.debug(f'[Updater] 버전 체크 실패 (네트워크): {e}')
            self.check_failed.emit(str(e))
        except Exception as e:
            logging.debug(f'[Updater] 버전 체크 오류: {e}')
            self.check_failed.emit(str(e))


# ── 자동 업데이트 스레드 ──────────────────────────────────────────────────────
class AutoUpdater(QThread):
    """새 버전 exe 다운로드 후 교체 배치 파일 생성"""
    progress = pyqtSignal(int, str)    # (퍼센트, 상태 메시지)
    finished = pyqtSignal(bool, str)   # (성공 여부, 배치경로 or 오류메시지)

    def __init__(self, download_url: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url

    def run(self):
        try:
            self.progress.emit(0, '다운로드 준비 중...')

            # 임시 폴더에 새 exe 저장
            tmp_dir  = tempfile.mkdtemp(prefix='na_update_')
            filename = os.path.basename(self.download_url.split('?')[0]) or 'NetworkAutomation_new.exe'
            tmp_exe  = os.path.join(tmp_dir, filename)

            req = urllib.request.Request(
                self.download_url,
                headers={'User-Agent': f'NetworkAutomation/{CURRENT_VERSION}'},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total      = int(resp.headers.get('Content-Length', 0))
                downloaded = 0

                with open(tmp_exe, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded / total * 90)
                            kb_done  = downloaded // 1024
                            kb_total = total // 1024
                            self.progress.emit(pct, f'다운로드 중...  {kb_done:,} KB / {kb_total:,} KB')
                        else:
                            self.progress.emit(50, f'다운로드 중...  {downloaded // 1024:,} KB')

            self.progress.emit(95, '업데이트 적용 준비 중...')

            # 배치 파일 생성
            bat_path = self._create_batch(tmp_exe)

            self.progress.emit(100, '준비 완료!')
            self.finished.emit(True, bat_path)

        except Exception as e:
            logging.error(f'[Updater] 다운로드 실패: {e}')
            self.finished.emit(False, str(e))

    def _create_batch(self, new_exe: str) -> str:
        """
        앱 종료 후 새 exe로 교체하고 재시작하는 Windows 배치 파일 생성.
        실행 중인 exe는 바로 덮어쓸 수 없으므로 종료될 때까지 루프 대기.
        """
        current_exe = get_exe_path()
        exe_name    = os.path.basename(current_exe)
        bat_path    = os.path.join(os.path.dirname(new_exe), 'na_update.bat')

        script = (
            '@echo off\n'
            'chcp 65001 > nul\n'
            f'echo [{exe_name}] 업데이트 적용 중...\n'
            ':wait\n'
            f'tasklist /fi "imagename eq {exe_name}" 2>nul '
            f'| find /i "{exe_name}" > nul\n'
            'if not errorlevel 1 (\n'
            '    timeout /t 1 /nobreak > nul\n'
            '    goto wait\n'
            ')\n'
            f'move /y "{new_exe}" "{current_exe}" > nul\n'
            'if errorlevel 1 (\n'
            '    echo 파일 교체 실패. 수동으로 교체해주세요.\n'
            '    pause\n'
            '    exit /b 1\n'
            ')\n'
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )

        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(script)

        return bat_path
