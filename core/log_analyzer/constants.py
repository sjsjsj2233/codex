from PyQt5.QtGui import QColor



SYSLOG_LEVELS = {
    0: "EMERGENCY",  # 시스템 사용 불가
    1: "ALERT",      # 즉시 조치 필요
    2: "CRITICAL",   # 중대한 상태
    3: "ERROR",      # 오류 상태
    4: "WARNING",    # 경고 상태
    5: "NOTICE",     # 정상이지만 중요한 상태
    6: "INFO",       # 정보성 메시지
    7: "DEBUG"       # 디버그 메시지
}

# 다양한 Cisco 장비 시리즈의 로그 형식에 대한 정규식 패턴 정의
# 더 현실적이고 다양한 로그 패턴 지원
LOG_PATTERNS = {
    # IOS XE 패턴 (3650, 3850, 9200, 9300, 9400, 9500)
    'ios_xe': [
        # 표준 syslog 포맷
        r'(\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?)\s+(\w+):?\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)',
        # 타임스탬프가 있는 포맷
        r'(\*?\w+\s+\d+\s+\d{4}(?::\s+|\s+)\d+:\d+:\d+(?:\.\d+)?):?\s+(\w+):?\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)',
        # 호스트명이 포함된 포맷
        r'(\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?)\s+(\S+)\s+(\w+):?\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)'
    ],
    
    # IOS 패턴 (2960X, 3560, 3750)
    'ios': [
        # 기본 IOS 로그 포맷
        r'(\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?):?\s+(\w+):?\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)',
        # 날짜 포함 포맷
        r'(\*?\w+\s+\d+\s+\d{4}(?::\s+|\s+)\d+:\d+:\d+(?:\.\d+)?):?\s+(\w+):?\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)'
    ],
    
    # NX-OS 패턴 (93180, 9504, 9300)
    'nxos': [
        # 표준 NX-OS 로그 포맷
        r'(\d{4}\s+\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?)\s+(\w+):\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)',
        # 다른 NX-OS 시간 포맷
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\s+(\w+):\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)'
    ],
    
    # ASA/FTD 패턴 (ASA, Firepower)
    'asa': [
        # ASA 포맷
        r'(\w+\s+\d+\s+\d{4}\s+\d+:\d+:\d+):\s+%ASA-(\d)-(\w+):\s+(.*)',
        # 심각도 레벨이 포함된 포맷
        r'(\w+\s+\d+\s+\d+:\d+:\d+):\s+%ASA-(\d)-(\w+):\s+(.*)'
    ],
    
    # ISR/ASR 라우터 패턴
    'router': [
        # 표준 IOS 라우터 로그
        r'(\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?):\s+%(\w+)-(\d)-(\w+):\s+(.*)',
        # 호스트명 포함 포맷
        r'(\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?)\s+(\S+):\s+%(\w+)-(\d)-(\w+):\s+(.*)'
    ],
    
    # 무선 컨트롤러 패턴 (9800 WLC)
    'wlc': [
        # 9800 WLC 로그 포맷
        r'(\w+\s+\d+\s+\d+:\d+:\d+(?:\.\d+)?)\s+(\w+):\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)',
        # WLC 특수 포맷
        r'(\*?\w+\s+\d+\s+\d{4}(?::\s+|\s+)\d+:\d+:\d+(?:\.\d+)?)\s+(\w+):\s+(%(?:\w+[-_])+\d-(?:\w+[-_])+):\s+(.*)'
    ],
    
    # SD-WAN (Viptela) 패턴
    'sdwan': [
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\s+(\w+)\s+(\w+):\s+(.*)',
        r'(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\w+)\s+(\w+):\s+(.*)'
    ]
}

# 시리즈별 OS 유형 매핑 (확장됨)
SERIES_TO_OS = {
    # Catalyst 스위치
    '2960': 'ios',
    '2960x': 'ios',
    '3560': 'ios',
    '3650': 'ios_xe',
    '3750': 'ios',
    '3850': 'ios_xe',
    '9200': 'ios_xe',
    '9300': 'ios_xe',
    '9400': 'ios_xe',
    '9500': 'ios_xe',
    
    # 무선
    '9800': 'wlc',
    '5520': 'wlc',
    '8540': 'wlc',
    
    # NX-OS
    '93180': 'nxos',
    '9504': 'nxos',
    '9300nx': 'nxos',
    '9500nx': 'nxos',
    '7000': 'nxos',
    '5000': 'nxos',
    
    # 라우터
    '4000': 'router',
    '4300': 'router',
    '4400': 'router',
    'asr1000': 'router',
    'asr9000': 'router',
    
    # 보안
    'asa': 'asa',
    'ftd': 'asa',
    'firepower': 'asa',
    
    # SD-WAN
    'viptela': 'sdwan',
    'vmanage': 'sdwan',
    'vedge': 'sdwan'
}

# 로그 심각도에 따른 색상 정의
SEVERITY_COLORS = {
    'EMERGENCY': QColor(255, 0, 0),       # 빨강
    'ALERT': QColor(255, 0, 0),           # 빨강
    'CRITICAL': QColor(255, 0, 0),        # 빨강
    'ERROR': QColor(255, 0, 0),           # 빨강
    'WARNING': QColor(255, 165, 0),       # 주황색
    'NOTICE': QColor(255, 255, 0),        # 노랑
    'INFO': QColor(0, 0, 0),              # 검정 (기본)
    'DEBUG': QColor(128, 128, 128)        # 회색
}

# 주요 네트워크 이벤트 정의
NETWORK_EVENTS = {
    'interface_down': [
        r'.*Interface (\S+), changed state to down',
        r'.*Interface (\S+).*down',
        r'.*%LINK-\d-DOWN: Interface (\S+), changed state to down',
        r'.*%LINEPROTO-\d-DOWN: Line protocol on Interface (\S+), changed state to down'
    ],
    'interface_up': [
        r'.*Interface (\S+), changed state to up',
        r'.*Interface (\S+).*up',
        r'.*%LINK-\d-UP: Interface (\S+), changed state to up',
        r'.*%LINEPROTO-\d-UP: Line protocol on Interface (\S+), changed state to up'
    ],
    'spanning_tree': [
        r'.*%SPANTREE-\d-\w+:\s+(.*)',
        r'.*STP.*'
    ],
    'bgp_neighbor': [
        r'.*%BGP-\d-\w+: Neighbor (\S+) (\w+)',
        r'.*BGP neighbor (\S+) (\w+)'
    ],
    'ospf_neighbor': [
        r'.*%OSPF-\d-\w+: Neighbor (\S+) (\w+)',
        r'.*OSPF neighbor (\S+) (\w+)'
    ],
    'authentication': [
        r'.*%SEC-\d-\w+: Authentication (\w+)',
        r'.*Authentication (\w+) for user (\S+)',
        r'.*Login (\w+) for user (\S+)'
    ],
    'reload': [
        r'.*Reload requested',
        r'.*System restarting',
        r'.*%SYS-\d-RELOAD:'
    ],
    'config_change': [
        r'.*%SYS-\d-CONFIG_I: Configured from (\S+) by (\S+)',
        r'.*%SYS-\d-CONFIG: Configured from (\S+) by (\S+)'
    ],
    'high_cpu': [
        r'.*%SYS-\d-CPUHOG:',
        r'.*CPU utilization is (\d+)%'
    ],
    'high_memory': [
        r'.*%SYS-\d-NOMEMORY:',
        r'.*Memory (\w+) threshold exceeded'
    ],
    'power': [
        r'.*%PLATFORM-\d-POWER:',
        r'.*%POWER-\d-\w+:'
    ],
    'fan': [
        r'.*%PLATFORM-\d-FAN:',
        r'.*%ENVIRONMENTAL-\d-FAN:'
    ],
    'temperature': [
        r'.*%PLATFORM-\d-TEMP:',
        r'.*%ENVIRONMENTAL-\d-TEMP:'
    ],
    'stack': [
        r'.*%STACK-\d-\w+:',
        r'.*Stack Port \d change'
    ]
}

# 보안 이벤트 정의
SECURITY_EVENTS = {
    'acl_violation': [
        r'.*%SEC-\d-IPACCESSLOGP:',
        r'.*Access denied by ACL',
        r'.*%PIX-\d-106100: access-list',
        r'.*ACLLOG-\d-DENY'
    ],
    'auth_failure': [
        r'.*%SEC-\d-LOGIN_FAILED:',
        r'.*Authentication failed',
        r'.*Login failed'
    ],
    'ssh_login': [
        r'.*%SEC-\d-LOGIN:',
        r'.*SSH login success',
        r'.*Accepted password for'
    ],
    'console_login': [
        r'.*%SEC-\d-LOGIN:',
        r'.*Console login success'
    ],
    'vty_login': [
        r'.*%SEC-\d-LOGIN:',
        r'.*Vty login success'
    ],
    'crypto': [
        r'.*%CRYPTO-\d-\w+:'
    ],
    'ipsec': [
        r'.*%IPSEC-\d-\w+:'
    ],
    'dot1x': [
        r'.*%DOT1X-\d-\w+:'
    ],
    'port_security': [
        r'.*%PORT_SECURITY-\d-\w+:'
    ],
    'dhcp_snooping': [
        r'.*%DHCP_SNOOPING-\d-\w+:'
    ],
    'arp_inspection': [
        r'.*%ARP_INSPECTION-\d-\w+:'
    ],
    'storm_control': [
        r'.*%STORM_CONTROL-\d-\w+:'
    ],
    'firewall': [
        r'.*%ASA-\d-\d+:',
        r'.*%FTD-\d-\d+:'
    ]
}