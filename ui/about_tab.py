"""
About Tab - 컴팩트 디자인
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import webbrowser


class AboutTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #f8fafc; border: none; }")

        content = QWidget()
        content.setStyleSheet("background-color: #f8fafc;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 헤더
        header = self.create_header()
        layout.addWidget(header)

        # 개발자 정보
        dev_card = self.create_card(
            "👨‍💻 개발자 정보",
            [("김상준", "#1e293b", True), ("네트워크 엔지니어", "#64748b", False)]
        )
        layout.addWidget(dev_card)

        # 안내
        notice = self.create_notice()
        layout.addWidget(notice)

        # 최근 업데이트
        updates = self.create_updates()
        layout.addWidget(updates)

        # 기능
        features = self.create_features()
        layout.addWidget(features)

        # 연락처
        contact = self.create_contact()
        layout.addWidget(contact)

        layout.addStretch()
        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def create_header(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("네트워크 자동화 프로그램")
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #1e293b;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("차세대 네트워크 관리 솔루션")
        subtitle.setFont(QFont("맑은 고딕", 10))
        subtitle.setStyleSheet("color: #64748b;")
        subtitle.setAlignment(Qt.AlignCenter)

        version = QLabel("Version 7.0 • Build 2025.10.30")
        version.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        version.setStyleSheet("""
            background-color: #3b82f6;
            color: white;
            padding: 6px 16px;
            border-radius: 12px;
        """)
        version.setAlignment(Qt.AlignCenter)
        version.setMaximumWidth(280)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(version, 0, Qt.AlignCenter)

        return widget

    def create_card(self, title, items):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        title_label.setStyleSheet("color: #1e293b; border: none; padding: 0;")
        layout.addWidget(title_label)

        for text, color, bold in items:
            label = QLabel(text)
            font = QFont("맑은 고딕", 10, QFont.Bold if bold else QFont.Normal)
            label.setFont(font)
            label.setStyleSheet(f"color: {color}; border: none; padding: 0;")
            layout.addWidget(label)

        return card

    def create_notice(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        notice1 = QLabel(
            "ℹ️ 현재 Catalyst 계열의 로그 분석 기능을 제공합니다.\n"
            "Nexus 계열은 추후 업데이트를 통해 지원할 예정입니다."
        )
        notice1.setFont(QFont("맑은 고딕", 9))
        notice1.setStyleSheet("color: #1e40af; border: none; padding: 0;")
        notice1.setWordWrap(True)
        layout.addWidget(notice1)

        notice2 = QLabel(
            "💬 프로그램 이용 중 불편한 점이나 개선할 부분이 있다면\n"
            "언제든지 편하게 의견을 남겨주세요. 적극 반영하겠습니다."
        )
        notice2.setFont(QFont("맑은 고딕", 9))
        notice2.setStyleSheet("color: #1e40af; border: none; padding: 0;")
        notice2.setWordWrap(True)
        layout.addWidget(notice2)

        return card

    def create_updates(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f0fdf4;
                border: 2px solid #86efac;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        title = QLabel("🎉 Version 7.0 업데이트 (2025.10.30)")
        title.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        title.setStyleSheet("color: #15803d; border: none; padding: 0;")
        layout.addWidget(title)

        updates = [
            "✨ 보고서 탭 UI 전면 개선 - 3단계 섹션 구조",
            "✨ QMessageBox 스타일 개선 - 가운데 정렬 및 크기 최적화",
            "✨ 패스워드 입력 공백 인식 기능 추가",
            "✨ 빠른 체크 기능 추가 - IP 연결 사전 확인",
            "✨ 실행 상태 실시간 표시 패널 추가",
            "✨ 탭 위치 개선 - 서브탭 상단 배치"
        ]

        for update in updates:
            label = QLabel(update)
            label.setFont(QFont("맑은 고딕", 9))
            label.setStyleSheet("color: #166534; border: none; padding: 2px 0;")
            layout.addWidget(label)

        return card

    def create_features(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        title = QLabel("💡 주요 기능")
        title.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        title.setStyleSheet("color: #1e293b; border: none; padding: 0;")
        layout.addWidget(title)

        features = [
            "📁 구성 백업 및 버전 관리",
            "💻 CPU, 메모리, 업타임 수집 및 분석",
            "📊 Excel 네트워크 상태 리포트 생성",
            "🔗 SSH/Telnet 일괄 작업 및 명령어 실행"
        ]

        for feature in features:
            label = QLabel(feature)
            label.setFont(QFont("맑은 고딕", 10))
            label.setStyleSheet("color: #475569; border: none; padding: 2px 0;")
            layout.addWidget(label)

        return card

    def create_contact(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("📞 연락처 010-2884-8765")
        title.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        title.setStyleSheet("color: #1e293b; border: none; padding: 0;")
        layout.addWidget(title)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        email_btn = QPushButton("📧 이메일 문의")
        email_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        email_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        email_btn.setCursor(Qt.PointingHandCursor)
        email_btn.clicked.connect(lambda: webbrowser.open("mailto:doaslove962@gmail.com"))

        web_btn = QPushButton("🌐 웹사이트")
        web_btn.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        web_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        web_btn.setCursor(Qt.PointingHandCursor)
        web_btn.clicked.connect(lambda: webbrowser.open("https://auto-network.co.kr"))

        button_layout.addWidget(email_btn)
        button_layout.addWidget(web_btn)
        layout.addLayout(button_layout)

        license_text = QLabel(
            "이 프로그램은 MIT 라이선스 하에 배포됩니다.\n"
            "문제 발생 시 언제든지 연락주세요! 🚀"
        )
        license_text.setFont(QFont("맑은 고딕", 9))
        license_text.setStyleSheet("color: #64748b; border: none; padding: 0;")
        license_text.setAlignment(Qt.AlignCenter)
        license_text.setWordWrap(True)
        layout.addWidget(license_text)

        return card
