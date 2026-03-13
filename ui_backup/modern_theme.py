"""
모던 UI 테마 - 전체 애플리케이션용
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt


class ModernTheme:
    """모던 테마 스타일 정의"""

    # 색상 팔레트
    COLORS = {
        # Primary colors
        'primary': '#3498db',
        'primary_dark': '#2980b9',
        'primary_light': '#5dade2',

        # Success
        'success': '#27ae60',
        'success_dark': '#229954',
        'success_light': '#52be80',

        # Danger
        'danger': '#e74c3c',
        'danger_dark': '#c0392b',
        'danger_light': '#ec7063',

        # Warning
        'warning': '#f39c12',
        'warning_dark': '#d68910',
        'warning_light': '#f5b041',

        # Info
        'info': '#3498db',
        'info_dark': '#2980b9',
        'info_light': '#5dade2',

        # Neutral
        'dark': '#2c3e50',
        'dark_light': '#34495e',
        'gray': '#7f8c8d',
        'gray_light': '#95a5a6',
        'light': '#ecf0f1',
        'light_dark': '#bdc3c7',
        'white': '#ffffff',

        # Background
        'bg_primary': '#f8f9fa',
        'bg_secondary': '#ffffff',
        'bg_dark': '#2c3e50',

        # Text
        'text_primary': '#2c3e50',
        'text_secondary': '#7f8c8d',
        'text_white': '#ffffff',

        # Border
        'border': '#dee2e6',
        'border_light': '#e9ecef',
    }

    @staticmethod
    def get_stylesheet():
        """전체 애플리케이션 스타일시트 반환"""
        return f"""
/* ==================== 전역 설정 ==================== */
QWidget {{
    font-family: '맑은 고딕', 'Segoe UI', sans-serif;
    font-size: 10pt;
    color: {ModernTheme.COLORS['text_primary']};
}}

QMainWindow {{
    background-color: {ModernTheme.COLORS['bg_primary']};
}}

/* ==================== 탭 위젯 ==================== */
QTabWidget::pane {{
    border: none;
    background-color: {ModernTheme.COLORS['bg_primary']};
}}

QTabBar::tab {{
    background-color: {ModernTheme.COLORS['white']};
    color: {ModernTheme.COLORS['text_secondary']};
    padding: 12px 20px;
    margin-right: 4px;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: bold;
    font-size: 10pt;
}}

QTabBar::tab:selected {{
    background-color: {ModernTheme.COLORS['primary']};
    color: {ModernTheme.COLORS['text_white']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {ModernTheme.COLORS['light']};
    color: {ModernTheme.COLORS['primary']};
}}

/* ==================== 그룹박스 ==================== */
QGroupBox {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 10px;
    margin-top: 12px;
    padding: 15px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {ModernTheme.COLORS['primary']};
    background-color: {ModernTheme.COLORS['white']};
}}

/* ==================== 버튼 ==================== */
QPushButton {{
    background-color: {ModernTheme.COLORS['primary']};
    color: {ModernTheme.COLORS['text_white']};
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 10pt;
    min-height: 32px;
}}

QPushButton:hover {{
    background-color: {ModernTheme.COLORS['primary_dark']};
}}

QPushButton:pressed {{
    background-color: {ModernTheme.COLORS['primary_dark']};
    padding-top: 12px;
}}

QPushButton:disabled {{
    background-color: {ModernTheme.COLORS['gray_light']};
    color: {ModernTheme.COLORS['text_secondary']};
}}

/* ==================== 입력 필드 ==================== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {ModernTheme.COLORS['primary_light']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {ModernTheme.COLORS['primary']};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {ModernTheme.COLORS['light']};
    color: {ModernTheme.COLORS['text_secondary']};
}}

/* ==================== 콤보박스 ==================== */
QComboBox {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 32px;
}}

QComboBox:hover {{
    border: 2px solid {ModernTheme.COLORS['primary_light']};
}}

QComboBox:focus {{
    border: 2px solid {ModernTheme.COLORS['primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {ModernTheme.COLORS['text_secondary']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 6px;
    selection-background-color: {ModernTheme.COLORS['primary']};
    selection-color: {ModernTheme.COLORS['text_white']};
    padding: 5px;
}}

/* ==================== 스핀박스 ==================== */
QSpinBox, QDoubleSpinBox {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 32px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {ModernTheme.COLORS['primary']};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 20px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {ModernTheme.COLORS['light']};
}}

/* ==================== 체크박스 & 라디오버튼 ==================== */
QCheckBox, QRadioButton {{
    spacing: 8px;
    color: {ModernTheme.COLORS['text_primary']};
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 4px;
    background-color: {ModernTheme.COLORS['white']};
}}

QRadioButton::indicator {{
    border-radius: 10px;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {ModernTheme.COLORS['primary']};
    border-color: {ModernTheme.COLORS['primary']};
}}

QCheckBox::indicator:checked {{
    image: none;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {ModernTheme.COLORS['primary']};
}}

/* ==================== 프로그레스바 ==================== */
QProgressBar {{
    background-color: {ModernTheme.COLORS['light']};
    border: none;
    border-radius: 8px;
    text-align: center;
    color: {ModernTheme.COLORS['text_white']};
    font-weight: bold;
    height: 24px;
}}

QProgressBar::chunk {{
    background-color: {ModernTheme.COLORS['primary']};
    border-radius: 8px;
}}

/* ==================== 스크롤바 ==================== */
QScrollBar:vertical {{
    background-color: {ModernTheme.COLORS['bg_primary']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {ModernTheme.COLORS['gray_light']};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {ModernTheme.COLORS['gray']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {ModernTheme.COLORS['bg_primary']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {ModernTheme.COLORS['gray_light']};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {ModernTheme.COLORS['gray']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ==================== 테이블 ==================== */
QTableWidget, QTableView {{
    background-color: {ModernTheme.COLORS['white']};
    alternate-background-color: {ModernTheme.COLORS['bg_primary']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 8px;
    gridline-color: {ModernTheme.COLORS['border_light']};
}}

QTableWidget::item, QTableView::item {{
    padding: 8px;
    border: none;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {ModernTheme.COLORS['primary_light']};
    color: {ModernTheme.COLORS['text_white']};
}}

QHeaderView::section {{
    background-color: {ModernTheme.COLORS['dark']};
    color: {ModernTheme.COLORS['text_white']};
    padding: 10px;
    border: none;
    font-weight: bold;
}}

/* ==================== 메뉴바 ==================== */
QMenuBar {{
    background-color: {ModernTheme.COLORS['white']};
    border-bottom: 1px solid {ModernTheme.COLORS['border']};
    padding: 5px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 8px 16px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {ModernTheme.COLORS['primary']};
    color: {ModernTheme.COLORS['text_white']};
}}

QMenu {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 8px;
    padding: 5px;
}}

QMenu::item {{
    padding: 8px 30px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {ModernTheme.COLORS['primary']};
    color: {ModernTheme.COLORS['text_white']};
}}

/* ==================== 상태바 ==================== */
QStatusBar {{
    background-color: {ModernTheme.COLORS['white']};
    border-top: 1px solid {ModernTheme.COLORS['border']};
    padding: 5px;
    color: {ModernTheme.COLORS['text_secondary']};
}}

/* ==================== 툴팁 ==================== */
QToolTip {{
    background-color: {ModernTheme.COLORS['dark']};
    color: {ModernTheme.COLORS['text_white']};
    border: none;
    border-radius: 6px;
    padding: 8px;
    font-size: 9pt;
}}

/* ==================== 스플리터 ==================== */
QSplitter::handle {{
    background-color: {ModernTheme.COLORS['border']};
    border-radius: 2px;
}}

QSplitter::handle:hover {{
    background-color: {ModernTheme.COLORS['primary']};
}}

QSplitter::handle:vertical {{
    height: 4px;
}}

QSplitter::handle:horizontal {{
    width: 4px;
}}

/* ==================== 다이얼로그 ==================== */
QDialog {{
    background-color: {ModernTheme.COLORS['bg_primary']};
}}

QMessageBox {{
    background-color: {ModernTheme.COLORS['white']};
}}

/* ==================== 프레임 ==================== */
QFrame {{
    background-color: {ModernTheme.COLORS['white']};
    border-radius: 8px;
}}

/* ==================== 리스트 위젯 ==================== */
QListWidget {{
    background-color: {ModernTheme.COLORS['white']};
    border: 2px solid {ModernTheme.COLORS['border']};
    border-radius: 8px;
    padding: 5px;
}}

QListWidget::item {{
    padding: 10px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {ModernTheme.COLORS['primary']};
    color: {ModernTheme.COLORS['text_white']};
}}

QListWidget::item:hover:!selected {{
    background-color: {ModernTheme.COLORS['light']};
}}

/* ==================== 라벨 ==================== */
QLabel {{
    background-color: transparent;
    color: {ModernTheme.COLORS['text_primary']};
}}
"""

    @staticmethod
    def apply_theme(app: QApplication):
        """애플리케이션에 테마 적용"""
        # 스타일시트 적용
        app.setStyle('Fusion')
        app.setStyleSheet(ModernTheme.get_stylesheet())

        # 팔레트 설정
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ModernTheme.COLORS['bg_primary']))
        palette.setColor(QPalette.WindowText, QColor(ModernTheme.COLORS['text_primary']))
        palette.setColor(QPalette.Base, QColor(ModernTheme.COLORS['white']))
        palette.setColor(QPalette.AlternateBase, QColor(ModernTheme.COLORS['light']))
        palette.setColor(QPalette.ToolTipBase, QColor(ModernTheme.COLORS['dark']))
        palette.setColor(QPalette.ToolTipText, QColor(ModernTheme.COLORS['text_white']))
        palette.setColor(QPalette.Text, QColor(ModernTheme.COLORS['text_primary']))
        palette.setColor(QPalette.Button, QColor(ModernTheme.COLORS['primary']))
        palette.setColor(QPalette.ButtonText, QColor(ModernTheme.COLORS['text_white']))
        palette.setColor(QPalette.Highlight, QColor(ModernTheme.COLORS['primary']))
        palette.setColor(QPalette.HighlightedText, QColor(ModernTheme.COLORS['text_white']))

        app.setPalette(palette)

        # 기본 폰트 설정
        font = QFont("맑은 고딕", 10)
        app.setFont(font)


# 추가 유틸리티 함수
def get_button_style(color_key='primary', size='normal'):
    """특정 스타일의 버튼 스타일 반환"""
    colors = {
        'primary': (ModernTheme.COLORS['primary'], ModernTheme.COLORS['primary_dark']),
        'success': (ModernTheme.COLORS['success'], ModernTheme.COLORS['success_dark']),
        'danger': (ModernTheme.COLORS['danger'], ModernTheme.COLORS['danger_dark']),
        'warning': (ModernTheme.COLORS['warning'], ModernTheme.COLORS['warning_dark']),
        'info': (ModernTheme.COLORS['info'], ModernTheme.COLORS['info_dark']),
        'secondary': (ModernTheme.COLORS['gray'], ModernTheme.COLORS['dark_light']),
    }

    sizes = {
        'small': ('8px 16px', '10pt', '28px'),
        'normal': ('10px 20px', '10pt', '36px'),
        'large': ('12px 24px', '11pt', '44px'),
    }

    color, color_dark = colors.get(color_key, colors['primary'])
    padding, font_size, min_height = sizes.get(size, sizes['normal'])

    return f"""
        QPushButton {{
            background-color: {color};
            color: white;
            border: none;
            border-radius: 6px;
            padding: {padding};
            font-weight: bold;
            font-size: {font_size};
            min-height: {min_height};
        }}
        QPushButton:hover {{
            background-color: {color_dark};
        }}
        QPushButton:pressed {{
            background-color: {color_dark};
            padding-top: {int(padding.split()[0].replace('px', '')) + 2}px;
        }}
        QPushButton:disabled {{
            background-color: {ModernTheme.COLORS['gray_light']};
            color: {ModernTheme.COLORS['text_secondary']};
        }}
    """


def get_card_style():
    """카드 스타일 반환"""
    return f"""
        QFrame {{
            background-color: {ModernTheme.COLORS['white']};
            border: 1px solid {ModernTheme.COLORS['border']};
            border-radius: 12px;
            padding: 20px;
        }}
    """
