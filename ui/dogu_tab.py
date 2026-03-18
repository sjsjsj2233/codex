"""
도구 탭 — 통합 허브
설정 비교, 점검 보고서, IOS-XE 보고서, NX-OS 보고서, 로그 분석
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStackedWidget,
)
from PyQt5.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPen
from PyQt5.QtCore import Qt, pyqtSignal
from core.i18n import tr


# ── 도구 허브 상수 ────────────────────────────────────────────────────────────
_NAV_ITEMS = [
    {'title': tr('설정 비교'),     'sub': tr('두 설정 변경사항 비교'),       'color': '#7c3aed', 'abbr': tr('비교')},
    {'title': tr('점검 보고서'),   'sub': tr('장비 점검 결과 PDF/Word/Excel'), 'color': '#ea580c', 'abbr': tr('점검')},
    {'title': 'IOS-XE 보고서', 'sub': tr('Cisco IOS-XE 데이터 수집'),   'color': '#2563eb', 'abbr': 'IOS'},
    {'title': 'NX-OS 보고서',  'sub': tr('Cisco Nexus 데이터 수집'),    'color': '#7c3aed', 'abbr': 'NXS'},
    {'title': tr('로그 분석'),     'sub': tr('Cisco 로그 파일 파싱'),        'color': '#dc2626', 'abbr': tr('로그')},
    {'title': tr('파일 뷰어'),     'sub': tr('LOG · TXT 검색 · 구문 강조'), 'color': '#0891b2', 'abbr': tr('뷰어')},
]


# ── 사이드바 헤더 ─────────────────────────────────────────────────────────────
class _SidebarHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor('#0f172a'))
        g.setColorAt(1.0, QColor('#1e293b'))
        p.fillRect(self.rect(), QBrush(g))
        # decorative circle
        p.setOpacity(0.08)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(140, -20, 100, 100)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor('#f8fafc')))
        p.setFont(QFont('맑은 고딕', 14, QFont.Bold))
        p.drawText(20, 38, tr('도구'))
        p.setPen(QPen(QColor('#64748b')))
        p.setFont(QFont('맑은 고딕', 8))
        p.drawText(20, 56, tr('통합 도구 · 분석 · 보고서'))
        p.end()


# ── 네비게이션 아이템 ─────────────────────────────────────────────────────────
class _NavItem(QWidget):
    clicked = pyqtSignal(int)

    def __init__(self, idx, title, sub, color, abbr, parent=None):
        super().__init__(parent)
        self._idx    = idx
        self._title  = title
        self._sub    = sub
        self._color  = color
        self._abbr   = abbr
        self._active = False
        self._hover  = False
        self.setFixedHeight(64)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def set_active(self, v):
        self._active = v
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._idx)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        if self._active:
            p.fillRect(self.rect(), QColor('#1a3550'))
            # Left accent bar
            p.fillRect(0, 0, 4, h, QColor('#3b82f6'))
        elif self._hover:
            p.fillRect(self.rect(), QColor('#243040'))

        # Bottom divider
        p.setPen(QPen(QColor('#2d3f52')))
        p.drawLine(12, h - 1, w - 1, h - 1)

        # Colored circle badge
        cx, cy, r = 32, h // 2, 15
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Abbreviation in circle
        p.setPen(QPen(QColor('#ffffff')))
        p.setFont(QFont('맑은 고딕', 7, QFont.Bold))
        p.drawText(cx - r, cy - r, r * 2, r * 2, Qt.AlignCenter, self._abbr[:3])

        # Title
        p.setPen(QPen(QColor('#f8fafc') if self._active else QColor('#e2e8f0')))
        p.setFont(QFont('맑은 고딕', 10, QFont.Bold))
        p.drawText(56, cy - 10, w - 64, 20, Qt.AlignVCenter | Qt.AlignLeft, self._title)

        # Subtitle
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 8, QFont.Bold))
        p.drawText(56, cy + 6, w - 64, 16, Qt.AlignVCenter | Qt.AlignLeft, self._sub)

        p.end()


# ── 통합 도구 탭 ──────────────────────────────────────────────────────────────
# 유료 기능 인덱스 (설정 비교, 점검 보고서, IOS-XE, NX-OS, 로그 분석)
_PREMIUM_INDICES = {0, 1, 4}
_PREMIUM_NAMES   = {
    0: '설정 비교',
    1: '점검 보고서',
    4: '로그 분석',
}


class DoguTab(QWidget):
    def __init__(self, parent=None, license_manager=None):
        super().__init__(parent)
        self._lm = license_manager
        self._nav_items = []
        self._current_idx = 5   # 기본: 파일 뷰어 (무료)
        self.init_ui()
        self._select(5)

    def init_ui(self):
        self.setObjectName('doguTab')
        self.setStyleSheet('#doguTab { background: #f1f5f9; }')
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 좌측 사이드바 ─────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(216)
        sidebar.setStyleSheet('background:#1e293b')
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)

        sv.addWidget(_SidebarHeader())

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background:#334155')
        sv.addWidget(sep)

        for i, item in enumerate(_NAV_ITEMS):
            nav = _NavItem(i, item['title'], item['sub'], item['color'], item['abbr'])
            nav.clicked.connect(self._select)
            self._nav_items.append(nav)
            sv.addWidget(nav)

        sv.addStretch()

        ver = QLabel('Network Automation v8.0')
        ver.setFont(QFont('맑은 고딕', 8))
        ver.setStyleSheet('color:#475569;padding:12px;background:transparent')
        ver.setAlignment(Qt.AlignCenter)
        sv.addWidget(ver)

        root.addWidget(sidebar)

        # ── 우측 컨텐츠 영역 ─────────────────────────────────────────────
        from ui.config_compare_tab import ConfigCompareTab
        from ui.inspection_tab import InspectionTab
        from ui.report_tab import (EnhancedInspectionReportGenerator,
                                   EnhancedNexusReportGenerator)
        from ui.log_analyzer_tab import LogAnalyzerTab
        from ui.file_viewer_tab import FileViewerTab

        self._stack = QStackedWidget()
        self._stack.setStyleSheet('QStackedWidget{background:#f1f5f9}')
        self._stack.addWidget(ConfigCompareTab())                     # 0 설정 비교
        self._stack.addWidget(InspectionTab().as_widget())            # 1 점검 보고서
        self._stack.addWidget(EnhancedInspectionReportGenerator())    # 2 IOS-XE
        self._stack.addWidget(EnhancedNexusReportGenerator())         # 3 NX-OS
        self._stack.addWidget(LogAnalyzerTab().as_widget())           # 4 로그 분석
        self._stack.addWidget(FileViewerTab())                        # 5 파일 뷰어

        root.addWidget(self._stack, 1)

    def _select(self, idx: int):
        # 유료 기능 진입 시 라이센스 확인
        if idx in _PREMIUM_INDICES:
            if self._lm is None or not self._lm.is_licensed():
                from ui.premium_popup import PremiumPopup
                PremiumPopup(self, feature=_PREMIUM_NAMES[idx]).exec_()
                # 팝업 후 현재 탭 유지 (파일 뷰어로 돌아감)
                for i, item in enumerate(self._nav_items):
                    item.set_active(i == self._current_idx)
                return

        self._current_idx = idx
        for i, item in enumerate(self._nav_items):
            item.set_active(i == idx)
        self._stack.setCurrentIndex(idx)
