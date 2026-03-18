"""
홈 화면 탭
"""
import os
from datetime import datetime

from core.i18n import tr
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QBrush,
    QLinearGradient, QPen, QPainterPath, QPixmap,
)

_BANNER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'icons', 'banner.jpg')

# ──────────────────────────────────────────────────────────────────────────────
_TOP3 = [
    {
        'num':      '01',
        'title':    tr('네트워크 자동화'),
        'sub':      tr('SSH / Telnet 다중 접속\n명령어 일괄 실행 및 설정 수집'),
        'c0':       '#0f2d6b',
        'c1':       '#1d4ed8',
        'tab':      1,
        'dogu_sub': None,
    },
    {
        'num':      '02',
        'title':    tr('로그 분석'),
        'sub':      tr('Cisco Syslog 자동 파싱\n심각도 필터 · HTML 보고서 생성'),
        'c0':       '#6b0f0f',
        'c1':       '#dc2626',
        'tab':      3,
        'dogu_sub': 4,
    },
    {
        'num':      '03',
        'title':    tr('점검 보고서'),
        'sub':      tr('show 명령어 파일 자동 분석\nPDF / Word / Excel 보고서 생성'),
        'c0':       '#2d0f6b',
        'c1':       '#7c3aed',
        'tab':      3,
        'dogu_sub': 1,
    },
]

_OTHERS = [
    {'title': tr('네트워크 진단'), 'sub': tr('Ping · TCPing 모니터링'),             'tab': 2, 'dogu_sub': None, 'color': '#0d9488', 'abbr': tr('진단')},
    {'title': tr('도구'),          'sub': tr('보고서 · 파일뷰어 · 로그분석'),       'tab': 3, 'dogu_sub': None, 'color': '#d97706', 'abbr': tr('도구')},
    {'title': tr('정보'),          'sub': tr('버전 · 라이센스'),                    'tab': 4, 'dogu_sub': None, 'color': '#4f46e5', 'abbr': tr('정보')},
]


# ──────────────────────────────────────────────────────────────────────────────
# TOP 3 — 컬러 그라데이션 카드
# ──────────────────────────────────────────────────────────────────────────────
class _TopCard(QWidget):
    def __init__(self, data, switch_fn, parent=None):
        super().__init__(parent)
        self._data   = data
        self._switch = switch_fn
        self._hov    = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(168)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor(self._data['c0']))
        g.setColorAt(1.0, QColor(self._data['c1']))

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.fillPath(path, QBrush(g))

        if self._hov:
            p.fillPath(path, QBrush(QColor(255, 255, 255, 18)))

        p.setOpacity(0.10)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 90, -40, 160, 160)
        p.drawEllipse(self.width() - 30, self.height() - 50, 100, 100)
        p.setOpacity(1.0)

        p.setPen(QPen(QColor(255, 255, 255, 60)))
        p.setFont(QFont('맑은 고딕', 36, QFont.Bold))
        p.drawText(QRect(self.width() - 90, -4, 80, 60), Qt.AlignRight, self._data['num'])

        p.setPen(QPen(QColor('#ffffff')))
        p.setFont(QFont('맑은 고딕', 18, QFont.Bold))
        p.drawText(24, 52, self._data['title'])

        p.setOpacity(0.3)
        p.setPen(QPen(QColor('#ffffff'), 1))
        p.drawLine(24, 66, 24 + 160, 66)
        p.setOpacity(1.0)

        p.setPen(QPen(QColor(255, 255, 255, 185)))
        p.setFont(QFont('맑은 고딕', 10))
        y = 86
        for line in self._data['sub'].split('\n'):
            p.drawText(24, y, line)
            y += 20

        p.setPen(QPen(QColor(255, 255, 255, 160)))
        p.setFont(QFont('맑은 고딕', 14, QFont.Bold))
        p.drawText(QRect(0, self.height() - 36, self.width() - 18, 30),
                   Qt.AlignRight | Qt.AlignVCenter, '→')
        p.end()

    def enterEvent(self, e):
        self._hov = True;  self.update()

    def leaveEvent(self, e):
        self._hov = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._switch(self._data['tab'], self._data.get('dogu_sub'))


# ──────────────────────────────────────────────────────────────────────────────
# 기타 기능 — 컬러 배지 카드
# ──────────────────────────────────────────────────────────────────────────────
class _MiniCard(QWidget):
    def __init__(self, data, switch_fn, parent=None):
        super().__init__(parent)
        self._data   = data
        self._switch = switch_fn
        self._hov    = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(84)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        accent = QColor(self._data['color'])

        # 카드 배경
        bg = QColor('#eef4ff' if self._hov else '#ffffff')
        card = QPainterPath()
        card.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(card, QBrush(bg))

        # 테두리
        border = QColor(accent.red(), accent.green(), accent.blue(), 120 if self._hov else 50)
        p.setPen(QPen(border, 1.5 if self._hov else 1.0))
        p.drawPath(card)

        # 좌측 컬러 액센트 바 (5px, 카드 영역 안으로 클리핑)
        p.setClipPath(card)
        p.fillRect(0, 0, 5, self.height(), accent)
        p.setClipping(False)

        # 컬러 원 배지
        cx, cy, cr = 40, self.height() // 2, 19
        p.setPen(Qt.NoPen)
        # 원 그림자 효과
        p.setBrush(QBrush(QColor(accent.red(), accent.green(), accent.blue(), 30)))
        p.drawEllipse(cx - cr - 2, cy - cr - 2, (cr + 2) * 2, (cr + 2) * 2)
        p.setBrush(QBrush(accent))
        p.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)

        # 배지 텍스트
        p.setPen(QPen(QColor('#ffffff')))
        p.setFont(QFont('맑은 고딕', 8, QFont.Bold))
        p.drawText(QRect(cx - cr, cy - cr, cr * 2, cr * 2),
                   Qt.AlignCenter, self._data['abbr'])

        # 제목
        p.setPen(QPen(QColor('#1e293b')))
        p.setFont(QFont('맑은 고딕', 12, QFont.Bold))
        p.drawText(72, cy - 4, self._data['title'])

        # 부제
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(72, cy + 14, self._data['sub'])

        # 화살표
        arrow_color = QColor(accent.red(), accent.green(), accent.blue(),
                             200 if self._hov else 130)
        p.setPen(QPen(arrow_color))
        p.setFont(QFont('맑은 고딕', 13, QFont.Bold))
        p.drawText(QRect(0, 0, self.width() - 16, self.height()),
                   Qt.AlignRight | Qt.AlignVCenter, '→')
        p.end()

    def enterEvent(self, e):
        self._hov = True;  self.update()

    def leaveEvent(self, e):
        self._hov = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._switch(self._data['tab'], self._data.get('dogu_sub'))


# ──────────────────────────────────────────────────────────────────────────────
# 헤더 — 배너 이미지 기반
# ──────────────────────────────────────────────────────────────────────────────
class _Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(180)
        self._pixmap = QPixmap(_BANNER_PATH)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        # 배너 이미지 (비율 유지 채우기 + 중앙 크롭)
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.width(), self.height(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            ox = (scaled.width()  - self.width())  // 2
            oy = (scaled.height() - self.height()) // 2
            p.drawPixmap(0, 0, scaled, ox, oy, self.width(), self.height())
        else:
            g = QLinearGradient(0, 0, self.width(), self.height())
            g.setColorAt(0.0, QColor('#0d1b2a'))
            g.setColorAt(1.0, QColor('#1a3a6e'))
            p.fillRect(self.rect(), QBrush(g))

        # 어두운 그라데이션 오버레이 (텍스트 가독성)
        ov = QLinearGradient(0, 0, self.width(), 0)
        ov.setColorAt(0.0, QColor(0, 0, 0, 160))
        ov.setColorAt(0.6, QColor(0, 0, 0, 80))
        ov.setColorAt(1.0, QColor(0, 0, 0, 40))
        p.fillRect(self.rect(), QBrush(ov))

        # 앱 이름
        p.setPen(QPen(QColor('#f1f5f9')))
        p.setFont(QFont('맑은 고딕', 26, QFont.Bold))
        p.drawText(36, 72, 'Network Automation')

        # 부제
        p.setPen(QPen(QColor(200, 220, 255, 180)))
        p.setFont(QFont('맑은 고딕', 10))
        p.drawText(38, 98, tr('Cisco 네트워크 장비  자동화 · 분석 · 점검'))

        # 버전 배지
        br = QRect(38, 116, 58, 22)
        p.setBrush(QBrush(QColor(255, 255, 255, 35)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(br, 11, 11)
        p.setPen(QPen(QColor('#93c5fd')))
        p.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        p.drawText(br, Qt.AlignCenter, 'v 8.0')
        p.end()


# ──────────────────────────────────────────────────────────────────────────────
# 하단 시계 바
# ──────────────────────────────────────────────────────────────────────────────
class _ClockBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setObjectName('clockBar')
        self.setStyleSheet('#clockBar{background:#1e293b;border-radius:10px}')

        h = QHBoxLayout(self)
        h.setContentsMargins(22, 0, 22, 0)

        self.lbl_date = QLabel()
        self.lbl_date.setFont(QFont('맑은 고딕', 10))
        self.lbl_date.setStyleSheet('color:#94a3b8;background:transparent')

        self.lbl_time = QLabel()
        self.lbl_time.setFont(QFont('맑은 고딕', 16, QFont.Bold))
        self.lbl_time.setStyleSheet('color:#f1f5f9;background:transparent')

        h.addWidget(self.lbl_date)
        h.addStretch()
        h.addWidget(self.lbl_time)

        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

    def _tick(self):
        now = datetime.now()
        day = [tr('월'), tr('화'), tr('수'), tr('목'), tr('금'), tr('토'), tr('일')][now.weekday()]
        self.lbl_date.setText(f"📅  {now.strftime(f'%Y년 %m월 %d일  {day}요일')}")
        self.lbl_time.setText(f"🕐  {now.strftime('%H : %M : %S')}")


# ──────────────────────────────────────────────────────────────────────────────
def _sec(text):
    l = QLabel(text.upper())
    l.setFont(QFont('맑은 고딕', 9, QFont.Bold))
    l.setStyleSheet('color:#94a3b8;background:transparent;letter-spacing:2px')
    return l


# ──────────────────────────────────────────────────────────────────────────────
class HomeTab(QWidget):
    def __init__(self, switch_tab_fn, parent=None):
        super().__init__(parent)
        self._switch = switch_tab_fn
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet('background:#f1f5f9')

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet('background:transparent;border:none')
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        ol = QVBoxLayout(self)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)

        body = QWidget()
        body.setStyleSheet('background:transparent')
        scroll.setWidget(body)

        root = QVBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 32)
        root.setSpacing(0)

        root.addWidget(_Header())

        # 콘텐츠
        w = QWidget()
        w.setStyleSheet('background:transparent')
        wv = QVBoxLayout(w)
        wv.setContentsMargins(36, 26, 36, 0)
        wv.setSpacing(0)

        wv.addWidget(_sec(tr('주요 기능')))
        wv.addSpacing(14)

        row1 = QHBoxLayout()
        row1.setSpacing(14)
        for d in _TOP3:
            row1.addWidget(_TopCard(d, self._switch))
        wv.addLayout(row1)

        wv.addSpacing(28)
        wv.addWidget(_sec(tr('기타 기능')))
        wv.addSpacing(12)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        for d in _OTHERS:
            row2.addWidget(_MiniCard(d, self._switch))
        wv.addLayout(row2)

        wv.addSpacing(28)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:#e2e8f0')
        wv.addWidget(sep)
        wv.addSpacing(10)

        foot = QHBoxLayout()
        for txt, align in [('Network Automation  v8.0', Qt.AlignLeft),
                            (tr('카드를 클릭하면 해당 기능으로 이동합니다'), Qt.AlignRight)]:
            l = QLabel(txt)
            l.setFont(QFont('맑은 고딕', 9))
            l.setStyleSheet('color:#cbd5e1;background:transparent')
            foot.addWidget(l)
            if align == Qt.AlignLeft:
                foot.addStretch()

        wv.addLayout(foot)
        wv.addSpacing(12)
        wv.addWidget(_ClockBar())
        root.addWidget(w)
        root.addStretch()
