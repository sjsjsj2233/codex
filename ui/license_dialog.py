"""
라이센스 활성화 다이얼로그

앱 최초 실행 시 또는 라이센스가 없을 때 표시됩니다.
"""

import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

from core.license_manager import LicenseManager

CONTACT_EMAIL = "doaslove962@gmail.com"


# ── 활성화 워커 (UI 블로킹 방지) ─────────────────────────────────
class ActivateWorker(QThread):
    done = pyqtSignal(bool, str)   # 성공여부, 메시지

    def __init__(self, manager: LicenseManager, key: str):
        super().__init__()
        self.manager = manager
        self.key     = key

    def run(self):
        ok, msg = self.manager.activate(self.key)
        self.done.emit(ok, msg)


# ── 라이센스 다이얼로그 ─────────────────────────────────────────
class LicenseDialog(QDialog):

    def __init__(self, manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.worker  = None

        self.setWindowTitle("Network Automation — 라이센스 활성화")
        self.setFixedSize(480, 420)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self._build_ui()
        self._apply_style()

    # ── UI 구성 ──────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 상단 헤더 ──
        header = QFrame()
        header.setObjectName("licHeader")
        header.setFixedHeight(110)
        h_lay = QVBoxLayout(header)
        h_lay.setAlignment(Qt.AlignCenter)
        h_lay.setSpacing(4)

        app_lbl = QLabel("Network Automation")
        app_lbl.setAlignment(Qt.AlignCenter)
        app_lbl.setObjectName("appTitle")

        ver_lbl = QLabel("v8.0  —  라이센스 활성화")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setObjectName("appSub")

        h_lay.addWidget(app_lbl)
        h_lay.addWidget(ver_lbl)
        root.addWidget(header)

        # ── 본문 ──
        body = QFrame()
        body.setObjectName("licBody")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(40, 28, 40, 28)
        b_lay.setSpacing(16)

        # 안내 문구
        guide = QLabel(
            "30일 무료 체험 기간이 종료되었습니다.\n"
            "라이센스키 발급은 이메일로 문의해주세요.\n"
            f"({CONTACT_EMAIL})"
        )
        guide.setWordWrap(True)
        guide.setAlignment(Qt.AlignCenter)
        guide.setObjectName("guideText")
        b_lay.addWidget(guide)

        # 라이센스키 입력
        key_lbl = QLabel("라이센스키")
        key_lbl.setObjectName("fieldLabel")
        b_lay.addWidget(key_lbl)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("ANTA-XXXX-XXXX-XXXX")
        self.key_input.setMaxLength(19)
        self.key_input.setObjectName("keyInput")
        self.key_input.setFixedHeight(38)
        self.key_input.textChanged.connect(self._auto_format)
        self.key_input.returnPressed.connect(self._on_activate)
        b_lay.addWidget(self.key_input)

        # 기기 ID (지원 문의 시 필요)
        machine_id = self.manager.get_machine_id()
        mid_row = QHBoxLayout()
        mid_lbl = QLabel("기기 ID:")
        mid_lbl.setObjectName("midLabel")
        mid_val = QLabel(machine_id)
        mid_val.setObjectName("midValue")
        mid_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mid_row.addWidget(mid_lbl)
        mid_row.addWidget(mid_val)
        mid_row.addStretch()
        b_lay.addLayout(mid_row)

        # 상태 메시지
        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setMinimumHeight(36)
        b_lay.addWidget(self.status_lbl)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.purchase_btn = QPushButton("📧  이메일로 신청")
        self.purchase_btn.setObjectName("purchaseBtn")
        self.purchase_btn.setFixedHeight(36)
        self.purchase_btn.clicked.connect(self._on_purchase)

        self.activate_btn = QPushButton("활성화")
        self.activate_btn.setObjectName("activateBtn")
        self.activate_btn.setFixedHeight(36)
        self.activate_btn.setMinimumWidth(100)
        self.activate_btn.clicked.connect(self._on_activate)

        btn_row.addWidget(self.purchase_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.activate_btn)
        b_lay.addLayout(btn_row)

        root.addWidget(body)

        # ── 하단 푸터 ──
        footer = QLabel(
            f"라이센스 문의 · 기기 변경:  {CONTACT_EMAIL}"
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName("footerText")
        footer.setFixedHeight(30)
        root.addWidget(footer)

    def _apply_style(self):
        self.setStyleSheet("""
            /* 전체 배경 */
            QDialog {
                background-color: #f1f5f9;
            }

            /* 헤더 */
            QFrame#licHeader {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563eb, stop:1 #1d4ed8
                );
                border: none;
            }
            QLabel#appTitle {
                color: white;
                font-size: 18px;
                font-weight: 700;
                font-family: "맑은 고딕";
                background: transparent;
            }
            QLabel#appSub {
                color: #bfdbfe;
                font-size: 11px;
                font-family: "맑은 고딕";
                background: transparent;
            }

            /* 본문 */
            QFrame#licBody {
                background-color: #ffffff;
                border: none;
            }
            QLabel#guideText {
                color: #475569;
                font-size: 11px;
                font-family: "맑은 고딕";
                line-height: 1.6;
            }
            QLabel#fieldLabel {
                color: #1e293b;
                font-size: 11px;
                font-weight: 700;
                font-family: "맑은 고딕";
            }

            /* 키 입력 필드 */
            QLineEdit#keyInput {
                background: #f8fafc;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 0 12px;
                font-family: "Consolas", monospace;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 1px;
                color: #1e293b;
            }
            QLineEdit#keyInput:focus {
                border-color: #3b82f6;
                background: #eff6ff;
            }

            /* 기기 ID */
            QLabel#midLabel {
                color: #94a3b8;
                font-size: 10px;
                font-family: "맑은 고딕";
            }
            QLabel#midValue {
                color: #64748b;
                font-size: 10px;
                font-family: "Consolas", monospace;
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 3px;
                padding: 1px 6px;
            }

            /* 상태 메시지 — JS 없이 objectName으로 색상 제어 */
            QLabel#statusLabel {
                font-size: 11px;
                font-family: "맑은 고딕";
                padding: 6px 0;
                color: #64748b;
            }

            /* 구매 버튼 */
            QPushButton#purchaseBtn {
                background-color: #f1f5f9;
                color: #475569;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                font-family: "맑은 고딕";
                padding: 0 14px;
            }
            QPushButton#purchaseBtn:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }

            /* 활성화 버튼 */
            QPushButton#activateBtn {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                font-family: "맑은 고딕";
                padding: 0 20px;
            }
            QPushButton#activateBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#activateBtn:pressed {
                background-color: #1e40af;
            }
            QPushButton#activateBtn:disabled {
                background-color: #93c5fd;
            }

            /* 푸터 */
            QLabel#footerText {
                color: #94a3b8;
                font-size: 10px;
                font-family: "맑은 고딕";
                background: #f8fafc;
                border-top: 1px solid #e2e8f0;
            }
        """)

    # ── 이벤트 핸들러 ────────────────────────────────────────────

    def _auto_format(self, text: str):
        """입력하면서 자동으로 ANTA-XXXX-XXXX-XXXX 형태로 포맷"""
        # 하이픈 제거 후 대문자 변환
        clean = text.replace("-", "").upper()
        # 4자리마다 하이픈 삽입
        parts = [clean[i:i+4] for i in range(0, len(clean), 4)]
        formatted = "-".join(parts)
        if formatted != text:
            self.key_input.blockSignals(True)
            self.key_input.setText(formatted)
            self.key_input.setCursorPosition(len(formatted))
            self.key_input.blockSignals(False)

    def _on_purchase(self):
        webbrowser.open(f"mailto:{CONTACT_EMAIL}?subject=Network Automation 라이센스 신청")

    def _on_activate(self):
        key = self.key_input.text().strip()
        if not key:
            self._show_error("라이센스키를 입력해주세요.")
            return

        self._set_loading(True)
        self._show_info("서버에 연결 중...")

        self.worker = ActivateWorker(self.manager, key)
        self.worker.done.connect(self._on_activate_done)
        self.worker.start()

    def _on_activate_done(self, ok: bool, msg: str):
        self._set_loading(False)
        if ok:
            self._show_success(msg)
            # 1.2초 후 자동으로 다이얼로그 닫기 (성공)
            QTimer.singleShot(1200, self.accept)
        else:
            self._show_error(msg)

    def _set_loading(self, loading: bool):
        self.activate_btn.setEnabled(not loading)
        self.key_input.setEnabled(not loading)
        self.activate_btn.setText("확인 중…" if loading else "활성화")

    # ── 상태 메시지 표시 ─────────────────────────────────────────

    def _show_success(self, msg: str):
        self.status_lbl.setText(f"✅  {msg.splitlines()[0]}")
        self.status_lbl.setStyleSheet(
            "color: #15803d; font-weight: 700; font-size: 11px;"
            "background: #f0fdf4; border-radius: 4px; padding: 6px;"
        )

    def _show_error(self, msg: str):
        # 줄바꿈을 공백으로 (한 줄 표시)
        short = msg.splitlines()[0]
        self.status_lbl.setText(f"❌  {short}")
        self.status_lbl.setStyleSheet(
            "color: #b91c1c; font-size: 11px;"
            "background: #fef2f2; border-radius: 4px; padding: 6px;"
        )
        # 툴팁에 전체 메시지
        self.status_lbl.setToolTip(msg)

    def _show_info(self, msg: str):
        self.status_lbl.setText(f"⏳  {msg}")
        self.status_lbl.setStyleSheet(
            "color: #1d4ed8; font-size: 11px;"
            "background: #eff6ff; border-radius: 4px; padding: 6px;"
        )
