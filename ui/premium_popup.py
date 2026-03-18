"""
유료 기능 안내 팝업
"""
import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush, QPen


class _Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor('#0f172a'))
        g.setColorAt(1.0, QColor('#7c2d12'))
        p.fillRect(self.rect(), QBrush(g))
        p.setOpacity(0.08)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 80, -30, 140, 140)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor('#ffffff')))
        p.setFont(QFont('맑은 고딕', 22))
        p.drawText(22, 54, '🔒')
        p.setFont(QFont('맑은 고딕', 13, QFont.Bold))
        p.drawText(62, 45, 'Pro 유료 기능')
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(63, 65, 'Network Automation  —  라이센스 필요')
        p.end()


class PremiumPopup(QDialog):
    """
    사용법:
        PremiumPopup(parent, feature='로그 분석').exec_()
    """
    def __init__(self, parent=None, feature: str = '이 기능'):
        super().__init__(parent)
        self.setWindowTitle('유료 기능 안내')
        self.setFixedWidth(420)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet('QDialog{background:#f8fafc}')
        self._feature = feature
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_Header())

        body = QWidget()
        body.setStyleSheet('background:#f8fafc')
        bv = QVBoxLayout(body)
        bv.setContentsMargins(28, 22, 28, 24)
        bv.setSpacing(14)

        # 기능명 강조
        feat_lbl = QLabel(f'「 {self._feature} 」')
        feat_lbl.setFont(QFont('맑은 고딕', 12, QFont.Bold))
        feat_lbl.setStyleSheet('color:#ea580c;background:transparent')
        feat_lbl.setAlignment(Qt.AlignCenter)
        bv.addWidget(feat_lbl)

        # 설명
        desc = QLabel(
            '이 기능은 <b>Pro 라이센스</b>가 있어야 사용할 수 있습니다.<br><br>'
            '라이센스를 구매하시면 아래 기능들을 모두 이용하실 수 있습니다.<br>'
            '<ul style="margin:6px 0 0 0; padding-left:18px; line-height:1.8">'
            '<li>네트워크 점검 보고서 (PDF / Word / Excel)</li>'
            '<li>설정 비교 (Config Diff)</li>'
            '<li>로그 분석</li>'
            '<li>시리얼 (COM) 콘솔 접속</li>'
            '</ul>'
        )
        desc.setFont(QFont('맑은 고딕', 9))
        desc.setStyleSheet(
            'color:#334155;background:#fff;border:1px solid #e2e8f0;'
            'border-radius:8px;padding:12px 14px'
        )
        desc.setWordWrap(True)
        bv.addWidget(desc)

        # 문의 안내
        contact = QLabel('라이센스 문의 :  <b>doaslove962@gmail.com</b>')
        contact.setFont(QFont('맑은 고딕', 9))
        contact.setStyleSheet('color:#475569;background:transparent')
        contact.setAlignment(Qt.AlignCenter)
        bv.addWidget(contact)

        # 버튼
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        buy_btn = QPushButton('🛒  지금 구매하기')
        buy_btn.setFixedHeight(36)
        buy_btn.setFont(QFont('맑은 고딕', 9, QFont.Bold))
        buy_btn.setCursor(Qt.PointingHandCursor)
        buy_btn.setStyleSheet(
            'QPushButton{background:#16a34a;color:#fff;border:none;'
            'border-radius:7px;padding:0 18px}'
            'QPushButton:hover{background:#15803d}'
        )
        buy_btn.clicked.connect(
            lambda: webbrowser.open('https://doaslove.gumroad.com/l/gxkxv')
        )

        email_btn = QPushButton('📧  문의')
        email_btn.setFixedHeight(36)
        email_btn.setFont(QFont('맑은 고딕', 9))
        email_btn.setCursor(Qt.PointingHandCursor)
        email_btn.setStyleSheet(
            'QPushButton{background:#2563eb;color:#fff;border:none;'
            'border-radius:7px;padding:0 18px}'
            'QPushButton:hover{background:#1d4ed8}'
        )
        email_btn.clicked.connect(
            lambda: webbrowser.open('mailto:doaslove962@gmail.com'
                                    '?subject=Network Automation 라이센스 문의')
        )

        close_btn = QPushButton('닫기')
        close_btn.setFixedHeight(36)
        close_btn.setFont(QFont('맑은 고딕', 9))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            'QPushButton{background:#f1f5f9;color:#64748b;border:1.5px solid #cbd5e1;'
            'border-radius:7px;padding:0 18px}'
            'QPushButton:hover{background:#e2e8f0}'
        )
        close_btn.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(buy_btn)
        btn_row.addWidget(email_btn)
        btn_row.addWidget(close_btn)
        bv.addLayout(btn_row)

        root.addWidget(body)
