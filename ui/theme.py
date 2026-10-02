"""Shared visual language for the desktop workspace."""


class ModernTheme:
    PRIMARY = "#2563eb"
    PRIMARY_DARK = "#1d4ed8"
    PRIMARY_LIGHT = "#eaf1ff"
    SUCCESS = "#0d9488"
    DANGER = "#dc2626"
    WARNING = "#d97706"
    BG_APP = "#f4f7fb"
    BG_PANEL = "#ffffff"
    BG_INPUT = "#ffffff"
    BG_HOVER = "#f3f6fb"
    TEXT_MAIN = "#14243d"
    TEXT_SUB = "#5b6b82"
    TEXT_MUTED = "#8a98ab"
    BORDER = "#dfe7f0"
    BORDER_FOCUS = PRIMARY

    @staticmethod
    def get_stylesheet() -> str:
        return """
        * { font-family: "Malgun Gothic", "Segoe UI", sans-serif; outline: none; }
        QMainWindow, QDialog { background: #f4f7fb; color: #14243d; }
        QWidget { color: #14243d; }

        QTabWidget#mainTabs { background: #f4f7fb; border: none; }
        QTabWidget#mainTabs > QTabBar::tab {
            background: #ffffff; color: #65758c; border: none;
            border-bottom: 3px solid transparent;
            padding: 13px 21px; margin-right: 1px;
            font-size: 12px; font-weight: 600; min-width: 92px;
        }
        QTabWidget#mainTabs > QTabBar::tab:selected {
            color: #2157c9; border-bottom: 3px solid #2563eb;
        }
        QTabWidget#mainTabs > QTabBar::tab:hover:!selected {
            color: #14243d; background: #f5f8fc;
        }
        QTabWidget#mainTabs::pane { border: none; background: #f4f7fb; }
        QTabWidget::pane {
            border: 1px solid #dfe7f0; border-radius: 8px;
            background: #ffffff;
        }
        QTabBar::tab {
            background: #f4f7fb; color: #65758c;
            border: 1px solid #dfe7f0; border-bottom: none;
            border-top-left-radius: 7px; border-top-right-radius: 7px;
            padding: 8px 16px; min-width: 70px; font-weight: 600;
        }
        QTabBar::tab:selected { background: #ffffff; color: #2157c9; }
        QTabBar::tab:hover:!selected { background: #eaf1ff; color: #2157c9; }

        QPushButton {
            background: #2563eb; color: #ffffff; border: 1px solid #2563eb;
            border-radius: 8px; padding: 6px 15px; min-height: 28px;
            font-size: 11px; font-weight: 600;
        }
        QPushButton:hover { background: #1d4ed8; border-color: #1d4ed8; }
        QPushButton:pressed { background: #1e40af; }
        QPushButton:disabled { background: #e8edf4; border-color: #e8edf4; color: #9aa6b6; }
        QPushButton[flat="true"] {
            background: #ffffff; border-color: #dfe7f0; color: #34455f;
        }
        QPushButton[flat="true"]:hover { background: #f3f6fb; border-color: #bdcce0; }

        QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QSpinBox, QComboBox {
            background: #ffffff; color: #14243d; border: 1px solid #d9e3ee;
            border-radius: 7px; padding: 5px 8px;
            selection-background-color: #2563eb; selection-color: #ffffff;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QTextBrowser:focus, QSpinBox:focus, QComboBox:focus { border-color: #2563eb; }
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background: #f3f6fb; color: #8a98ab;
        }
        QComboBox::drop-down { border: none; width: 22px; }
        QComboBox QAbstractItemView {
            background: #ffffff; color: #14243d; border: 1px solid #dfe7f0;
            selection-background-color: #eaf1ff; selection-color: #2157c9;
        }
        QCheckBox, QRadioButton { spacing: 7px; color: #34455f; }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 15px; height: 15px; background: #ffffff; border: 1px solid #bdcce0;
        }
        QCheckBox::indicator { border-radius: 4px; }
        QRadioButton::indicator { border-radius: 8px; }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background: #2563eb; border-color: #2563eb;
        }

        QGroupBox {
            background: #ffffff; border: 1px solid #dfe7f0; border-radius: 9px;
            margin-top: 15px; padding: 9px 8px 8px 8px; font-weight: 700;
        }
        QGroupBox::title {
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 12px; padding: 0 5px; background: #ffffff; color: #14243d;
        }
        QProgressBar {
            background: #e8edf4; border: none; border-radius: 4px;
            text-align: center; color: #14243d; height: 18px;
        }
        QProgressBar::chunk { background: #2563eb; border-radius: 4px; }
        QTableWidget, QTableView {
            background: #ffffff; alternate-background-color: #f8fafc;
            border: 1px solid #dfe7f0; border-radius: 7px;
            gridline-color: #e8edf4; selection-background-color: #eaf1ff;
            selection-color: #2157c9;
        }
        QTableWidget::item { padding: 5px 7px; }
        QHeaderView::section {
            background: #f2f5fa; color: #53657d; border: none;
            border-right: 1px solid #dfe7f0; border-bottom: 1px solid #dfe7f0;
            padding: 7px 9px; font-weight: 700;
        }
        QScrollBar:vertical { background: transparent; width: 9px; margin: 0; }
        QScrollBar::handle:vertical { background: #c5d0df; border-radius: 4px; min-height: 25px; }
        QScrollBar::handle:vertical:hover { background: #9cabc0; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { background: transparent; height: 9px; margin: 0; }
        QScrollBar::handle:horizontal { background: #c5d0df; border-radius: 4px; min-width: 25px; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        QMenuBar { background: #ffffff; color: #53657d; border-bottom: 1px solid #e7edf5; padding: 3px 8px; }
        QMenuBar::item { padding: 5px 11px; border-radius: 5px; }
        QMenuBar::item:selected { background: #eaf1ff; color: #2157c9; }
        QMenu { background: #ffffff; color: #14243d; border: 1px solid #dfe7f0; padding: 5px; }
        QMenu::item { padding: 7px 22px 7px 12px; border-radius: 5px; }
        QMenu::item:selected { background: #eaf1ff; color: #2157c9; }
        QMenu::separator { height: 1px; background: #dfe7f0; margin: 5px 8px; }
        QStatusBar { background: #ffffff; color: #65758c; border-top: 1px solid #e7edf5; padding: 2px 8px; }
        QToolTip { background: #14243d; color: #ffffff; border: none; padding: 5px 8px; }
        QSplitter::handle { background: #dfe7f0; }
        """
