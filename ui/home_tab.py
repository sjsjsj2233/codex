"""Home workspace and shortcuts to the existing tools."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from core.i18n import get_language


def _copy(ko, en):
    return en if get_language() == "en" else ko


def _label(text, size=10, color="#5b6b82", bold=False):
    label = QLabel(text)
    label.setFont(QFont("Malgun Gothic", size, QFont.Bold if bold else QFont.Normal))
    label.setStyleSheet(f"color:{color};background:transparent;border:none")
    label.setWordWrap(True)
    label.setAttribute(Qt.WA_TransparentForMouseEvents)
    return label


class _Hero(QFrame):
    """Painted topology motif; all labels and actions remain normal Qt widgets."""

    def __init__(self, switch, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(235)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("homeHero")
        self.setStyleSheet("#homeHero{background:#111f38;border-radius:16px}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 27, 36, 28)
        layout.setSpacing(0)

        eyebrow = _label(_copy("NETWORK OPERATIONS  /  WORKSPACE", "NETWORK OPERATIONS  /  WORKSPACE"),
                         8, "#72c9ee", True)
        layout.addWidget(eyebrow)
        layout.addSpacing(16)

        title = _label(_copy("네트워크 작업을\n한 곳에서.", "Your network work,\nin one place."),
                       24, "#ffffff", True)
        title.setMaximumWidth(590)
        layout.addWidget(title)
        layout.addSpacing(8)

        subtitle = _label(_copy(
            "Cisco 장비 접속부터 명령 실행, 진단, 보고서까지 빠르게 이어가세요.",
            "Connect to Cisco devices, run commands, diagnose issues, and build reports."
        ), 9, "#b8c9dd")
        subtitle.setMaximumWidth(625)
        layout.addWidget(subtitle)
        layout.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(9)
        start = QPushButton(_copy("장비 자동화 시작  →", "Start automation  →"))
        start.setCursor(Qt.PointingHandCursor)
        start.setFixedHeight(37)
        start.setStyleSheet(
            "QPushButton{background:#52bbec;color:#0d263f;border:none;border-radius:8px;"
            "padding:0 17px;font-weight:700}"
            "QPushButton:hover{background:#8dd8f6}"
        )
        start.clicked.connect(lambda: switch(1, None))
        actions.addWidget(start)

        inspect = QPushButton(_copy("진단 도구 열기", "Open diagnostics"))
        inspect.setCursor(Qt.PointingHandCursor)
        inspect.setFixedHeight(37)
        inspect.setStyleSheet(
            "QPushButton{background:#203858;color:#e8f3ff;border:1px solid #436080;"
            "border-radius:8px;padding:0 17px;font-weight:600}"
            "QPushButton:hover{background:#2b4b70}"
        )
        inspect.clicked.connect(lambda: switch(3, None))
        actions.addWidget(inspect)
        actions.addStretch()
        layout.addLayout(actions)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        if width < 850:
            painter.end()
            return

        # Quiet network map behind the hero copy.
        cx = width - 190
        cy = height // 2
        nodes = [(cx - 92, cy - 57, 6), (cx + 79, cy - 76, 7),
                 (cx + 103, cy + 61, 6), (cx - 72, cy + 77, 7),
                 (cx + 9, cy - 6, 14)]
        painter.setPen(QPen(QColor(107, 177, 222, 65), 1))
        for index in range(4):
            painter.drawLine(nodes[index][0], nodes[index][1], nodes[4][0], nodes[4][1])
        painter.setPen(QPen(QColor(107, 177, 222, 30), 1))
        painter.drawEllipse(cx - 136, cy - 127, 270, 250)
        painter.drawEllipse(cx - 96, cy - 89, 190, 177)
        for x, y, radius in nodes:
            painter.setPen(QPen(QColor("#67c8f2"), 1.5))
            painter.setBrush(QColor("#172c48"))
            painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)
        painter.end()


class _FeatureCard(QFrame):
    def __init__(self, number, title, detail, tag, switch, target, parent=None):
        super().__init__(parent)
        self._switch = switch
        self._target = target
        self.setObjectName("featureCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._set_hover(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(19, 18, 19, 18)
        layout.setSpacing(0)
        top = QHBoxLayout()
        top.addWidget(_label(number, 9, "#3884c6", True))
        top.addStretch()
        top.addWidget(_label(tag, 8, "#8293a9", True))
        layout.addLayout(top)
        layout.addSpacing(24)
        layout.addWidget(_label(title, 14, "#14243d", True))
        layout.addSpacing(5)
        layout.addWidget(_label(detail, 9, "#65758c"))
        layout.addStretch()
        layout.addWidget(_label(_copy("열기  ↗", "Open  ↗"), 9, "#2563eb", True))

    def _set_hover(self, active):
        border = "#9bc7f3" if active else "#dfe7f0"
        background = "#fafdff" if active else "#ffffff"
        self.setStyleSheet(
            f"#featureCard{{background:{background};border:1px solid {border};border-radius:12px}}"
        )

    def enterEvent(self, event):
        self._set_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_hover(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._switch(*self._target)
        super().mousePressEvent(event)


class _UtilityCard(QFrame):
    def __init__(self, initials, title, detail, switch, target, parent=None):
        super().__init__(parent)
        self._switch = switch
        self._target = target
        self.setObjectName("utilityCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(82)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._set_hover(False)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(11)
        icon = _label(initials, 9, "#2373af", True)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(34, 34)
        icon.setStyleSheet("background:#eaf5fd;color:#2373af;border-radius:8px")
        row.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(_label(title, 10, "#14243d", True))
        text.addWidget(_label(detail, 8, "#8293a9"))
        row.addLayout(text, 1)
        row.addWidget(_label("↗", 12, "#92a4ba"))

    def _set_hover(self, active):
        border = "#9bc7f3" if active else "#dfe7f0"
        background = "#fafdff" if active else "#ffffff"
        self.setStyleSheet(
            f"#utilityCard{{background:{background};border:1px solid {border};border-radius:11px}}"
        )

    def enterEvent(self, event):
        self._set_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_hover(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._switch(*self._target)
        super().mousePressEvent(event)


class HomeTab(QWidget):
    def __init__(self, switch_tab_fn, parent=None):
        super().__init__(parent)
        self._switch = switch_tab_fn
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("background:#f4f7fb")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;background:#f4f7fb}")
        outer.addWidget(scroll)

        body = QWidget()
        body.setStyleSheet("background:#f4f7fb")
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(0)

        layout.addWidget(_Hero(self._switch))
        layout.addSpacing(24)
        layout.addWidget(_label(_copy("주요 작업", "Core workflows"), 16, "#14243d", True))
        layout.addSpacing(4)
        layout.addWidget(_label(_copy(
            "자주 쓰는 기능으로 바로 이동하세요.", "Jump directly to the work you need."
        ), 9, "#8293a9"))
        layout.addSpacing(13)

        core = [
            ("01", _copy("장비 자동화", "Device automation"),
             _copy("여러 장비에 접속하고 명령을 한 번에 실행", "Connect to devices and run commands in bulk"),
             "SSH  /  TELNET", (1, None)),
            ("02", _copy("실시간 콘솔", "Live console"),
             _copy("장비 세션을 열고 응답을 바로 확인", "Open a session and inspect responses live"),
             "TERMINAL", (2, None)),
            ("03", _copy("네트워크 진단", "Network diagnostics"),
             _copy("연결 상태와 응답 시간을 빠르게 점검", "Check reachability and response times"),
             "PING  /  TCP", (3, None)),
        ]
        core_row = QHBoxLayout()
        core_row.setSpacing(12)
        for item in core:
            core_row.addWidget(_FeatureCard(item[0], item[1], item[2], item[3],
                                            self._switch, item[4]))
        layout.addLayout(core_row)

        layout.addSpacing(25)
        layout.addWidget(_label(_copy("분석 · 보고서", "Analysis & reports"), 16, "#14243d", True))
        layout.addSpacing(4)
        layout.addWidget(_label(_copy(
            "설정 변경점과 장비 데이터를 결과물로 정리합니다.",
            "Turn configuration changes and device data into clear results."
        ), 9, "#8293a9"))
        layout.addSpacing(13)

        utilities = [
            ("DIFF", _copy("설정 비교", "Config comparison"),
             _copy("변경점 추적", "Track changes"), (4, 0)),
            ("RPT", _copy("점검 보고서", "Inspection reports"),
             _copy("점검 결과 정리", "Organize findings"), (4, 1)),
            ("LOG", _copy("로그 분석", "Log analysis"),
             _copy("이벤트 흐름 파악", "Review event flow"), (4, 3)),
            ("FILE", _copy("파일 뷰어", "File viewer"),
             _copy("로그·텍스트 검색", "Search logs and text"), (4, 4)),
        ]
        utility_row = QHBoxLayout()
        utility_row.setSpacing(11)
        for item in utilities:
            utility_row.addWidget(_UtilityCard(item[0], item[1], item[2],
                                               self._switch, item[3]))
        layout.addLayout(utility_row)

        layout.addSpacing(25)
        footer = QHBoxLayout()
        footer.addWidget(_label("NETWORK AUTOMATION   /   v9.9", 8, "#9aa9bb", True))
        footer.addStretch()
        footer.addWidget(_label(_copy("Cisco 네트워크 운영 워크스페이스", "Cisco network operations workspace"),
                                8, "#9aa9bb"))
        layout.addLayout(footer)
        layout.addStretch()
