"""
모던 플랫 테마 - 깔끔하고 컴팩트
"""


class ModernTheme:

    # ── 색상 팔레트 ──────────────────────────────────────────────
    PRIMARY       = "#3b82f6"   # 파란색 메인
    PRIMARY_DARK  = "#2563eb"
    PRIMARY_LIGHT = "#eff6ff"   # 아주 연한 파랑 (선택 배경 등)

    SUCCESS = "#10b981"
    DANGER  = "#ef4444"
    WARNING = "#f59e0b"

    # 배경
    BG_APP    = "#f1f5f9"   # 앱 전체 배경 (연한 회색)
    BG_PANEL  = "#ffffff"   # 패널/카드 배경
    BG_INPUT  = "#ffffff"   # 입력 필드 배경
    BG_HOVER  = "#f8fafc"   # 호버 배경

    # 텍스트
    TEXT_MAIN  = "#1e293b"   # 본문
    TEXT_SUB   = "#64748b"   # 보조 텍스트
    TEXT_MUTED = "#94a3b8"   # 흐린 텍스트

    # 테두리
    BORDER       = "#e2e8f0"
    BORDER_FOCUS = "#3b82f6"

    @staticmethod
    def get_stylesheet() -> str:
        P  = ModernTheme.PRIMARY
        PD = ModernTheme.PRIMARY_DARK
        PL = ModernTheme.PRIMARY_LIGHT
        BG_APP   = ModernTheme.BG_APP
        BG_PANEL = ModernTheme.BG_PANEL
        BG_INPUT = ModernTheme.BG_INPUT
        BG_HOVER = ModernTheme.BG_HOVER
        TM = ModernTheme.TEXT_MAIN
        TS = ModernTheme.TEXT_SUB
        TT = ModernTheme.TEXT_MUTED
        BD = ModernTheme.BORDER
        BF = ModernTheme.BORDER_FOCUS

        return f"""

/* ── 기본 ─────────────────────────────────────────────────── */
* {{
    font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
    font-size: 11px;
    outline: none;
}}

QWidget {{
    background-color: transparent;
    color: {TM};
}}

QMainWindow, QDialog {{
    background-color: {BG_APP};
}}

/* ── 메인 탭 바 ───────────────────────────────────────────── */
/* 최상위 QTabWidget */
QMainWindow > QWidget > QTabWidget > QTabBar::tab,
QTabWidget#mainTabs > QTabBar::tab {{
    background-color: transparent;
    color: {TS};
    padding: 8px 18px;
    margin-right: 2px;
    font-weight: 600;
    font-size: 11px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 90px;
}}

QMainWindow > QWidget > QTabWidget > QTabBar::tab:selected,
QTabWidget#mainTabs > QTabBar::tab:selected {{
    color: {P};
    border-bottom: 2px solid {P};
    background-color: transparent;
}}

QMainWindow > QWidget > QTabWidget > QTabBar::tab:hover:!selected,
QTabWidget#mainTabs > QTabBar::tab:hover:!selected {{
    color: {TM};
    background-color: {BG_HOVER};
}}

/* ── 전체 QTabWidget (공통) ──────────────────────────────── */
QTabWidget::pane {{
    background-color: {BG_PANEL};
    border: 1px solid {BD};
    border-radius: 6px;
    border-top-left-radius: 0px;
}}

QTabBar {{
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: {BG_HOVER};
    color: {TS};
    padding: 6px 14px;
    margin-right: 2px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid {BD};
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 70px;
}}

QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {P};
    border-top: 2px solid {P};
    border-left: 1px solid {BD};
    border-right: 1px solid {BD};
    border-bottom: none;
}}

QTabBar::tab:hover:!selected {{
    background-color: #e2e8f0;
    color: {TM};
}}

/* ── 버튼 ─────────────────────────────────────────────────── */
QPushButton {{
    background-color: {P};
    color: white;
    border: none;
    padding: 5px 14px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 11px;
    min-height: 26px;
}}

QPushButton:hover {{
    background-color: {PD};
}}

QPushButton:pressed {{
    background-color: #1e40af;
}}

QPushButton:disabled {{
    background-color: #cbd5e1;
    color: #94a3b8;
}}

/* 보조 버튼 (flat) */
QPushButton[flat="true"] {{
    background-color: {BG_HOVER};
    color: {TM};
    border: 1px solid {BD};
}}

QPushButton[flat="true"]:hover {{
    background-color: #e2e8f0;
}}

/* ── 입력 필드 ────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BD};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TM};
    font-size: 11px;
    selection-background-color: {P};
    selection-color: white;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {BF};
    background-color: {BG_INPUT};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: #f1f5f9;
    color: {TT};
    border-color: #e2e8f0;
}}

/* ── 스핀박스 ─────────────────────────────────────────────── */
QSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BD};
    border-radius: 4px;
    padding: 3px 6px;
    color: {TM};
    font-size: 11px;
    min-height: 22px;
}}

QSpinBox:focus {{
    border-color: {BF};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {BG_HOVER};
    border: none;
    width: 16px;
    border-radius: 2px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: #e2e8f0;
}}

/* ── 콤보박스 ─────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BD};
    border-radius: 4px;
    padding: 3px 8px;
    color: {TM};
    font-size: 11px;
    min-height: 22px;
}}

QComboBox:focus {{
    border-color: {BF};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}

QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: white;
    border: 1px solid {BD};
    border-radius: 4px;
    selection-background-color: {PL};
    selection-color: {P};
    color: {TM};
    padding: 2px;
}}

/* ── 체크박스 & 라디오 ────────────────────────────────────── */
QCheckBox, QRadioButton {{
    color: {TM};
    spacing: 6px;
    font-size: 11px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #cbd5e1;
    background-color: white;
}}

QCheckBox::indicator:checked {{
    background-color: {P};
    border-color: {P};
    image: none;
}}

QCheckBox::indicator:hover {{
    border-color: {P};
}}

QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 1px solid #cbd5e1;
    background-color: white;
}}

QRadioButton::indicator:checked {{
    background-color: {P};
    border-color: {P};
}}

/* ── 그룹박스 ─────────────────────────────────────────────── */
QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BD};
    border-radius: 6px;
    margin-top: 14px;
    padding: 8px 6px 6px 6px;
    font-weight: 700;
    font-size: 11px;
    color: {TM};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 0px;
    padding: 0 4px;
    color: {TM};
    background-color: {BG_PANEL};
    font-weight: 700;
}}

/* ── 프로그레스 바 ────────────────────────────────────────── */
QProgressBar {{
    background-color: #e2e8f0;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: {TM};
    font-weight: 600;
    font-size: 10px;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {P};
    border-radius: 4px;
}}

/* ── 테이블 ───────────────────────────────────────────────── */
QTableWidget {{
    background-color: {BG_PANEL};
    border: 1px solid {BD};
    border-radius: 4px;
    gridline-color: {BD};
    selection-background-color: {PL};
    selection-color: {P};
    color: {TM};
    font-size: 11px;
    alternate-background-color: #f8fafc;
}}

QTableWidget::item {{
    padding: 4px 6px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {PL};
    color: {P};
}}

QHeaderView::section {{
    background-color: #f1f5f9;
    color: {TS};
    padding: 5px 8px;
    border: none;
    border-right: 1px solid {BD};
    border-bottom: 1px solid {BD};
    font-weight: 700;
    font-size: 10px;
}}

QHeaderView::section:first {{
    border-top-left-radius: 4px;
}}

/* ── 스크롤바 ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #94a3b8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: #cbd5e1;
    border-radius: 4px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #94a3b8;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── 메뉴바 & 메뉴 ────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_PANEL};
    color: {TM};
    border-bottom: 1px solid {BD};
    padding: 1px 4px;
    font-size: 11px;
}}

QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
    background: transparent;
}}

QMenuBar::item:selected {{
    background-color: {PL};
    color: {P};
}}

QMenu {{
    background-color: white;
    border: 1px solid {BD};
    border-radius: 6px;
    padding: 4px;
    font-size: 11px;
}}

QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
    color: {TM};
}}

QMenu::item:selected {{
    background-color: {PL};
    color: {P};
}}

QMenu::separator {{
    height: 1px;
    background: {BD};
    margin: 4px 8px;
}}

/* ── 상태바 ───────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_PANEL};
    color: {TS};
    border-top: 1px solid {BD};
    font-size: 10px;
    padding: 0 6px;
}}

/* ── 레이블 ───────────────────────────────────────────────── */
QLabel {{
    color: {TM};
    background-color: transparent;
    font-size: 11px;
}}

/* ── 스플리터 ─────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BD};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── 툴팁 ─────────────────────────────────────────────────── */
QToolTip {{
    background-color: #1e293b;
    color: white;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 10px;
}}

/* ── 메시지박스 ───────────────────────────────────────────── */
QMessageBox {{
    background-color: white;
}}

QMessageBox QLabel {{
    color: {TM};
    background-color: transparent;
    font-size: 11px;
    min-width: 220px;
}}

QMessageBox QPushButton {{
    min-width: 70px;
    min-height: 26px;
    padding: 4px 16px;
    background-color: {P};
    color: white;
}}

/* ── 텍스트브라우저 ───────────────────────────────────────── */
QTextBrowser {{
    background-color: {BG_INPUT};
    border: 1px solid {BD};
    border-radius: 4px;
    padding: 4px;
    color: {TM};
    font-size: 11px;
    selection-background-color: {P};
    selection-color: white;
}}

"""
