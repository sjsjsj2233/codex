"""
컴팩트한 라이트 테마 - 화면에 잘 맞게
"""

class ModernTheme:
    """컴팩트한 라이트 테마"""

    # 색상 팔레트
    PRIMARY = "#3b82f6"
    PRIMARY_DARK = "#2563eb"
    PRIMARY_LIGHT = "#60a5fa"

    SECONDARY = "#10b981"
    DANGER = "#ef4444"
    WARNING = "#f59e0b"
    SUCCESS = "#10b981"

    # 배경 색상 - 흰색으로 통일
    BG_PRIMARY = "#ffffff"      # 흰색
    BG_SECONDARY = "#ffffff"    # 흰색
    BG_TERTIARY = "#f8fafc"     # 아주 연한 회색 (탭바용)

    # 텍스트 색상
    TEXT_PRIMARY = "#1e293b"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED = "#64748b"

    # 테두리 색상
    BORDER = "#e2e8f0"
    BORDER_DARK = "#cbd5e1"

    @staticmethod
    def get_stylesheet():
        return f"""
/* 전역 스타일 - 컴팩트하게 */
* {{
    font-family: "맑은 고딕", sans-serif;
    font-size: 11px;
}}

QWidget {{
    background-color: transparent;  /* 투명 배경 */
    color: {ModernTheme.TEXT_PRIMARY};
}}

QMainWindow {{
    background-color: {ModernTheme.BG_PRIMARY};  /* 메인 윈도우만 배경색 */
}}

/* 탭 위젯 - 작게 */
QTabWidget::pane {{
    border: 1px solid {ModernTheme.BORDER};
    background-color: #ffffff;  /* 순백색으로 변경 */
    border-radius: 6px;
    padding: 4px;
}}

QTabBar::tab {{
    background-color: {ModernTheme.BG_TERTIARY};
    color: {ModernTheme.TEXT_PRIMARY};
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: 600;
    font-size: 11px;
    min-width: 80px;
    border: 1px solid {ModernTheme.BORDER};
}}

QTabBar::tab:selected {{
    background-color: {ModernTheme.PRIMARY};
    color: white;
}}

QTabBar::tab:hover:!selected {{
    background-color: {ModernTheme.PRIMARY_LIGHT};
    color: white;
}}

/* 버튼 - 작게 */
QPushButton {{
    background-color: {ModernTheme.PRIMARY};
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 11px;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {ModernTheme.PRIMARY_DARK};
}}

QPushButton:pressed {{
    background-color: {ModernTheme.PRIMARY_DARK};
}}

QPushButton:disabled {{
    background-color: {ModernTheme.BORDER_DARK};
    color: {ModernTheme.TEXT_MUTED};
}}

/* 입력 필드 - 작게 */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #fafafa;  /* 아주 연한 회색 */
    border: 2px solid {ModernTheme.BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {ModernTheme.TEXT_PRIMARY};
    font-size: 11px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {ModernTheme.PRIMARY};
    background-color: #f0f9ff;  /* 연한 파란색 배경 */
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);  /* 글로우 효과 */
}}

QTextEdit::selection, QPlainTextEdit::selection, QLineEdit::selection {{
    background-color: {ModernTheme.PRIMARY};
    color: white;
}}

/* 스핀박스 - 작게 */
QSpinBox {{
    background-color: #fafafa;
    border: 1px solid {ModernTheme.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {ModernTheme.TEXT_PRIMARY};
    font-size: 11px;
    min-height: 20px;
}}

QSpinBox:focus {{
    border: 2px solid {ModernTheme.PRIMARY};
    background-color: #f0f9ff;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {ModernTheme.BG_TERTIARY};
    border: none;
    width: 16px;
}}

/* 콤보박스 - 작게 */
QComboBox {{
    background-color: #fafafa;
    border: 1px solid {ModernTheme.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {ModernTheme.TEXT_PRIMARY};
    font-size: 11px;
    min-height: 20px;
}}

QComboBox:focus {{
    border: 2px solid {ModernTheme.PRIMARY};
    background-color: #f0f9ff;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: white;
    border: 1px solid {ModernTheme.BORDER};
    selection-background-color: {ModernTheme.PRIMARY};
    selection-color: white;
    color: {ModernTheme.TEXT_PRIMARY};
    font-size: 11px;
}}

/* 체크박스 & 라디오 - 작게 */
QCheckBox, QRadioButton {{
    color: {ModernTheme.TEXT_PRIMARY};
    spacing: 6px;
    font-size: 11px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {ModernTheme.BORDER_DARK};
    background-color: white;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {ModernTheme.PRIMARY};
    border-color: {ModernTheme.PRIMARY};
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

/* 진행 바 - 작게 */
QProgressBar {{
    background-color: {ModernTheme.BG_TERTIARY};
    border: 1px solid {ModernTheme.BORDER};
    border-radius: 4px;
    text-align: center;
    color: {ModernTheme.TEXT_PRIMARY};
    font-weight: 600;
    font-size: 10px;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {ModernTheme.PRIMARY};
    border-radius: 3px;
}}

/* 그룹박스 - 작게 */
QGroupBox {{
    background-color: #fefefe;  /* 거의 흰색에 가까운 부드러운 색 */
    border: 2px solid {ModernTheme.BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    font-weight: 700;
    font-size: 11px;
    color: {ModernTheme.TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: {ModernTheme.PRIMARY};
    color: white;
    border-radius: 4px;
    margin-left: 6px;
    font-weight: 700;
    font-size: 11px;
}}

/* 테이블 - 작게 */
QTableWidget {{
    background-color: #fafafa;
    border: 1px solid {ModernTheme.BORDER};
    border-radius: 4px;
    gridline-color: {ModernTheme.BORDER};
    selection-background-color: {ModernTheme.PRIMARY};
    selection-color: white;
    color: {ModernTheme.TEXT_PRIMARY};
    font-size: 10px;
}}

QTableWidget::item {{
    padding: 4px;
    color: {ModernTheme.TEXT_PRIMARY};
}}

QTableWidget::item:selected {{
    background-color: {ModernTheme.PRIMARY};
    color: white;
}}

QHeaderView::section {{
    background-color: {ModernTheme.BG_TERTIARY};
    color: {ModernTheme.TEXT_PRIMARY};
    padding: 6px;
    border: 1px solid {ModernTheme.BORDER};
    font-weight: 700;
    font-size: 10px;
}}

/* 스크롤바 - 얇게 */
QScrollBar:vertical {{
    background-color: {ModernTheme.BG_TERTIARY};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {ModernTheme.BORDER_DARK};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {ModernTheme.PRIMARY};
}}

QScrollBar:horizontal {{
    background-color: {ModernTheme.BG_TERTIARY};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {ModernTheme.BORDER_DARK};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {ModernTheme.PRIMARY};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    border: none;
    background: none;
}}

/* 메뉴바 - 작게 */
QMenuBar {{
    background-color: {ModernTheme.BG_TERTIARY};
    color: {ModernTheme.TEXT_PRIMARY};
    border-bottom: 1px solid {ModernTheme.BORDER};
    padding: 2px;
    font-size: 11px;
}}

QMenuBar::item {{
    padding: 4px 12px;
    border-radius: 3px;
    color: {ModernTheme.TEXT_PRIMARY};
}}

QMenuBar::item:selected {{
    background-color: {ModernTheme.PRIMARY};
    color: white;
}}

QMenu {{
    background-color: white;
    border: 1px solid {ModernTheme.BORDER};
    border-radius: 4px;
    padding: 4px;
    font-size: 11px;
}}

QMenu::item {{
    padding: 6px 20px;
    border-radius: 3px;
    color: {ModernTheme.TEXT_PRIMARY};
}}

QMenu::item:selected {{
    background-color: {ModernTheme.PRIMARY};
    color: white;
}}

/* 상태바 - 작게 */
QStatusBar {{
    background-color: {ModernTheme.BG_TERTIARY};
    color: {ModernTheme.TEXT_PRIMARY};
    border-top: 1px solid {ModernTheme.BORDER};
    font-size: 10px;
    padding: 2px;
}}

/* 레이블 */
QLabel {{
    color: {ModernTheme.TEXT_PRIMARY};
    background-color: transparent;
    font-size: 11px;
}}

/* 메시지 박스 */
QMessageBox {{
    background-color: white;
    color: #1e293b;
}}

QMessageBox QLabel {{
    color: #1e293b;
    background-color: transparent;
    font-size: 12px;
    padding: 10px 15px;
    margin: 0px;
    qproperty-alignment: AlignCenter;
}}

QMessageBox QPushButton {{
    background-color: #3b82f6;
    color: white;
    border: none;
    padding: 6px 18px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 11px;
    min-width: 70px;
    min-height: 28px;
}}

QMessageBox QPushButton:hover {{
    background-color: #2563eb;
}}

QMessageBox QPushButton:pressed {{
    background-color: #1d4ed8;
}}
"""
