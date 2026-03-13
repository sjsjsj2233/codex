from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter, QLinearGradient, QColor, QPalette
from datetime import datetime
import webbrowser

class ModernCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 0px;
            }
        """)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def enterEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border-radius: 16px;
                padding: 0px;
            }
        """)

    def leaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 0px;
            }
        """)


class StylishButton(QPushButton):
    def __init__(self, text, color="#007bff", parent=None):
        super().__init__(text, parent)
        self.color = color
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 0.2)};
            }}
        """)
        
    def _darken_color(self, color, factor=0.1):
        # 간단한 색상 어둡게 만들기
        if color == "#007bff":
            return "#0056b3" if factor == 0.1 else "#004085"
        elif color == "#28a745":
            return "#1e7e34" if factor == 0.1 else "#155724"
        elif color == "#dc3545":
            return "#c82333" if factor == 0.1 else "#bd2130"
        return color

class AboutTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        
    def init_ui(self):
        # 메인 스크롤 영역
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 연한 배경색 지정
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #f5f5f5;
            }
        """)
        
        # 스크롤 내용 위젯
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(40, 40, 40, 40)
        scroll_layout.setSpacing(30)
        
        # 헤더 카드
        header_card = self.create_header_card()
        scroll_layout.addWidget(header_card)
        
        # 개발자 정보 카드만 남김
        dev_card = self.create_developer_card()
        scroll_layout.addWidget(dev_card)
        
        # 주요 기능 카드
        features_card = self.create_features_card()
        scroll_layout.addWidget(features_card)
        
        # 연락처 카드
        contact_card = self.create_contact_card()
        scroll_layout.addWidget(contact_card)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        
    def create_header_card(self):
        card = ModernCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)
        
        # 제목과 부제목
        title_layout = QVBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("네트워크 자동화 프로그램")
        title.setFont(QFont("맑은 고딕", 28, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin: 0;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("차세대 네트워크 관리 솔루션")
        subtitle.setFont(QFont("맑은 고딕", 14))
        subtitle.setStyleSheet("color: #6c757d; margin-top: 5px;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        
        # 버전 정보
        today = datetime.now().strftime("%Y.%m.%d")
        version_layout = QHBoxLayout()
        version_layout.addStretch()
        
        version_label = QLabel(f"Version 4.0 • Build {today}")
        version_label.setFont(QFont("맑은 고딕", 12))
        version_label.setStyleSheet("""
            color: white;
            background-color: #007bff;
            padding: 8px 16px;
            border-radius: 15px;
            font-weight: bold;
        """)
        
        version_layout.addWidget(version_label)
        version_layout.addStretch()
        
        layout.addLayout(version_layout)
        
        return card
        
    def create_developer_card(self):
        card = ModernCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(8)

        # 카드 제목
        title = QLabel("👨‍💻 개발자 정보")
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        layout.addWidget(title)

        # 개발자 이름
        name = QLabel("김상준")
        name.setFont(QFont("맑은 고딕", 16, QFont.Bold))
        name.setStyleSheet("color: #495057;")
        layout.addWidget(name)

        # 직책
        position = QLabel("네트워크 엔지니어")
        position.setFont(QFont("맑은 고딕", 12))
        position.setStyleSheet("color: #6c757d;")
        layout.addWidget(position)

        # 추가 안내 메시지
        note = QLabel(
            "ℹ️ 현재 Catalyst 계열의 로그 분석 기능을 제공합니다.\n"
            "Nexus 계열은 추후 업데이트를 통해 지원할 예정입니다."
        )
        note.setFont(QFont("맑은 고딕", 10))
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #555555; background-color: #f1f1f1; padding: 8px; border-radius: 6px;"
        )
        layout.addWidget(note)

        # 추가 안내 메시지 2
        contact_note = QLabel(
            "💬 프로그램 이용 중 불편한 점이나 개선할 부분이 있다면\n"
            "언제든지 편하게 의견을 남겨주세요. 적극 반영하겠습니다."
        )
        contact_note.setFont(QFont("맑은 고딕", 10))
        contact_note.setWordWrap(True)
        contact_note.setStyleSheet(
            "color: #555555; background-color: #f1f1f1; padding: 8px; border-radius: 6px;"
        )
        layout.addWidget(contact_note)

        layout.addStretch()
        return card


        
    def create_stats_card(self):
        card = ModernCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # 카드 제목
        title = QLabel("📊 프로젝트 통계")
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)

        # 새로운 통계 정보
        stats = [
            ("코드 라인 수", "12,450+"),    # 유지
            ("지원 벤더 수", "5+"),         # 새 항목
            ("지원 명령어 수", "30+"),      # 새 항목
            ("빌드 수", "42")             # 새 항목
        ]

        for label, value in stats:
            stat_layout = QHBoxLayout()

            label_widget = QLabel(label)
            label_widget.setFont(QFont("맑은 고딕", 11))
            label_widget.setStyleSheet("color: #6c757d;")

            value_widget = QLabel(value)
            value_widget.setFont(QFont("맑은 고딕", 11, QFont.Bold))
            value_widget.setStyleSheet("color: #007bff;")
            value_widget.setAlignment(Qt.AlignRight)

            stat_layout.addWidget(label_widget)
            stat_layout.addStretch()
            stat_layout.addWidget(value_widget)

            layout.addLayout(stat_layout)

        layout.addStretch()

        return card

        
    def create_features_card(self):
        card = ModernCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)

        title = QLabel("✨ 주요 기능")
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)

        # 주요 기능들
        features = [
            "📂 구성 백업 및 버전 관리",
            "🧮 CPU, 메모리, 업타임 수집 및 분석",
            "📊 Excel 네트워크 상태 리포트 생성",
            "🛠️ SSH/Telnet 일괄 작업 및 명령어 실행",
        ]
        features_text = "   ".join(features)  # 한 줄로 이어붙임

        features_label = QLabel(features_text)
        features_label.setFont(QFont("맑은 고딕", 12))
        features_label.setStyleSheet("color: #495057; padding: 5px 0;")
        features_label.setWordWrap(True)  # 너무 길 경우 줄 바꿈
        layout.addWidget(features_label)

        return card


        
    def create_contact_card(self):
        card = ModernCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)
        
        # 카드 제목
        title = QLabel("📬 연락처 010-2884-8765")
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 이메일 버튼
        email_btn = StylishButton("📧 이메일 문의", "#007bff")
        email_btn.clicked.connect(lambda: webbrowser.open("mailto:doaslove962@gmail.com"))
        
        # 웹사이트 버튼
        website_btn = StylishButton("🌐 웹사이트", "#28a745")
        website_btn.clicked.connect(lambda: webbrowser.open("https://auto-network.co.kr"))
        
        button_layout.addWidget(email_btn)
        button_layout.addWidget(website_btn)
        
        layout.addLayout(button_layout)
        
        # 추가 정보
        info_text = QLabel("이 프로그램은 MIT 라이선스 하에 배포됩니다.\n문제 발생 시 언제든지 연락주세요! 🚀")
        info_text.setFont(QFont("맑은 고딕", 11))
        info_text.setStyleSheet("color: #6c757d; margin-top: 10px;")
        info_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_text)
        
        return card