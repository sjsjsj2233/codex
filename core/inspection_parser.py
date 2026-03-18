"""
Cisco 네트워크 장비 점검 파서
show version / show proc cpu / show proc memory / show dir / show flash / show logging
을 하나의 파일 또는 여러 파일에서 파싱
"""
import re
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class StorageInfo:
    filesystem: str = ''
    total_bytes: int = 0
    free_bytes: int = 0

    @property
    def used_pct(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.total_bytes - self.free_bytes) / self.total_bytes * 100

    @property
    def total_mb(self) -> str:
        if self.total_bytes >= 1024 ** 3:
            return f"{self.total_bytes / 1024**3:.1f} GB"
        return f"{self.total_bytes / 1024**2:.1f} MB" if self.total_bytes else '-'

    @property
    def free_mb(self) -> str:
        if self.free_bytes >= 1024 ** 3:
            return f"{self.free_bytes / 1024**3:.1f} GB"
        return f"{self.free_bytes / 1024**2:.1f} MB" if self.free_bytes else '-'


@dataclass
class DeviceInspection:
    filename: str = ''
    hostname: str = ''
    platform: str = ''
    ios_version: str = ''
    serial: str = ''
    uptime: str = ''
    reload_reason: str = ''
    last_reload_time: str = ''

    cpu_5sec: str = ''
    cpu_1min: str = ''
    cpu_5min: str = ''

    mem_total: int = 0
    mem_used: int = 0
    mem_free: int = 0

    storages: List[StorageInfo] = field(default_factory=list)
    notable_logs: List[str] = field(default_factory=list)

    status: str = '정상'
    issues: List[str] = field(default_factory=list)

    @property
    def mem_pct(self) -> float:
        if self.mem_total == 0:
            return 0.0
        return self.mem_used / self.mem_total * 100

    @property
    def mem_total_mb(self) -> str:
        if self.mem_total >= 1024 ** 3:
            return f"{self.mem_total / 1024**3:.1f} GB"
        return f"{self.mem_total / 1024**2:.0f} MB" if self.mem_total else '-'

    @property
    def mem_free_mb(self) -> str:
        if self.mem_free >= 1024 ** 3:
            return f"{self.mem_free / 1024**3:.1f} GB"
        return f"{self.mem_free / 1024**2:.0f} MB" if self.mem_free else '-'


# ── 파일 읽기 ──────────────────────────────────────────────────────────────
def _read(path: str) -> str:
    for enc in ('utf-8', 'euc-kr', 'cp949', 'latin-1'):
        try:
            with open(path, 'r', encoding=enc, errors='ignore') as f:
                return f.read()
        except Exception:
            continue
    return ''


# ── 섹션 분리 ──────────────────────────────────────────────────────────────
_CMD_RE = re.compile(r'(?:^|\n)([\w\-\.]+)[>#]\s*(show\s+\S[^\n]*)', re.IGNORECASE)

def _split_sections(text: str) -> dict:
    sections = {}
    matches = list(_CMD_RE.finditer(text))
    if not matches:
        return {'raw': text}
    for i, m in enumerate(matches):
        cmd   = m.group(2).strip().lower()
        start = m.end()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[cmd] = text[start:end]
    return sections


# ── show version ──────────────────────────────────────────────────────────
def _parse_version(text: str, dev: DeviceInspection):
    if not dev.hostname:
        m = re.search(r'^([\w\-\.]+)[>#]', text, re.MULTILINE)
        if m:
            dev.hostname = m.group(1)
        m2 = re.search(r'^\s*hostname\s+(\S+)', text, re.MULTILINE | re.IGNORECASE)
        if m2:
            dev.hostname = m2.group(1)

    if not dev.ios_version:
        m = re.search(r'Cisco IOS(?:-XE)? Software.*?Version\s+([\d\w\.\(\)]+)', text, re.IGNORECASE)
        if m:
            dev.ios_version = m.group(1)
    if not dev.ios_version:
        m = re.search(r'(?:NXOS|system):\s*version\s+([\d\w\.\(\)]+)', text, re.IGNORECASE)
        if m:
            dev.ios_version = m.group(1)
    if not dev.ios_version:
        m = re.search(r'\bVersion\s+([\d\w\.\(\)]+)', text, re.IGNORECASE)
        if m:
            dev.ios_version = m.group(1)

    if not dev.platform:
        m = re.search(r'(Cisco\s+(?:Catalyst|Nexus|ASA|ISR|ASR|CSR|CBS|Firepower)\s*[\w\-]+)', text, re.IGNORECASE)
        if m:
            dev.platform = m.group(1).strip()
    if not dev.platform:
        m = re.search(r'(?:Hardware|cisco)\s+([\w\-]+ Series)', text, re.IGNORECASE)
        if m:
            dev.platform = m.group(1).strip()

    if not dev.uptime:
        m = re.search(r'([\w\-\.]+)\s+uptime\s+is\s+(.+)', text, re.IGNORECASE)
        if m:
            if not dev.hostname:
                dev.hostname = m.group(1)
            dev.uptime = m.group(2).strip().rstrip('.')

    if not dev.reload_reason:
        m = re.search(r'(?:System returned to ROM by|Last reload reason)\s*[:\-]?\s*(.+)', text, re.IGNORECASE)
        if m:
            dev.reload_reason = m.group(1).strip()

    if not dev.last_reload_time:
        m = re.search(r'at\s+(\d{2}:\d{2}:\d{2}\s+\w+\s+\w+\s+\w+\s+\d+\s+\d{4})', text, re.IGNORECASE)
        if m:
            dev.last_reload_time = m.group(1).strip()

    if not dev.serial:
        m = re.search(r'(?:Processor board ID|System Serial Number)\s+(\S+)', text, re.IGNORECASE)
        if m:
            dev.serial = m.group(1)


# ── show processes cpu ────────────────────────────────────────────────────
def _parse_cpu(text: str, dev: DeviceInspection):
    m = re.search(
        r'CPU\s+utilization.*?five\s+seconds\s*:\s*([\d\.]+)%.*?'
        r'one\s+minute\s*:\s*([\d\.]+)%.*?five\s+minutes\s*:\s*([\d\.]+)%',
        text, re.IGNORECASE | re.DOTALL
    )
    if m:
        dev.cpu_5sec = m.group(1) + '%'
        dev.cpu_1min = m.group(2) + '%'
        dev.cpu_5min = m.group(3) + '%'
        return
    m = re.search(r'CPU states\s*:\s*([\d\.]+)%\s*user.*?([\d\.]+)%\s*kernel', text, re.IGNORECASE | re.DOTALL)
    if m:
        try:
            total = float(m.group(1)) + float(m.group(2))
            s = f'{total:.1f}%'
            dev.cpu_5sec = dev.cpu_1min = dev.cpu_5min = s
        except Exception:
            pass


# ── show processes memory ─────────────────────────────────────────────────
def _parse_memory(text: str, dev: DeviceInspection):
    m = re.search(r'Processor Pool\s+Total:\s*(\d+)\s+Used:\s*(\d+)\s+Free:\s*(\d+)', text, re.IGNORECASE)
    if m:
        dev.mem_total = int(m.group(1))
        dev.mem_used  = int(m.group(2))
        dev.mem_free  = int(m.group(3))
        return
    m = re.search(r'Total:\s*(\d+)\s+Used:\s*(\d+)\s+Free:\s*(\d+)', text, re.IGNORECASE)
    if m:
        dev.mem_total = int(m.group(1))
        dev.mem_used  = int(m.group(2))
        dev.mem_free  = int(m.group(3))
        return
    m = re.search(r'(\d+)K\s+total,\s*(\d+)K\s+used,\s*(\d+)K\s+free', text, re.IGNORECASE)
    if m:
        dev.mem_total = int(m.group(1)) * 1024
        dev.mem_used  = int(m.group(2)) * 1024
        dev.mem_free  = int(m.group(3)) * 1024


# ── show dir / show flash ─────────────────────────────────────────────────
def _parse_storage(text: str, dev: DeviceInspection):
    for m in re.finditer(r'([\d,]+)\s+bytes\s+total\s+\(([\d,]+)\s+bytes\s+free\)', text, re.IGNORECASE):
        total = int(m.group(1).replace(',', ''))
        free  = int(m.group(2).replace(',', ''))
        preceding = text[:m.start()]
        fs_list = re.findall(r'Directory of\s+([\w/:\.\-]+)', preceding, re.IGNORECASE)
        fs = fs_list[-1] if fs_list else ''
        si = StorageInfo(filesystem=fs, total_bytes=total, free_bytes=free)
        if not any(s.filesystem == si.filesystem and s.total_bytes == si.total_bytes for s in dev.storages):
            dev.storages.append(si)


# ── show logging ──────────────────────────────────────────────────────────
_LOG_RE = re.compile(r'%[A-Z][A-Z0-9_]*(?:-[A-Z0-9_]+)*-[0-4]-\w+\s*:.*', re.IGNORECASE)

def _parse_logging(text: str, dev: DeviceInspection):
    found = _LOG_RE.findall(text)
    dev.notable_logs = [l.strip()[:200] for l in found[-30:]]


# ── 상태 평가 ─────────────────────────────────────────────────────────────
def _assess(dev: DeviceInspection):
    issues = []
    worst  = 0

    for label, val in [('5초', dev.cpu_5sec), ('1분', dev.cpu_1min), ('5분', dev.cpu_5min)]:
        if val:
            try:
                pct = float(val.rstrip('%'))
                if pct >= 80:
                    issues.append(f'CPU {label} 사용률 높음: {val}')
                    worst = max(worst, 2)
                elif pct >= 60:
                    issues.append(f'CPU {label} 사용률 주의: {val}')
                    worst = max(worst, 1)
            except ValueError:
                pass

    if dev.mem_total > 0:
        if dev.mem_pct >= 85:
            issues.append(f'메모리 사용률 높음: {dev.mem_pct:.1f}%')
            worst = max(worst, 2)
        elif dev.mem_pct >= 70:
            issues.append(f'메모리 사용률 주의: {dev.mem_pct:.1f}%')
            worst = max(worst, 1)

    for s in dev.storages:
        if s.used_pct >= 85:
            issues.append(f'스토리지 {s.filesystem} 사용률 높음: {s.used_pct:.1f}%')
            worst = max(worst, 2)
        elif s.used_pct >= 70:
            issues.append(f'스토리지 {s.filesystem} 사용률 주의: {s.used_pct:.1f}%')
            worst = max(worst, 1)

    if len(dev.notable_logs) >= 20:
        issues.append(f'주요 경보 다수 감지: {len(dev.notable_logs)}건')
        worst = max(worst, 2)
    elif dev.notable_logs:
        issues.append(f'주요 경보 감지: {len(dev.notable_logs)}건')
        worst = max(worst, 1)

    if not issues:
        issues.append('이상 없음')

    dev.issues = issues
    dev.status  = ['정상', '주의', '경고'][worst]


# ── 공개 API ──────────────────────────────────────────────────────────────
def parse_file(filepath: str) -> DeviceInspection:
    dev  = DeviceInspection(filename=os.path.basename(filepath))
    text = _read(filepath)
    if not text:
        dev.status = '파일 오류'
        dev.issues = ['파일을 읽을 수 없습니다']
        return dev

    sections = _split_sections(text)

    for cmd, body in sections.items():
        if 'version' in cmd:
            _parse_version(body, dev)
        if 'cpu' in cmd:
            _parse_cpu(body, dev)
        if 'memory' in cmd or 'mem' in cmd:
            _parse_memory(body, dev)
        if any(k in cmd for k in ('dir', 'flash', 'disk', 'bootflash')):
            _parse_storage(body, dev)
        if 'log' in cmd:
            _parse_logging(body, dev)

    if 'raw' in sections:
        raw = sections['raw']
        _parse_version(raw, dev)
        _parse_cpu(raw, dev)
        _parse_memory(raw, dev)
        _parse_storage(raw, dev)
        _parse_logging(raw, dev)

    if not dev.hostname:
        dev.hostname = os.path.splitext(os.path.basename(filepath))[0]

    _assess(dev)
    return dev
