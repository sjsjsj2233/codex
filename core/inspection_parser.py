"""
Cisco 네트워크 장비 점검 파서 (IOS / IOS-XE / NX-OS)
show version / show proc cpu / show proc memory / show dir / show flash
show logging / show standby brief / show hsrp brief
show spanning-tree / show environment / show power
"""
import re
import os
from dataclasses import dataclass, field
from typing import List, Optional


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
class HsrpGroup:
    interface: str = ''
    group: str = ''
    priority: str = ''
    preempt: bool = False
    state: str = ''
    active_addr: str = ''
    standby_addr: str = ''
    virtual_ip: str = ''


@dataclass
class StpBlockedPort:
    interface: str = ''
    vlan: str = ''
    role: str = 'Altn'


@dataclass
class PowerSupply:
    slot: str = ''
    model: str = ''
    status: str = ''
    output: str = ''
    capacity: str = ''


@dataclass
class TempSensor:
    name: str = ''
    current: str = ''
    threshold: str = ''
    status: str = ''


@dataclass
class FanModule:
    name: str = ''
    status: str = ''
    model: str = ''


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
    # NX-OS show system resources의 load average (참고용)
    cpu_load_1m:  str = ''
    cpu_load_5m:  str = ''
    cpu_load_15m: str = ''

    mem_total: int = 0
    mem_used: int = 0
    mem_free: int = 0

    storages: List[StorageInfo] = field(default_factory=list)
    notable_logs: List[str] = field(default_factory=list)

    # 이중화
    hsrp_groups: List[HsrpGroup] = field(default_factory=list)

    # 스패닝트리
    stp_blocked_ports: List[StpBlockedPort] = field(default_factory=list)
    stp_mode: str = ''
    stp_root_vlans: List[str] = field(default_factory=list)

    # 환경 (온도 / 전원 / 팬)
    temp_sensors: List[TempSensor] = field(default_factory=list)
    power_supplies: List[PowerSupply] = field(default_factory=list)
    fans: List[FanModule] = field(default_factory=list)

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
    # NX-OS: Device name: DIST-NX-02
    m_nx = re.search(r'Device name\s*:\s*(\S+)', text, re.IGNORECASE)
    if m_nx and not dev.hostname:
        dev.hostname = m_nx.group(1)

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
        _SKIP_UPTIME_HOSTS = {'kernel', 'system', 'chassis'}
        m = re.search(r'([\w\-\.]+)\s+uptime\s+is\s+(.+)', text, re.IGNORECASE)
        if m and m.group(1).lower() not in _SKIP_UPTIME_HOSTS:
            if not dev.hostname:
                dev.hostname = m.group(1)
            dev.uptime = m.group(2).strip().rstrip('.')
        elif m:
            # NX-OS: "Kernel uptime is X day(s)..." → uptime만 추출
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


# ── show processes cpu (IOS/IOS-XE) ─────────────────────────────────────
def _parse_cpu(text: str, dev: DeviceInspection):
    # IOS/IOS-XE: CPU utilization for five seconds: 12%/6%; one minute: 8%; five minutes: 7%
    m = re.search(
        r'CPU\s+utilization.*?five\s+seconds\s*:\s*([\d\.]+)%.*?'
        r'one\s+minute\s*:\s*([\d\.]+)%.*?five\s+minutes\s*:\s*([\d\.]+)%',
        text, re.IGNORECASE | re.DOTALL
    )
    if m:
        dev.cpu_5sec = m.group(1) + '%'
        dev.cpu_1min = m.group(2) + '%'
        dev.cpu_5min = m.group(3) + '%'


# ── show system resources (NX-OS 전용) ──────────────────────────────────
def _parse_system_resources(text: str, dev: DeviceInspection):
    """
    NX-OS show system resources 출력 파싱
    Load average:    1 minute: 0.70 5 minutes: 0.89 15 minutes: 0.88
    CPU states  :  7.06% user,  5.49% kernel, 87.43% idle
    Memory usage: 16401700K total, 14525236K used, 1876464K free
    """
    # Load average → 1분/5분/15분을 1분/5분/5분(대체)으로 활용
    m = re.search(
        r'Load average\s*:\s*1\s*minute\s*:\s*([\d\.]+)\s*'
        r'5\s*minutes\s*:\s*([\d\.]+)\s*'
        r'15\s*minutes\s*:\s*([\d\.]+)',
        text, re.IGNORECASE
    )
    if m:
        # load average를 cpu 수치로 표현 (참고용, 정확한 % 아님)
        dev.cpu_load_1m  = m.group(1)
        dev.cpu_load_5m  = m.group(2)
        dev.cpu_load_15m = m.group(3)

    # CPU states: user% + kernel% = 전체 사용률
    m = re.search(
        r'CPU states\s*:\s*([\d\.]+)%\s*user,\s*([\d\.]+)%\s*kernel,\s*([\d\.]+)%\s*idle',
        text, re.IGNORECASE
    )
    if m and not dev.cpu_5sec:
        try:
            user   = float(m.group(1))
            kernel = float(m.group(2))
            total  = round(user + kernel, 1)
            dev.cpu_5sec = f'{total}%'
            dev.cpu_1min = f'{total}%'
            dev.cpu_5min = f'{total}%'
        except Exception:
            pass

    # Memory usage: 16401700K total, 14525236K used, 1876464K free
    m = re.search(
        r'Memory usage\s*:\s*(\d+)K\s+total,\s*(\d+)K\s+used,\s*(\d+)K\s+free',
        text, re.IGNORECASE
    )
    if m and not dev.mem_total:
        dev.mem_total = int(m.group(1)) * 1024
        dev.mem_used  = int(m.group(2)) * 1024
        dev.mem_free  = int(m.group(3)) * 1024


# ── show processes memory ─────────────────────────────────────────────────
def _parse_memory(text: str, dev: DeviceInspection):
    # IOS: Processor Pool  Total: NNNN  Used: NNNN  Free: NNNN
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
# 반복적 up/down 로그 제외 패턴
_LOG_NOISE_RE = re.compile(
    r'%LINK-\d-(?:CHANGED|UPDOWN)|%LINEPROTO-\d-UPDOWN'
    r'|%SYS-\d-LOGGINGHOST_STARTSTOP|%COUNTERS_|%SNMP_|%SYS-5-CONFIG_I'
    r'|%CDP-\d-|%SPANTREE-\d-PORT_STATE',
    re.IGNORECASE
)
# 유의미한 로그 (severity 0~4: emergency~warning, 일부 5도 포함)
_LOG_RE = re.compile(r'%[A-Z][A-Z0-9_]*(?:-[A-Z0-9_]+)*-[0-4]-\w+\s*:.*', re.IGNORECASE)

def _parse_logging(text: str, dev: DeviceInspection):
    found = _LOG_RE.findall(text)
    filtered = [l.strip()[:200] for l in found if not _LOG_NOISE_RE.search(l)]
    # 중복 제거 (같은 내용 반복 5회 이상이면 첫 1건만)
    seen: dict = {}
    deduped = []
    for log in filtered:
        key = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\b\d+\b', '#', log)[:80]
        seen[key] = seen.get(key, 0) + 1
        if seen[key] <= 2:  # 동일 유형 최대 2건만 허용
            deduped.append(log)
    dev.notable_logs = deduped[-50:]


# ── show standby brief / show hsrp brief ─────────────────────────────────
_HSRP_ROW_RE = re.compile(
    r'^\s*\*?\s*([\w/\.]+)\s+(\d+)\s+(\d+)\s*(P?)\s+'
    r'(Active|Standby|Init|Listen|Speak|Coup|Learn)\s+'
    r'(\S+)\s+(\S+)\s+(\S+)',
    re.IGNORECASE | re.MULTILINE
)

def _parse_hsrp(text: str, dev: DeviceInspection):
    for m in _HSRP_ROW_RE.finditer(text):
        grp = HsrpGroup(
            interface   = m.group(1),
            group       = m.group(2),
            priority    = m.group(3),
            preempt     = bool(m.group(4).strip()),
            state       = m.group(5),
            active_addr = m.group(6),
            standby_addr= m.group(7),
            virtual_ip  = m.group(8),
        )
        if not any(g.interface == grp.interface and g.group == grp.group
                   for g in dev.hsrp_groups):
            dev.hsrp_groups.append(grp)


# ── show spanning-tree ────────────────────────────────────────────────────
_STP_BLK_RE = re.compile(
    r'^\s*((?:Gi|Fa|Te|Hu|Et|Po|Vl|Gi\d|Fa\d|Te\d|Et\d)\S*)\s+'
    r'(?:Altn|Back|Desg|Root)\s+BLK',
    re.IGNORECASE | re.MULTILINE
)
_STP_MODE_RE = re.compile(r'Switch is in\s+([\w\-]+)\s+mode', re.IGNORECASE)
_STP_ROOT_RE = re.compile(r'Root bridge for:\s*(.+)', re.IGNORECASE)
_STP_BLOCKED_SUMMARY_RE = re.compile(
    r'^([\w\d\-]+)\s+([\w\d/,\s]+)$',
    re.MULTILINE
)

def _parse_stp(text: str, dev: DeviceInspection):
    if not dev.stp_mode:
        m = _STP_MODE_RE.search(text)
        if m:
            dev.stp_mode = m.group(1)

    for m in _STP_ROOT_RE.finditer(text):
        for vlan in re.split(r'[,\s]+', m.group(1)):
            vlan = vlan.strip()
            if vlan and vlan not in dev.stp_root_vlans:
                dev.stp_root_vlans.append(vlan)

    # BLK 포트 파싱 (show spanning-tree)
    for m in _STP_BLK_RE.finditer(text):
        port = m.group(1)
        # 어느 VLAN인지 앞 컨텍스트에서 찾기
        preceding = text[:m.start()]
        vlan_m = re.findall(r'(?:VLAN|vlan)(\d+)', preceding)
        vlan = vlan_m[-1] if vlan_m else '-'
        bp = StpBlockedPort(interface=port, vlan=vlan)
        if not any(b.interface == port and b.vlan == vlan for b in dev.stp_blocked_ports):
            dev.stp_blocked_ports.append(bp)

    # show spanning-tree blockedports 형식
    # VLAN0001   Gi0/3, Gi0/4
    in_blocked = 'Blocked Interfaces' in text
    if in_blocked:
        for line in text.splitlines():
            m2 = re.match(r'^(VLAN\d+|vlan\d+)\s+(.+)', line.strip(), re.IGNORECASE)
            if m2:
                vlan_id = re.sub(r'[^\d]', '', m2.group(1))
                for iface in re.split(r'[,\s]+', m2.group(2)):
                    iface = iface.strip()
                    if iface:
                        bp = StpBlockedPort(interface=iface, vlan=vlan_id)
                        if not any(b.interface == iface and b.vlan == vlan_id
                                   for b in dev.stp_blocked_ports):
                            dev.stp_blocked_ports.append(bp)


# ── show environment / show env all / show env power / show env temp ──────
def _parse_env(text: str, dev: DeviceInspection):
    # ── 온도 센서 ──────────────────────────────────────────────────
    # NX-OS 형식: Module  Sensor  MajorThresh  MinorThres  CurTemp  Status
    for m in re.finditer(
        r'^\s*(?:\d+\s+)?([\w/\(\)\s]+?)\s{2,}(\d+)\s+(\d+)\s+(\d+)\s+(Ok|OK|Minor|Major|critical\w*)',
        text, re.MULTILINE | re.IGNORECASE
    ):
        name  = m.group(1).strip()
        major = m.group(2)
        _     = m.group(3)
        cur   = m.group(4)
        st    = m.group(5)
        if any(k in name.lower() for k in ('inlet', 'outlet', 'temp', 'sensor', 'cpu', 'ambient')):
            ts = TempSensor(name=name, current=f'{cur}°C', threshold=f'{major}°C', status=st)
            if not any(t.name == ts.name for t in dev.temp_sensors):
                dev.temp_sensors.append(ts)

    # IOS 형식: Temp (Inlet/Outlet): 38C/42C  (Threshold 85C)
    for m in re.finditer(
        r'Temp\s*(?:\(([^)]+)\))?\s*:\s*([\d/]+)C.*?(?:Threshold\s+(\d+)C)?',
        text, re.IGNORECASE
    ):
        label = m.group(1) or 'System'
        vals  = m.group(2).split('/')
        thresh= m.group(3) or '-'
        for i, v in enumerate(vals):
            parts = label.split('/') if '/' in label else [label]
            nm = parts[i] if i < len(parts) else label
            ts = TempSensor(name=nm.strip(), current=f'{v}°C',
                            threshold=f'{thresh}°C' if thresh != '-' else '-',
                            status='Ok')
            if not any(t.name == ts.name for t in dev.temp_sensors):
                dev.temp_sensors.append(ts)

    # IOS 형식: Temperature Value: 38 Celsius, Temperature State: GREEN/YELLOW/RED
    for m in re.finditer(
        r'Temperature\s+Value\s*:\s*(\d+)\s+Celsius.*?Temperature\s+State\s*:\s*(\w+)',
        text, re.IGNORECASE | re.DOTALL
    ):
        raw = m.group(2).upper()
        if raw in ('GREEN', 'OK', 'NORMAL'):
            status = 'Ok'
        elif raw == 'YELLOW':
            status = 'Minor'   # 주의
        elif raw in ('RED', 'CRITICAL'):
            status = 'Major'   # 경고
        else:
            status = m.group(2)
        ts = TempSensor(name='System', current=f'{m.group(1)}°C', status=status)
        if not any(t.name == 'System' for t in dev.temp_sensors):
            dev.temp_sensors.append(ts)

    # 간단 형식: SYSTEM TEMPERATURE is OK / CRITICAL
    for m in re.finditer(r'(?:SYSTEM\s+)?TEMPERATURE\s+(?:is\s+)?(OK|CRITICAL|WARNING)', text, re.IGNORECASE):
        if not dev.temp_sensors:
            dev.temp_sensors.append(TempSensor(name='System', current='-', status=m.group(1)))

    # ── 전원 공급 ──────────────────────────────────────────────────
    # NX-OS: 1  N9K-PAC-1200W  600 W  1200 W  Ok
    for m in re.finditer(
        r'^\s*(\d+)\s+([\w\-]+(?:\s+[\w\-]+)?)\s+([\d\.]+ W)\s+([\d\.]+ W)\s+(Ok|OK|Absent|Shutdown|Fail\w*)',
        text, re.MULTILINE | re.IGNORECASE
    ):
        ps = PowerSupply(
            slot=m.group(1), model=m.group(2).strip(),
            output=m.group(3), capacity=m.group(4), status=m.group(5)
        )
        if not any(p.slot == ps.slot for p in dev.power_supplies):
            dev.power_supplies.append(ps)

    # IOS: Power Supply 0: Present, OK  /  Power Supply 1: Not Present
    for m in re.finditer(
        r'Power Supply\s+(\d+)\s*:\s*(.*?)(?:\n|$)',
        text, re.IGNORECASE
    ):
        raw_status = m.group(2).strip()
        status = 'Ok' if any(k in raw_status.lower() for k in ('ok', 'good', 'present')) and 'not' not in raw_status.lower() else raw_status
        ps = PowerSupply(slot=m.group(1), status=status)
        if not any(p.slot == ps.slot for p in dev.power_supplies):
            dev.power_supplies.append(ps)

    # ── 팬 ────────────────────────────────────────────────────────
    # NX-OS: Fan1(sys_fan1)  N9K-C9300-FAN2  1.0  Ok
    for m in re.finditer(
        r'^\s*(Fan\d+\S*)\s+([\w\-]+)\s+[\d\.]+\s+(Ok|OK|Fail\w*|absent)',
        text, re.MULTILINE | re.IGNORECASE
    ):
        fm = FanModule(name=m.group(1), model=m.group(2), status=m.group(3))
        if not any(f.name == fm.name for f in dev.fans):
            dev.fans.append(fm)

    # IOS: Fan 0: OK / FAN status: OK
    for m in re.finditer(r'Fan\s+(\d+)\s*:\s*(OK|FAIL\w*|ok|fail\w*)', text, re.IGNORECASE):
        fm = FanModule(name=f'Fan {m.group(1)}', status=m.group(2))
        if not any(f.name == fm.name for f in dev.fans):
            dev.fans.append(fm)


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

    if dev.notable_logs:
        cnt = len(dev.notable_logs)
        if cnt >= 20:
            issues.append(f'주요 경보 다수 감지: {cnt}건')
            worst = max(worst, 2)
        else:
            issues.append(f'주요 경보 감지: {cnt}건')
            worst = max(worst, 1)

    # HSRP 상태 점검
    for g in dev.hsrp_groups:
        if g.state.lower() not in ('active', 'standby'):
            issues.append(f'HSRP 비정상 상태: {g.interface} Grp{g.group} → {g.state}')
            worst = max(worst, 2)

    # STP 블락 포트
    if dev.stp_blocked_ports:
        cnt = len(dev.stp_blocked_ports)
        issues.append(f'STP 블락 포트 감지: {cnt}개 포트')
        worst = max(worst, 1)

    # 전원 이상
    for ps in dev.power_supplies:
        if any(k in ps.status.lower() for k in ('fail', 'absent', 'not present')):
            issues.append(f'전원 이상: PSU {ps.slot} → {ps.status}')
            worst = max(worst, 2)

    # 온도 이상
    for ts in dev.temp_sensors:
        if any(k in ts.status.lower() for k in ('minor', 'major', 'critical', 'warning')):
            issues.append(f'온도 경고: {ts.name} → {ts.current} ({ts.status})')
            worst = max(worst, 2 if 'major' in ts.status.lower() or 'critical' in ts.status.lower() else 1)

    # 팬 이상
    for fan in dev.fans:
        if 'fail' in fan.status.lower():
            issues.append(f'팬 이상: {fan.name} → {fan.status}')
            worst = max(worst, 2)

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
        if 'system resources' in cmd or 'system resource' in cmd:
            # NX-OS: show system resources → CPU + 메모리 통합
            _parse_system_resources(body, dev)
        elif 'cpu' in cmd:
            # IOS: show processes cpu
            _parse_cpu(body, dev)
        if 'memory' in cmd or 'mem' in cmd:
            _parse_memory(body, dev)
        if any(k in cmd for k in ('dir', 'flash', 'disk', 'bootflash')):
            _parse_storage(body, dev)
        if 'log' in cmd:
            _parse_logging(body, dev)
        if 'standby' in cmd or 'hsrp' in cmd:
            _parse_hsrp(body, dev)
        if 'spanning' in cmd or 'span' in cmd:
            _parse_stp(body, dev)
        if 'env' in cmd or 'power' in cmd or 'temperature' in cmd:
            _parse_env(body, dev)

    if 'raw' in sections:
        raw = sections['raw']
        _parse_version(raw, dev)
        _parse_system_resources(raw, dev)
        _parse_cpu(raw, dev)
        _parse_memory(raw, dev)
        _parse_storage(raw, dev)
        _parse_logging(raw, dev)
        _parse_hsrp(raw, dev)
        _parse_stp(raw, dev)
        _parse_env(raw, dev)

    if not dev.hostname:
        dev.hostname = os.path.splitext(os.path.basename(filepath))[0]

    _assess(dev)
    return dev


# ── 점검 명령어 목록 ──────────────────────────────────────────────────────
INSPECTION_COMMANDS_IOS = """\
! ===== Cisco IOS / IOS-XE 점검 명령어 =====
terminal length 0
show version
show processes cpu history
show processes cpu sorted
show processes memory sorted
show inventory
show environment all
show power
show redundancy
show standby brief
show spanning-tree summary
show spanning-tree blockedports
show ip route summary
show ip interface brief
show interfaces status
show cdp neighbors detail
show logging
dir flash:
dir bootflash:\
"""

INSPECTION_COMMANDS_NXOS = """\
! ===== Cisco NX-OS (Nexus) 점검 명령어 =====
terminal length 0
show version
show system resources
show processes cpu sort
show processes memory sort
show inventory
show environment
show environment power
show environment temperature
show redundancy status
show hsrp brief
show spanning-tree summary
show spanning-tree blockedports
show ip route summary
show ip interface brief
show interface status
show cdp neighbors detail
show logging last 200
dir bootflash:\
"""
