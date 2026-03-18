"""
다국어 지원 모듈 (한국어 / English)
"""
import os
import json

_LANG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.lang')

_current_lang = 'ko'

TRANSLATIONS: dict[str, str] = {
    # ── 메뉴 ──────────────────────────────────────────────────────────────────
    '파일': 'File',
    '설정 불러오기': 'Load Settings',
    '설정 저장': 'Save Settings',
    '결과 폴더 열기': 'Open Results Folder',
    '종료': 'Exit',
    '도구': 'Tools',
    '로그 파일 보기': 'View Log File',
    '폰트 설정': 'Font Settings',
    'UI 새로고침': 'Refresh UI',
    '프로그램 정보': 'About',
    '언어': 'Language',
    '한국어': '한국어',
    'English': 'English',

    # ── 탭 레이블 ─────────────────────────────────────────────────────────────
    '🏠 홈': '🏠 Home',
    '네트워크 자동화': 'Network Automation',
    '네트워크 진단': 'Network Diagnostics',
    '정보': 'About',

    # ── 공통 버튼 / 다이얼로그 ───────────────────────────────────────────────
    '확인': 'OK',
    '닫기': 'Close',
    '취소': 'Cancel',
    '저장': 'Save',
    '열기': 'Open',
    '초기화': 'Reset',
    '중지': 'Stop',
    '실행': 'Execute',
    '전송': 'Send',
    '지우기': 'Clear',
    '연결 해제': 'Disconnect',
    '알림': 'Notice',
    '오류': 'Error',
    '경고': 'Warning',
    '입력 오류': 'Input Error',
    '작업 완료': 'Task Complete',
    '작업 오류': 'Task Error',
    '작업 중지 확인': 'Confirm Stop',
    '폰트 선택': 'Select Font',
    '저장 경로 선택': 'Select Save Path',

    # ── main_window 상태 ──────────────────────────────────────────────────────
    'Ready': 'Ready',
    'UI 새로고침 중...': 'Refreshing UI...',
    '폰트가 변경되었습니다: {font.family()} {font.pointSize()}pt':
        'Font changed: {font.family()} {font.pointSize()}pt',
    '모든 작업이 완료되었습니다!': 'All tasks completed!',
    '모든 작업이 완료되었습니다.': 'All tasks completed.',
    '명령어 실행 시작...': 'Starting command execution...',
    '작업 진행 중': 'Tasks in progress',
    '완료': 'Done',

    # ── 로그 뷰어 ─────────────────────────────────────────────────────────────
    '파일:': 'File:',
    '외부 편집기로 열기': 'Open in External Editor',
    '로그 파일이 아직 생성되지 않았습니다.': 'No log file has been created yet.',

    # ── 네트워크 자동화 탭 헤더 ───────────────────────────────────────────────
    'SSH / Telnet 다중 접속 · 명령어 일괄 실행 · 설정 수집':
        'SSH / Telnet multi-device · Bulk execution · Config backup',

    # ── 빠른 체크 ─────────────────────────────────────────────────────────────
    '장비 IP 리스트': 'Device IP List',
    'IP 주소를 각 줄에\n하나씩 입력하세요': 'Enter one IP address\nper line',
    '빠른 연결 체크': 'Quick Connectivity Check',
    '연결 체크 시작': 'Start Check',
    '체크 대기 중...': 'Waiting...',
    '실패한 IP 자동 제외': 'Auto-exclude failed IPs',
    '체크 중...': 'Checking...',
    'IP 리스트가 비어있습니다': 'IP list is empty',
    '연결 가능': 'Reachable',
    '실패': 'Failed',

    # ── 실행 상태 ─────────────────────────────────────────────────────────────
    '실행 상태': 'Execution Status',
    '대기 중...': 'Waiting...',

    # ── 명령어 입력 ───────────────────────────────────────────────────────────
    '명령어 입력': 'Commands',
    '예시:': 'Example:',
    '템플릿': 'Template',
    '선택하세요...': 'Select...',
    '기본 정보 수집': 'Basic Info',
    '인터페이스 정보': 'Interface Info',
    '라우팅 정보': 'Routing Info',
    '보안 설정 확인': 'Security Check',

    # ── 실행 버튼 ─────────────────────────────────────────────────────────────
    '▶  실행': '▶  Execute',
    '⏹  중지': '⏹  Stop',
    '↺  초기화': '↺  Reset',

    # ── 카운터 패널 ───────────────────────────────────────────────────────────
    '완료 / 전체': 'Done / Total',
    '경과': 'Elapsed',
    '실패한 IP  ·  클릭하면 복사': 'Failed IPs  ·  Click to copy',
    '다시 클릭하면 닫기': 'Click again to dismiss',

    # ── 인증 정보 ─────────────────────────────────────────────────────────────
    '인증 정보': 'Credentials',
    '사용자명': 'Username',
    '비밀번호': 'Password',
    'Enable PW': 'Enable PW',

    # ── 접속 설정 ─────────────────────────────────────────────────────────────
    '접속 설정': 'Connection',
    '접속 방식': 'Protocol',
    'SSH 포트': 'SSH Port',
    '시리얼 (COM)': 'Serial (COM)',
    'COM 포트': 'COM Port',
    '포트 목록 새로고침': 'Refresh port list',
    '보드레이트': 'Baud Rate',
    '🖥  콘솔 연결': '🖥  Open Console',
    '실행 방식': 'Execution Mode',
    '동시 실행': 'Concurrent',
    '순차 실행': 'Sequential',

    # ── 출력 저장 ─────────────────────────────────────────────────────────────
    '출력 저장': 'Output',
    '결과 저장 경로': 'Save path',
    '경로': 'Path',
    '파일명 형식': 'Filename Format',
    'IP만': 'IP only',
    'Hostname만': 'Hostname only',
    'IP + Hostname': 'IP + Hostname',
    'Hostname + IP': 'Hostname + IP',
    '※ Hostname 추출은 sh run 전체가 필요합니다':
        '※ Hostname extraction requires full sh run',

    # ── 초기화 다이얼로그 ─────────────────────────────────────────────────────
    '초기화 확인': 'Confirm Reset',
    '모든 입력 필드를 초기화하시겠습니까?': 'Reset all input fields?',

    # ── 보안 안내 ─────────────────────────────────────────────────────────────
    '보안 안내': 'Security Notice',
    '이 프로그램의 보안 동작 확인': 'View security behavior of this program',
    '이 프로그램의 보안 정책 안내입니다.': 'Security policy information for this program.',
    '외부 서버 통신 없음':
        'No external server communication',
    '모든 네트워크 연결은 사용자가 입력한 장비 IP로만 이루어집니다. 수집된 데이터는 외부로 전송되지 않습니다.':
        'All network connections are made only to device IPs entered by the user. Collected data is never transmitted externally.',
    '비밀번호 미저장':
        'Passwords never stored',
    '입력한 사용자명 · 비밀번호 · Enable 비밀번호는 실행 중 메모리에만 존재합니다. 파일, 레지스트리, 데이터베이스 어디에도 저장하지 않습니다.':
        'Username, Password, and Enable Password exist only in memory during execution. They are never written to files, registry, or databases.',
    'SSH 접속 시 호스트 키 자동 수락':
        'Auto-accept SSH host keys',
    'SSH로 처음 접속하는 장비의 신원(호스트 키)을 자동으로 수락합니다. 내부 관리망 전용 도구이므로 외부 인터넷 환경에서는 사용하지 마세요.':
        'Host keys of newly connected devices are accepted automatically. This tool is for internal management networks only — do not use on public internet.',
    '결과 파일 저장 경로':
        'Result file save path',
    '명령어 실행 결과는 사용자가 지정한 로컬 폴더에만 저장됩니다. 경로를 지정하지 않으면 파일이 생성되지 않습니다.':
        'Command output is saved only to the local folder specified by the user. No file is created if no path is set.',
    '사용 포트': 'Ports used',
    'SSH: TCP 22 (변경 가능)  ·  Telnet: TCP 23':
        'SSH: TCP 22 (configurable)  ·  Telnet: TCP 23',
    '빠른 체크는 위 포트의 연결 가능 여부만 확인합니다.':
        'Quick check only verifies reachability on the above ports.',
    '내부 관리 네트워크 전용 프로그램입니다.':
        'This program is intended for internal management networks only.',

    # ── SSH 로그 ──────────────────────────────────────────────────────────────
    'SSH 로그 보기': 'Show SSH Log',
    'SSH 로그 닫기': 'Hide SSH Log',
    'SSH 로그 뷰어': 'SSH Log Viewer',
    '로그 뷰어': 'Log Viewer',
    '=== 로그 세션 시작 ===': '=== Log Session Started ===',
    '크기 조절': 'Resize',
    '호스트: {worker.ip} - 로그 모니터링 시작': 'Host: {ip} - Log monitoring started',
    'SSH 로그 뷰어가 활성화되었습니다.': 'SSH log viewer is active.',

    # ── 시리얼 터미널 ─────────────────────────────────────────────────────────
    '연결 중...': 'Connecting...',
    '명령어 입력 후 Enter 또는 전송': 'Type command and press Enter or Send',
    '[오류] pyserial 라이브러리가 없습니다.': '[Error] pyserial library not found.',
    '포트 없음': 'No ports',
    '연결할 COM 포트를 선택해주세요.': 'Please select a COM port to connect.',
    '(포트 없음)': '(no ports)',

    # ── 네트워크 진단 탭 ──────────────────────────────────────────────────────
    'Ping · TCP 포트 연결 상태 확인': 'Ping & TCP Port Connectivity Check',
    'IP 목록': 'IP List',
    '인터벌 (초)': 'Interval (s)',
    '타임아웃 (초)': 'Timeout (s)',
    '호스트': 'Host',
    '포트 (쉼표 구분)': 'Ports (comma-separated)',
    '▶  시작': '▶  Start',
    '■  중지': '■  Stop',
    'Ping 결과': 'Ping Results',
    'TCPing 결과': 'TCPing Results',
    'IP 주소': 'IP Address',
    '상태': 'Status',
    '응답시간': 'Response',
    '평균': 'Average',
    '성공': 'Success',
    '마지막 확인': 'Last Check',
    '포트': 'Port',
    '● 응답': '● Alive',
    '● 실패': '● Failed',
    '● 대기': '● Waiting',

    # ── 정보 탭 ───────────────────────────────────────────────────────────────
    '버전': 'Version',
    '빌드': 'Build',
    '플랫폼': 'Platform',
    '활성화됨': 'Activated',
    '만료일': 'Expires',
    '기기 ID': 'Device ID',
    '무료 체험 중': 'Free Trial',
    '안내': 'Info',
    '30일 무료 체험판입니다. 체험 종료 후\n라이센스 발급은 이메일로 문의해주세요.':
        '30-day free trial. After the trial ends,\nplease contact us by email for a license.',
    '문의': 'Contact',
    '체험 만료': 'Trial Expired',
    '🔑 라이센스 활성화': '🔑 Activate License',
    '📋 이용약관': '📋 Terms of Service',
    '🌐 웹사이트': '🌐 Website',
    '버전 정보 · 라이센스': 'Version Info · License',

    # ── 홈 탭 ─────────────────────────────────────────────────────────────────
    'Cisco 네트워크 장비  자동화 · 분석 · 점검':
        'Cisco Network Device  Automation · Analysis · Inspection',
    'SSH / Telnet 다중 접속\n명령어 일괄 실행 및 설정 수집':
        'SSH / Telnet multi-device\nBulk execution & config backup',
    '로그 분석': 'Log Analysis',
    'Cisco Syslog 자동 파싱\n심각도 필터 · HTML 보고서 생성':
        'Cisco Syslog auto-parsing\nSeverity filter · HTML report',
    '점검 보고서': 'Inspection Report',
    'show 명령어 파일 자동 분석\nPDF / Word / Excel 보고서 생성':
        'Auto-analyze show command files\nPDF / Word / Excel reports',
    'Ping · TCPing 모니터링': 'Ping · TCPing monitoring',
    '진단': 'Diagnostics',
    '보고서 · 파일뷰어 · 로그분석': 'Reports · File viewer · Log analysis',
    '버전 · 라이센스': 'Version · License',
    '주요 기능': 'Key Features',
    '기타 기능': 'Other Features',
    '카드를 클릭하면 해당 기능으로 이동합니다': 'Click a card to navigate',
    '월': 'Mon', '화': 'Tue', '수': 'Wed', '목': 'Thu',
    '금': 'Fri', '토': 'Sat', '일': 'Sun',

    # ── 도구 탭 ───────────────────────────────────────────────────────────────
    '통합 도구 · 분석 · 보고서': 'Integrated Tools · Analysis · Reports',
    '설정 비교': 'Config Compare',
    '두 설정 변경사항 비교': 'Compare changes between two configs',
    '비교': 'Diff',
    '장비 점검 결과 PDF/Word/Excel': 'Device inspection PDF/Word/Excel',
    '점검': 'Inspect',
    'IOS-XE 보고서': 'IOS-XE Report',
    'Cisco IOS-XE 데이터 수집': 'Cisco IOS-XE data collection',
    'NX-OS 보고서': 'NX-OS Report',
    'Cisco Nexus 데이터 수집': 'Cisco Nexus data collection',
    'Cisco 로그 파일 파싱': 'Cisco log file parsing',
    '로그': 'Log',
    '파일 뷰어': 'File Viewer',
    'LOG · TXT 검색 · 구문 강조': 'LOG · TXT search · syntax highlight',
    '뷰어': 'Viewer',

    # ── 입력 검증 메시지 ──────────────────────────────────────────────────────
    'IP 리스트를 입력해주세요!': 'Please enter the IP list!',
    'COM 포트 리스트를 입력해주세요!': 'Please enter the COM port list!',
    '비밀번호를 입력해주세요!': 'Please enter the password!',
    '실행할 명령어를 입력해주세요!': 'Please enter commands to execute!',
    '저장 경로를 선택해주세요!': 'Please select a save path!',
    '폴더를 열 수 없습니다': 'Cannot open folder',
    '저장 경로를 생성할 수 없습니다': 'Cannot create save path',

    # ── 언어 변경 ─────────────────────────────────────────────────────────────
    '언어 변경': 'Language Changed',
    '언어가 변경되었습니다. 프로그램을 재시작하면 적용됩니다.':
        'Language changed. Please restart the program to apply.',
}


def set_language(lang: str):
    """'ko' 또는 'en' 설정 후 파일에 저장"""
    global _current_lang
    _current_lang = lang
    try:
        with open(_LANG_FILE, 'w', encoding='utf-8') as f:
            f.write(lang)
    except Exception:
        pass


def get_language() -> str:
    return _current_lang


def tr(text: str) -> str:
    """현재 언어에 따라 번역된 문자열 반환"""
    if _current_lang == 'en':
        return TRANSLATIONS.get(text, text)
    return text


def load_language():
    """저장된 언어 설정 불러오기"""
    global _current_lang
    try:
        if os.path.exists(_LANG_FILE):
            with open(_LANG_FILE, encoding='utf-8') as f:
                lang = f.read().strip()
            if lang in ('ko', 'en'):
                _current_lang = lang
    except Exception:
        pass


# 모듈 로드 시 자동으로 저장된 언어 적용
load_language()
