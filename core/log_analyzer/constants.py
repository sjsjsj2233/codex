from PyQt5.QtGui import QColor

# ──────────────────────────────────────────────────────────────
# Syslog 심각도 레벨
# ──────────────────────────────────────────────────────────────
SYSLOG_LEVELS = {
    0: "EMERGENCY",
    1: "ALERT",
    2: "CRITICAL",
    3: "ERROR",
    4: "WARNING",
    5: "NOTICE",
    6: "INFO",
    7: "DEBUG"
}

# ──────────────────────────────────────────────────────────────
# 범용 Cisco Syslog 앵커 패턴
# 모든 Cisco 장비는 %FACILITY-SEV-MNEMONIC: 형식을 공유
# ──────────────────────────────────────────────────────────────
# 이 패턴을 라인에서 찾은 뒤, 앞부분에서 타임스탬프/호스트명을 추출
CISCO_MSG_RE = r'%([A-Z0-9_]+-(?:[A-Z0-9_]+-)*\d-[A-Z0-9_]+):\s*(.*)'

# NX-OS는 %FACILITY-SEV-MNEMONIC 구조가 약간 다를 수 있음
NXOS_MSG_RE  = r'%([A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)'

# ──────────────────────────────────────────────────────────────
# 장비 유형별 로그 패턴 (device_type 자동 감지용)
# 실제 현장 포맷 기반으로 재작성
# ──────────────────────────────────────────────────────────────
LOG_PATTERNS = {
    # IOS / IOS-XE (Catalyst Switch, ISR Router 공통)
    # *Mar  1 00:00:00.123: %LINK-3-UPDOWN: ...
    # 000001: Mar  1 00:00:00.123: %SYS-5-CONFIG_I: ...
    # Mar  1 2026 00:00:00 KST: %OSPF-5-ADJCHG: ...
    'ios_xe': [
        r'(?:\d+:\s+)?(?:\*|\.)?(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*:\s*(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(?:\d+:\s+)?(?:\*|\.)?(\w{3}\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\s+\w+)?)\s*:\s*(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',   # 타임스탬프 없는 경우
    ],
    'ios': [
        r'(?:\d+:\s+)?(?:\*|\.)?(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*:\s*(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
    ],
    # NX-OS (Nexus 5K/7K/9K)
    # 2026 Mar  1 00:00:00.123 N9K-1 %ETHPORT-5-IF_UP: ...
    # 2026-03-01T00:00:00.123+09:00 N9K-1 %STP-2-BLOCK_PVID_PEER: ...
    'nxos': [
        r'(\d{4}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(\S+)\s+(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\s+(\S+)\s+(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
    ],
    # ASA / FTD
    # Jan  1 2026 00:00:00: %ASA-6-302013: Built inbound TCP ...
    # %ASA-5-111010: User 'enable_1' ...
    'asa': [
        r'(\w{3}\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2})\s*:\s*%ASA-(\d)-(\w+):\s*(.*)',
        r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s*:\s*%ASA-(\d)-(\w+):\s*(.*)',
        r'%ASA-(\d)-(\w+):\s*(.*)',
        r'%FTD-(\d)-(\w+):\s*(.*)',
    ],
    # Router (ISR/ASR)
    'router': [
        r'(?:\d+:\s+)?(?:\*|\.)?(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*:\s*(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(?:\d+:\s+)?(?:\*|\.)?(\w{3}\s+\d{1,2}\s+\d{4}\s+\d{2}:\d{2}:\d{2})\s*:\s*(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
    ],
    # WLC (Catalyst 9800)
    'wlc': [
        r'(?:\*|\.)?(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*:\s*(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
        r'(%[A-Z0-9_]+-\d-[A-Z0-9_]+):\s*(.*)',
    ],
    # SD-WAN (Viptela/IOS-XE SD-WAN)
    'sdwan': [
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\s+(\S+)\s+(\S+):\s+(.*)',
        r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+):\s+(.*)',
    ],
}

# ──────────────────────────────────────────────────────────────
# 장비 시리즈 → OS 매핑
# ──────────────────────────────────────────────────────────────
SERIES_TO_OS = {
    # Catalyst Switch (IOS)
    '2960': 'ios', '2960x': 'ios', '2960s': 'ios',
    '3560': 'ios', '3750': 'ios', '3750x': 'ios',
    # Catalyst Switch (IOS-XE)
    '3650': 'ios_xe', '3850': 'ios_xe',
    '9200': 'ios_xe', '9300': 'ios_xe',
    '9400': 'ios_xe', '9500': 'ios_xe',
    # Nexus (NX-OS)
    '2000': 'nxos', '5000': 'nxos', '5500': 'nxos', '5600': 'nxos',
    '6000': 'nxos', '7000': 'nxos', '7700': 'nxos',
    '9000': 'nxos', '9200nx': 'nxos', '9300nx': 'nxos',
    '9500nx': 'nxos', '93180': 'nxos', '93240': 'nxos',
    '9504': 'nxos', '9508': 'nxos', '9516': 'nxos',
    # Router (IOS-XE)
    '1100': 'router', '1900': 'router',
    '4000': 'router', '4300': 'router', '4400': 'router',
    'asr1000': 'router', 'asr1001': 'router', 'asr1002': 'router',
    'asr9000': 'router', 'asr9001': 'router',
    'isr4321': 'router', 'isr4331': 'router',
    'isr4351': 'router', 'isr4431': 'router',
    # ASA/FTD
    'asa': 'asa', 'ftd': 'asa', 'firepower': 'asa',
    # WLC
    '9800': 'wlc', '5520': 'wlc', '8540': 'wlc',
    # SD-WAN
    'viptela': 'sdwan', 'vmanage': 'sdwan',
    'vedge': 'sdwan', 'vsmart': 'sdwan',
}

# ──────────────────────────────────────────────────────────────
# NX-OS 특유 Facility 코드 (장비 감지용)
# ──────────────────────────────────────────────────────────────
NXOS_FACILITIES = {
    'ETHPORT', 'ETH_PORT_CHANNEL', 'VPC', 'VPCM',
    'PLATFORM', 'MODULE', 'SYSMGR', 'KERN',
    'FEX', 'URIB', 'L2FM', 'VSHD',
    'NGOAM', 'IPQOS', 'COPP',
}

# IOS/IOS-XE 특유 Facility 코드
IOS_FACILITIES = {
    'LINEPROTO', 'SPANTREE', 'CDP', 'LLDP',
    'SW_VLAN', 'SYS', 'STBY', 'HSRP',
    'STACKMGR', 'SWITCH_QOS_TB',
}

# ──────────────────────────────────────────────────────────────
# 심각도 색상
# ──────────────────────────────────────────────────────────────
SEVERITY_COLORS = {
    'EMERGENCY': QColor(180, 0,   0),
    'ALERT':     QColor(200, 0,   0),
    'CRITICAL':  QColor(220, 0,   0),
    'ERROR':     QColor(255, 0,   0),
    'WARNING':   QColor(255, 140, 0),
    'NOTICE':    QColor(180, 130, 0),
    'INFO':      QColor(0,   0,   0),
    'DEBUG':     QColor(128, 128, 128),
}

# ──────────────────────────────────────────────────────────────
# 네트워크 이벤트 패턴
# ──────────────────────────────────────────────────────────────
NETWORK_EVENTS = {
    'interface_down': [
        r'%LINK-\d-UPDOWN.*changed state to down',
        r'%LINEPROTO-\d-UPDOWN.*changed state to down',
        r'%ETHPORT-\d-IF_DOWN',
        r'%ETHPORT-\d-IF_RX_FLOW_CONTROL',
        r'Interface \S+.*down',
        r'changed state to down',
    ],
    'interface_up': [
        r'%LINK-\d-UPDOWN.*changed state to up',
        r'%LINEPROTO-\d-UPDOWN.*changed state to up',
        r'%ETHPORT-\d-IF_UP',
        r'Interface \S+.*up',
        r'changed state to up',
    ],
    'spanning_tree': [
        r'%SPANTREE-',
        r'%STP-',
        r'spanning.tree',
        r'BLOCK_PVID',
        r'TOPO_CHANGE',
        r'ROOT_CHANGE',
        r'TCN',
    ],
    'bgp_neighbor': [
        r'%BGP-\d-ADJCHANGE',
        r'%BGP-\d-NOTIFICATION',
        r'BGP.*neighbor.*[Uu]p',
        r'BGP.*neighbor.*[Dd]own',
        r'BGP.*[Ss]ession.*[Ee]stablished',
        r'BGP.*[Ss]ession.*[Rr]eset',
    ],
    'ospf_neighbor': [
        r'%OSPF-\d-ADJCHG',
        r'%OSPF-\d-NEIGHBORCHG',
        r'OSPF.*neighbor.*[Uu]p',
        r'OSPF.*neighbor.*[Dd]own',
        r'OSPF.*state.*Full',
    ],
    'eigrp_neighbor': [
        r'%DUAL-\d-NBRCHANGE',
        r'EIGRP.*neighbor.*[Uu]p',
        r'EIGRP.*neighbor.*[Dd]own',
    ],
    'vpc': [
        r'%VPC-',
        r'%VPCM-',
        r'vPC.*[Oo]nline',
        r'vPC.*[Oo]ffline',
        r'peer-link',
        r'keepalive',
    ],
    'port_channel': [
        r'%ETH_PORT_CHANNEL-',
        r'%PAGP-',
        r'%LACP-',
        r'Port-channel.*[Uu]p',
        r'Port-channel.*[Dd]own',
        r'channel.*misconfig',
    ],
    'reload': [
        r'%SYS-\d-RELOAD',
        r'%SYSMGR-\d-REBOOT',
        r'Reload requested',
        r'System restarting',
        r'reloading',
    ],
    'config_change': [
        r'%SYS-\d-CONFIG_I',
        r'%SYS-\d-CONFIG_P',
        r'%VSHD-\d-VSHD_SYSLOG_CONFIG_I',
        r'Configured from',
    ],
    'high_cpu': [
        r'%SYS-\d-CPUHOG',
        r'%PLATFORM-\d-PFM_ALERT',
        r'CPU utilization.*\d{2,3}%',
        r'CPU.*high',
    ],
    'high_memory': [
        r'%SYS-\d-NOMEMORY',
        r'Memory.*threshold',
        r'memory.*low',
        r'out of memory',
    ],
    'power': [
        r'%PLATFORM-\d-POWER',
        r'%POWER-\d-',
        r'%C\d+-\d-POWER',
        r'power supply.*fail',
        r'PSU.*fail',
    ],
    'fan': [
        r'%PLATFORM-\d-FAN',
        r'%ENVIRONMENTAL-\d-FAN',
        r'%C\d+-\d-FAN',
        r'fan.*fail',
        r'cooling.*fail',
    ],
    'temperature': [
        r'%PLATFORM-\d-TEMP',
        r'%ENVIRONMENTAL-\d-TEMP',
        r'%C\d+-\d-TEMP',
        r'temperature.*exceed',
        r'thermal.*shut',
    ],
    'module': [
        r'%MODULE-\d-MOD_OK',
        r'%MODULE-\d-MOD_FAIL',
        r'%MODULE-\d-MOD_REMOVED',
        r'%MODULE-\d-MOD_INSERTED',
        r'Module \d.*online',
        r'Module \d.*fail',
    ],
    'fex': [
        r'%FEX-\d-',
        r'FEX.*online',
        r'FEX.*offline',
    ],
    'stack': [
        r'%STACK-\d-',
        r'%STACKMGR-\d-',
        r'Stack Port \d change',
        r'switch.*master',
    ],
    'ntp': [
        r'%NTP-\d-',
        r'NTP.*sync',
        r'clock.*synchronized',
        r'stratum',
    ],
}

# ──────────────────────────────────────────────────────────────
# 보안 이벤트 패턴
# ──────────────────────────────────────────────────────────────
SECURITY_EVENTS = {
    'acl_violation': [
        r'%SEC-\d-IPACCESSLOG',
        r'%ACLLOG-\d-DENY',
        r'%PIX-\d-106',
        r'%ASA-\d-106',
        r'access-list.*denied',
        r'ACL.*drop',
        r'IPACCESSLOG',
    ],
    'auth_failure': [
        r'%SEC-\d-LOGIN_FAILED',
        r'%AAA-\d-ACCT_STOP',
        r'Authentication failed',
        r'Login failed',
        r'Bad password',
        r'invalid password',
        r'%AUTHMGR-\d-FAIL',
    ],
    'login_success': [
        r'%SEC-\d-LOGIN_SUCCESS',
        r'%AUTHMGR-\d-SUCCESS',
        r'User.*logged in',
        r'SSH.*Accepted',
        r'login.*success',
    ],
    'ssh_event': [
        r'%SSH-\d-',
        r'SSH2.*from',
        r'SSH.*connection',
        r'sshd.*Accepted',
        r'sshd.*Failed',
    ],
    'dot1x': [
        r'%DOT1X-\d-',
        r'%AUTHMGR-\d-',
        r'802\.1X.*authenticated',
        r'802\.1X.*failed',
        r'MAB.*success',
        r'MAB.*fail',
    ],
    'port_security': [
        r'%PORT_SECURITY-\d-',
        r'%PSECURE-\d-',
        r'port security.*violation',
        r'MAC.*violation',
        r'secure.*violation',
    ],
    'dhcp_snooping': [
        r'%DHCP_SNOOPING-\d-',
        r'%DHCP-\d-SNOOPING',
        r'DHCP.*snooping.*drop',
        r'snooping.*violation',
    ],
    'arp_inspection': [
        r'%ARP_INSPECTION-\d-',
        r'%ARPINSPECT-\d-',
        r'ARP.*inspection.*drop',
        r'invalid ARP',
    ],
    'storm_control': [
        r'%STORM_CONTROL-\d-',
        r'storm.*control',
        r'traffic.*suppressed',
        r'broadcast.*storm',
    ],
    'crypto': [
        r'%CRYPTO-\d-',
        r'%PKI-\d-',
        r'certificate.*expire',
        r'IKE.*fail',
    ],
    'ipsec': [
        r'%IPSEC-\d-',
        r'%ISAKMP-\d-',
        r'IPSec.*SA.*deleted',
        r'tunnel.*down',
    ],
    'firewall': [
        r'%ASA-\d-\d{6}',
        r'%FTD-\d-\d{6}',
        r'Teardown.*connection',
        r'Built.*connection',
        r'Deny.*by ACL',
    ],
    'copp': [
        r'%COPP-\d-',
        r'CoPP.*drop',
        r'rate-limit.*exceed',
    ],
}
