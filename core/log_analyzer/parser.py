import os
import re
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

from .constants import (
    SYSLOG_LEVELS, LOG_PATTERNS, SEVERITY_COLORS,
    NETWORK_EVENTS, SECURITY_EVENTS,
    NXOS_FACILITIES, IOS_FACILITIES,
)

# ──────────────────────────────────────────────────────────────
# 범용 Cisco syslog 앵커: %FACILITY-SEV-MNEMONIC:
# ──────────────────────────────────────────────────────────────
_CISCO_RE = re.compile(
    r'%([A-Z][A-Z0-9_]*(?:-[A-Z0-9_]+)*)-(\d)-([A-Z0-9_]+):\s*(.*)',
    re.IGNORECASE
)

# ASA 별도 패턴: %ASA-SEV-MSGID:
_ASA_RE = re.compile(
    r'%(?:ASA|FTD|PIX)-(\d)-(\w+):\s*(.*)',
    re.IGNORECASE
)

# syslog PRI 제거: <190>
_PRI_RE  = re.compile(r'^<\d+>')
# 시퀀스 번호 제거: "123: " 또는 "*123: "
_SEQ_RE  = re.compile(r'^\*?\d+:\s+')
# 선두 * 또는 . 제거
_STAR_RE = re.compile(r'^[*\.]\s*')

# 타임스탬프 패턴 목록 (앞부분 컨텍스트 파싱용)
_TS_FORMATS = [
    # NX-OS: 2026 Mar  1 00:00:00.123
    (re.compile(r'^(\d{4}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)'),
     ['%Y %b %d %H:%M:%S', '%Y %b  %d %H:%M:%S',
      '%Y %b %d %H:%M:%S.%f', '%Y %b  %d %H:%M:%S.%f']),
    # ISO: 2026-03-01T00:00:00.123+09:00
    (re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)'),
     ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']),
    # IOS 연도 포함: Mar  1 2026 00:00:00
    (re.compile(r'^(\w{3}\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)'),
     ['%b %d %Y %H:%M:%S', '%b  %d %Y %H:%M:%S',
      '%b %d %Y %H:%M:%S.%f', '%b  %d %Y %H:%M:%S.%f']),
    # IOS 기본: Mar  1 00:00:00
    (re.compile(r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)'),
     ['%b %d %H:%M:%S', '%b  %d %H:%M:%S',
      '%b %d %H:%M:%S.%f', '%b  %d %H:%M:%S.%f']),
    # uptime: 1d00h (타임스탬프 없음으로 처리)
]


class LogParserThread(QThread):
    """백그라운드 로그 파싱 스레드"""
    progress_update  = pyqtSignal(int)
    parsing_complete = pyqtSignal(list)
    error_occurred   = pyqtSignal(str)

    def __init__(self, file_path, device_type=None):
        super().__init__()
        self.file_path   = file_path
        self.device_type = device_type  # None 이면 자동 감지

    # ── 진입점 ──────────────────────────────────────────────────
    def run(self):
        try:
            if not os.path.exists(self.file_path):
                self.error_occurred.emit(f"파일을 찾을 수 없습니다: {self.file_path}")
                return
            if os.path.getsize(self.file_path) == 0:
                self.error_occurred.emit(f"빈 파일입니다: {self.file_path}")
                return

            self.progress_update.emit(5)
            content = self._read_file()
            if content is None:
                return

            # 장비 유형 자동 감지
            if not self.device_type:
                self.device_type = self._detect_device_type(content[:50000])

            logs = self._parse_content(content)
            self.progress_update.emit(100)
            self.parsing_complete.emit(logs)

        except Exception as e:
            self.error_occurred.emit(f"파싱 오류: {e}")

    # ── 파일 읽기 (인코딩 자동 감지) ────────────────────────────
    def _read_file(self):
        for enc in ('utf-8', 'euc-kr', 'cp949', 'latin-1'):
            try:
                with open(self.file_path, 'r', encoding=enc, errors='ignore') as f:
                    return f.read()
            except Exception:
                continue
        self.error_occurred.emit("파일 읽기 실패: 인코딩을 감지할 수 없습니다.")
        return None

    # ── 장비 유형 자동 감지 ──────────────────────────────────────
    def _detect_device_type(self, sample: str) -> str:
        """NX-OS / ASA / IOS-XE / IOS 순서로 판별"""
        # NX-OS: "2026 Mar  1 …" 또는 NX-OS 전용 Facility
        if re.search(r'\d{4}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}', sample):
            return 'nxos'
        if re.search(r'%(?:ETHPORT|VPC|VPCM|FEX|L2FM|URIB|NGOAM)-\d-', sample):
            return 'nxos'

        # ASA / FTD
        if re.search(r'%(?:ASA|FTD|PIX)-\d-\d+:', sample):
            return 'asa'

        # WLC
        if re.search(r'%(?:DOT11|CAPWAP|LWAPP|WLAN|APSTATEMACHINE)-\d-', sample):
            return 'wlc'

        # SD-WAN
        if re.search(r'%(?:SDWAN|VEDGE|OMP|BFD)-\d-', sample):
            return 'sdwan'

        # Router: BGP/OSPF/EIGRP/MPLS가 많으면 라우터
        router_score = len(re.findall(
            r'%(?:BGP|OSPF|EIGRP|MPLS|ISIS|RSVP|LDP|ISAKMP|IPSEC)-\d-', sample))
        switch_score = len(re.findall(
            r'%(?:LINEPROTO|SPANTREE|STP|SW_VLAN|CDP|LLDP|STACKMGR|DOT1X)-\d-', sample))

        if router_score > switch_score:
            return 'router'

        # 기본 IOS-XE
        return 'ios_xe'

    # ── 전체 파싱 ────────────────────────────────────────────────
    def _parse_content(self, content: str) -> list:
        lines = content.splitlines()
        total = max(len(lines), 1)
        logs  = []

        for i, line in enumerate(lines):
            if i % max(1, total // 20) == 0:
                self.progress_update.emit(min(95, 5 + int(i / total * 90)))

            entry = self._parse_line(line)
            if entry:
                logs.append(self._analyze(entry))

        return logs

    # ── 라인 파싱 (핵심) ─────────────────────────────────────────
    def _parse_line(self, line: str) -> dict | None:
        line = line.strip()
        if not line:
            return None

        # 1. syslog PRI 제거 <190>
        line = _PRI_RE.sub('', line).strip()

        # 2. 시퀀스 번호 제거 "000001: "
        line = _SEQ_RE.sub('', line).strip()

        # 3. 선두 * / . 제거
        line = _STAR_RE.sub('', line).strip()

        # 4. ASA 전용 패턴 시도
        if re.search(r'%(?:ASA|FTD|PIX)-\d-', line, re.IGNORECASE):
            return self._parse_asa_line(line)

        # 5. 범용 Cisco syslog 패턴으로 파싱
        m = _CISCO_RE.search(line)
        if not m:
            return None

        full_facility = m.group(1).upper()   # e.g. LINK, LINEPROTO, ETHPORT
        sev_digit     = int(m.group(2))
        mnemonic      = m.group(3).upper()
        message       = m.group(4).strip()
        severity      = SYSLOG_LEVELS.get(sev_digit, 'INFO')

        # 6. 타임스탬프 / 호스트명 추출 (% 앞 부분)
        prefix = line[:m.start()].strip().rstrip(':').strip()
        timestamp_str, hostname = self._split_prefix(prefix)
        timestamp_obj = self._parse_timestamp(timestamp_str) if timestamp_str else None

        return {
            'raw':           line,
            'timestamp':     timestamp_str or '',
            'timestamp_obj': timestamp_obj,
            'hostname':      hostname,
            'severity':      severity,
            'facility':      f'%{full_facility}-{sev_digit}-{mnemonic}',
            'facility_name': full_facility,
            'mnemonic':      mnemonic,
            'message':       message,
        }

    def _parse_asa_line(self, line: str) -> dict | None:
        m = _ASA_RE.search(line)
        if not m:
            return None

        sev_digit = int(m.group(1))
        mnemonic  = m.group(2).upper()
        message   = m.group(3).strip()
        severity  = SYSLOG_LEVELS.get(sev_digit, 'INFO')

        prefix = line[:m.start()].strip().rstrip(':').strip()
        timestamp_str, hostname = self._split_prefix(prefix)
        timestamp_obj = self._parse_timestamp(timestamp_str) if timestamp_str else None

        return {
            'raw':           line,
            'timestamp':     timestamp_str or '',
            'timestamp_obj': timestamp_obj,
            'hostname':      hostname,
            'severity':      severity,
            'facility':      f'%ASA-{sev_digit}-{mnemonic}',
            'facility_name': 'ASA',
            'mnemonic':      mnemonic,
            'message':       message,
        }

    # ── 타임스탬프 / 호스트명 분리 ──────────────────────────────
    def _split_prefix(self, prefix: str):
        """prefix에서 (timestamp_str, hostname) 추출"""
        if not prefix:
            return None, None

        for ts_re, _ in _TS_FORMATS:
            m = ts_re.match(prefix)
            if m:
                ts_str   = m.group(1).strip()
                rest     = prefix[m.end():].strip()
                # rest가 남아있으면 호스트명일 가능성
                hostname = rest.split()[0] if rest else None
                return ts_str, hostname

        # 타임스탬프를 찾지 못하면 전체를 호스트명으로 간주
        parts = prefix.split()
        return None, parts[0] if parts else None

    # ── 타임스탬프 파싱 ─────────────────────────────────────────
    def _parse_timestamp(self, ts_str: str) -> datetime | None:
        if not ts_str:
            return None
        ts_str = ts_str.strip()

        # ISO 8601 (timezone 포함)
        iso_m = re.match(
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)([+-]\d{2}:\d{2})?', ts_str)
        if iso_m:
            try:
                return datetime.fromisoformat(iso_m.group(1))
            except Exception:
                pass

        fmts = [
            '%Y %b %d %H:%M:%S',   '%Y %b  %d %H:%M:%S',
            '%Y %b %d %H:%M:%S.%f','%Y %b  %d %H:%M:%S.%f',
            '%b %d %Y %H:%M:%S',   '%b  %d %Y %H:%M:%S',
            '%b %d %Y %H:%M:%S.%f','%b  %d %Y %H:%M:%S.%f',
            '%b %d %H:%M:%S',      '%b  %d %H:%M:%S',
            '%b %d %H:%M:%S.%f',   '%b  %d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',   '%Y-%m-%dT%H:%M:%S.%f',
            '%b %d %Y: %H:%M:%S',
        ]
        year = datetime.now().year
        for fmt in fmts:
            try:
                dt = datetime.strptime(ts_str, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=year)
                return dt
            except ValueError:
                continue
        return None

    # ── 이벤트 분석 ──────────────────────────────────────────────
    def _analyze(self, entry: dict) -> dict:
        raw = entry.get('raw', '')

        for event_type, patterns in NETWORK_EVENTS.items():
            for p in patterns:
                if re.search(p, raw, re.IGNORECASE):
                    entry['event_type']     = event_type
                    entry['event_category'] = 'network'
                    return entry

        for event_type, patterns in SECURITY_EVENTS.items():
            for p in patterns:
                if re.search(p, raw, re.IGNORECASE):
                    entry['event_type']     = event_type
                    entry['event_category'] = 'security'
                    return entry

        return entry

    # ── 하위 호환성: 구버전 인터페이스 ──────────────────────────
    def parse_timestamp(self, timestamp_str):
        return self._parse_timestamp(timestamp_str)

    def detect_device_type(self, sample_content):
        return self._detect_device_type(sample_content)

    def analyze_log_entry(self, log_entry):
        return self._analyze(log_entry)

    # parse_normal_file / parse_large_file (UI 호환)
    def parse_normal_file(self):
        content = self._read_file()
        if content is None:
            return
        if not self.device_type:
            self.device_type = self._detect_device_type(content[:50000])
        logs = self._parse_content(content)
        self.progress_update.emit(100)
        self.parsing_complete.emit(logs)

    def parse_large_file(self):
        self.parse_normal_file()
