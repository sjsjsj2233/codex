"""
온보딩 다이얼로그 — 이메일 입력 → 결제 → 완료
앱 최초 실행 또는 라이센스 없을 때 표시
"""

import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QStackedWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QRegExpValidator
from PyQt5.QtCore import QRegExp

from core.license_manager import LicenseManager, SERVER_URL

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

PURCHASE_URL = "https://auto-network.co.kr"


# ── 백그라운드 워커들 ─────────────────────────────────────────────

class CheckWorker(QThread):
    """이메일 상태 확인"""
    done = pyqtSignal(str, str)   # status, token(있으면)

    def __init__(self, email, machine_id):
        super().__init__()
        self.email = email
        self.machine_id = machine_id

    def run(self):
        if not REQUESTS_OK:
            self.done.emit("error_no_requests", "")
            return
        try:
            r = requests.post(
                f"{SERVER_URL}/user/status",
                json={"email": self.email, "machine_id": self.machine_id},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                self.done.emit(data.get("status", "error"),
                               data.get("token", ""))
            else:
                self.done.emit("server_error", "")
        except requests.exceptions.ConnectionError:
            self.done.emit("conn_error", "")
        except Exception:
            self.done.emit("error", "")


class PayWorker(QThread):
    """임시 결제 처리"""
    done = pyqtSignal(bool, str, str)   # 성공, token, message

    def __init__(self, email, machine_id):
        super().__init__()
        self.email = email
        self.machine_id = machine_id

    def run(self):
        if not REQUESTS_OK:
            self.done.emit(False, "", "requests 모듈이 없습니다.")
            return
        try:
            r = requests.post(
                f"{SERVER_URL}/payment/temp",
                json={"email": self.email, "machine_id": self.machine_id},
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                self.done.emit(True, data.get("token", ""), "결제 완료")
            elif r.status_code == 409:
                self.done.emit(False, "",
                               "이미 다른 기기에서 활성화된 계정입니다.\n"
                               "기기 변경은 고객센터로 문의해주세요.")
            else:
                self.done.emit(False, "", f"서버 오류 ({r.status_code})")
        except requests.exceptions.ConnectionError:
            self.done.emit(False, "",
                           "서버에 연결할 수 없습니다.\n인터넷 연결을 확인해주세요.")
        except Exception as e:
            self.done.emit(False, "", str(e))


# ── 공통 헤더 ────────────────────────────────────────────────────

def _header(subtitle: str) -> QFrame:
    f = QFrame()
    f.setObjectName("obHeader")
    f.setFixedHeight(100)
    lay = QVBoxLayout(f)
    lay.setAlignment(Qt.AlignCenter)
    lay.setSpacing(4)

    t = QLabel("Network Automation")
    t.setAlignment(Qt.AlignCenter)
    t.setObjectName("obTitle")

    s = QLabel(subtitle)
    s.setAlignment(Qt.AlignCenter)
    s.setObjectName("obSub")

    lay.addWidget(t)
    lay.addWidget(s)
    return f


# ── 페이지 0 : 이메일 입력 ────────────────────────────────────────

class EmailPage(QWidget):
    go_next    = pyqtSignal(str)   # email
    go_done    = pyqtSignal(str)   # token (이미 결제한 경우)
    show_error = pyqtSignal(str)

    def __init__(self, manager: LicenseManager):
        super().__init__()
        self.manager = manager
        self.worker  = None
        _lay = QVBoxLayout(self)
        _lay.setContentsMargins(0, 0, 0, 0)
        _lay.setSpacing(0)

        _lay.addWidget(_header("시작하기"))

        body = QFrame()
        body.setObjectName("obBody")
        b = QVBoxLayout(body)
        b.setContentsMargins(40, 30, 40, 30)
        b.setSpacing(14)

        desc = QLabel(
            "이메일을 입력하면 구매 여부를 확인합니다.\n"
            "처음 사용하시는 경우 결제 화면으로 이동합니다."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setObjectName("obDesc")
        b.addWidget(desc)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setObjectName("obInput")
        self.email_input.setFixedHeight(38)
        self.email_input.returnPressed.connect(self._next)
        b.addWidget(self.email_input)

        self.status = QLabel("")
        self.status.setObjectName("obStatus")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setMinimumHeight(28)
        b.addWidget(self.status)

        self.next_btn = QPushButton("다음  →")
        self.next_btn.setObjectName("obPrimary")
        self.next_btn.setFixedHeight(38)
        self.next_btn.clicked.connect(self._next)
        b.addWidget(self.next_btn)

        _lay.addWidget(body)

        footer = QLabel("이미 라이센스키가 있으신가요?  "
                        "<a href='#key'>라이센스키 직접 입력</a>")
        footer.setTextInteractionFlags(Qt.TextBrowserInteraction)
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName("obFooter")
        footer.setFixedHeight(30)
        footer.linkActivated.connect(lambda _: self.show_error.emit("__show_key__"))
        _lay.addWidget(footer)

    def _next(self):
        email = self.email_input.text().strip().lower()
        if "@" not in email or "." not in email:
            self._set_status("올바른 이메일을 입력해주세요.", error=True)
            return

        self._loading(True)
        machine_id = self.manager.get_machine_id()
        self.worker = CheckWorker(email, machine_id)
        self.worker.done.connect(lambda s, t: self._on_check(s, t, email))
        self.worker.start()

    def _on_check(self, status, token, email):
        self._loading(False)
        if status == "active":
            self._set_status("구매 확인 완료!", error=False)
            self.go_done.emit(token)
        elif status == "not_paid":
            self.go_next.emit(email)
        elif status == "already_activated":
            self._set_status(
                "이미 다른 기기에서 활성화된 계정입니다.\n"
                "기기 변경은 doaslove962@gmail.com 로 문의해주세요.",
                error=True
            )
        elif status == "conn_error":
            self._set_status("서버에 연결할 수 없습니다. 인터넷을 확인해주세요.", error=True)
        else:
            self._set_status("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", error=True)

    def _loading(self, on: bool):
        self.next_btn.setEnabled(not on)
        self.email_input.setEnabled(not on)
        self.next_btn.setText("확인 중…" if on else "다음  →")
        if on:
            self._set_status("서버 확인 중…", error=False, info=True)

    def _set_status(self, msg, error=False, info=False):
        self.status.setText(msg)
        if error:
            self.status.setStyleSheet(
                "color:#b91c1c; background:#fef2f2; border-radius:4px; padding:4px 8px; font-size:10px;")
        elif info:
            self.status.setStyleSheet(
                "color:#1d4ed8; background:#eff6ff; border-radius:4px; padding:4px 8px; font-size:10px;")
        else:
            self.status.setStyleSheet(
                "color:#15803d; background:#f0fdf4; border-radius:4px; padding:4px 8px; font-size:10px;")


# ── 페이지 1 : 결제 ──────────────────────────────────────────────

class PaymentPage(QWidget):
    go_done    = pyqtSignal(str)   # token
    go_back    = pyqtSignal()
    show_error = pyqtSignal(str)

    def __init__(self, manager: LicenseManager):
        super().__init__()
        self.manager = manager
        self.email   = ""
        self.worker  = None
        _lay = QVBoxLayout(self)
        _lay.setContentsMargins(0, 0, 0, 0)
        _lay.setSpacing(0)

        _lay.addWidget(_header("결제"))

        body = QFrame()
        body.setObjectName("obBody")
        b = QVBoxLayout(body)
        b.setContentsMargins(40, 24, 40, 24)
        b.setSpacing(12)

        # 상품 카드
        card = QFrame()
        card.setObjectName("productCard")
        c = QVBoxLayout(card)
        c.setContentsMargins(16, 14, 16, 14)
        c.setSpacing(6)

        prod_name = QLabel("Network Automation v6.1")
        prod_name.setObjectName("prodName")
        prod_desc = QLabel("Cisco 네트워크 장비 자동화 · 설정 비교 · 로그 분석\n평생 라이센스 (1기기)")
        prod_desc.setObjectName("prodDesc")
        prod_desc.setWordWrap(True)
        self.price_lbl = QLabel("₩ 1,000")
        self.price_lbl.setObjectName("prodPrice")
        self.price_lbl.setAlignment(Qt.AlignRight)

        c.addWidget(prod_name)
        c.addWidget(prod_desc)
        c.addWidget(self.price_lbl)
        b.addWidget(card)

        # 이메일 확인 표시
        self.email_lbl = QLabel("")
        self.email_lbl.setObjectName("emailConfirm")
        self.email_lbl.setAlignment(Qt.AlignCenter)
        b.addWidget(self.email_lbl)

        # 임시 결제 안내
        notice = QLabel("⚠  현재 테스트 모드 — 실제 결제가 발생하지 않습니다.")
        notice.setObjectName("noticeText")
        notice.setAlignment(Qt.AlignCenter)
        b.addWidget(notice)

        self.status = QLabel("")
        self.status.setObjectName("obStatus")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setMinimumHeight(28)
        self.status.setWordWrap(True)
        b.addWidget(self.status)

        # 버튼 행
        btn_row = QHBoxLayout()
        back_btn = QPushButton("← 뒤로")
        back_btn.setObjectName("obSecondary")
        back_btn.setFixedHeight(36)
        back_btn.clicked.connect(self.go_back.emit)

        self.pay_btn = QPushButton("결제하기  ₩1,000")
        self.pay_btn.setObjectName("obPrimary")
        self.pay_btn.setFixedHeight(36)
        self.pay_btn.setMinimumWidth(140)
        self.pay_btn.clicked.connect(self._pay)

        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.pay_btn)
        b.addLayout(btn_row)

        _lay.addWidget(body)

        footer = QLabel("결제 문의:  doaslove962@gmail.com")
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName("obFooter")
        footer.setFixedHeight(30)
        _lay.addWidget(footer)

    def set_email(self, email: str):
        self.email = email
        self.email_lbl.setText(f"구매자 이메일:  {email}")

    def _pay(self):
        if not self.email:
            return
        self._loading(True)
        machine_id = self.manager.get_machine_id()
        self.worker = PayWorker(self.email, machine_id)
        self.worker.done.connect(self._on_pay_done)
        self.worker.start()

    def _on_pay_done(self, ok, token, msg):
        self._loading(False)
        if ok:
            self._set_status("결제 완료!", error=False)
            QTimer.singleShot(800, lambda: self.go_done.emit(token))
        else:
            self._set_status(msg, error=True)

    def _loading(self, on: bool):
        self.pay_btn.setEnabled(not on)
        self.pay_btn.setText("처리 중…" if on else "결제하기  ₩1,000")
        if on:
            self._set_status("결제 처리 중…", error=False, info=True)

    def _set_status(self, msg, error=False, info=False):
        self.status.setText(msg)
        if error:
            self.status.setStyleSheet(
                "color:#b91c1c; background:#fef2f2; border-radius:4px; padding:4px 8px; font-size:10px;")
        elif info:
            self.status.setStyleSheet(
                "color:#1d4ed8; background:#eff6ff; border-radius:4px; padding:4px 8px; font-size:10px;")
        else:
            self.status.setStyleSheet(
                "color:#15803d; background:#f0fdf4; border-radius:4px; padding:4px 8px; font-size:10px;")


# ── 페이지 2 : 완료 ──────────────────────────────────────────────

class DonePage(QWidget):
    def __init__(self):
        super().__init__()
        _lay = QVBoxLayout(self)
        _lay.setContentsMargins(0, 0, 0, 0)
        _lay.setSpacing(0)
        _lay.addWidget(_header("활성화 완료"))

        body = QFrame()
        body.setObjectName("obBody")
        b = QVBoxLayout(body)
        b.setContentsMargins(40, 40, 40, 40)
        b.setSpacing(16)
        b.setAlignment(Qt.AlignCenter)

        icon = QLabel("✅")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:48px; background:transparent;")
        b.addWidget(icon)

        msg = QLabel("라이센스가 활성화되었습니다!\n잠시 후 프로그램이 시작됩니다.")
        msg.setAlignment(Qt.AlignCenter)
        msg.setObjectName("doneMsg")
        b.addWidget(msg)

        _lay.addWidget(body)


# ── 메인 온보딩 다이얼로그 ────────────────────────────────────────

class OnboardingDialog(QDialog):
    """이메일 입력 → 결제 → 완료 3단계 다이얼로그"""

    def __init__(self, manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.manager = manager

        self.setWindowTitle("Network Automation — 시작하기")
        self.setFixedSize(460, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        self.email_page   = EmailPage(manager)
        self.payment_page = PaymentPage(manager)
        self.done_page    = DonePage()

        self.stack.addWidget(self.email_page)    # 0
        self.stack.addWidget(self.payment_page)  # 1
        self.stack.addWidget(self.done_page)     # 2

        # 시그널 연결
        self.email_page.go_next.connect(self._to_payment)
        self.email_page.go_done.connect(self._finish)
        self.email_page.show_error.connect(self._handle_special)

        self.payment_page.go_done.connect(self._finish)
        self.payment_page.go_back.connect(lambda: self.stack.setCurrentIndex(0))

        root.addWidget(self.stack)
        self._apply_style()

    # ── 페이지 전환 ──────────────────────────────────────────────

    def _to_payment(self, email: str):
        self.payment_page.set_email(email)
        self.stack.setCurrentIndex(1)

    def _finish(self, token: str):
        """토큰 저장 후 완료 페이지 표시 → 1.5초 후 accept"""
        self.manager._save(token)
        self.stack.setCurrentIndex(2)
        QTimer.singleShot(1500, self.accept)

    def _handle_special(self, signal: str):
        if signal == "__show_key__":
            # 기존 라이센스키 직접 입력 다이얼로그 열기
            from ui.license_dialog import LicenseDialog
            dlg = LicenseDialog(self.manager, self)
            if dlg.exec_() == LicenseDialog.Accepted:
                self.accept()

    # ── 스타일 ───────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #f1f5f9; }

            /* 헤더 */
            QFrame#obHeader {
                background: qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 #2563eb, stop:1 #1d4ed8);
                border: none;
            }
            QLabel#obTitle {
                color: white; font-size: 17px; font-weight: 700;
                font-family: "맑은 고딕"; background: transparent;
            }
            QLabel#obSub {
                color: #bfdbfe; font-size: 11px;
                font-family: "맑은 고딕"; background: transparent;
            }

            /* 본문 */
            QFrame#obBody {
                background: white; border: none;
            }
            QLabel#obDesc {
                color: #475569; font-size: 11px;
                font-family: "맑은 고딕"; line-height: 1.6;
            }

            /* 입력 */
            QLineEdit#obInput {
                background: #f8fafc; border: 1.5px solid #cbd5e1;
                border-radius: 6px; padding: 0 12px;
                font-size: 13px; color: #1e293b;
                font-family: "맑은 고딕";
            }
            QLineEdit#obInput:focus {
                border-color: #3b82f6; background: #eff6ff;
            }

            /* 상태 */
            QLabel#obStatus {
                font-size: 10px; font-family: "맑은 고딕"; padding: 3px 0;
            }

            /* 버튼 — 주요 */
            QPushButton#obPrimary {
                background: #2563eb; color: white; border: none;
                border-radius: 6px; font-size: 12px; font-weight: 700;
                font-family: "맑은 고딕";
            }
            QPushButton#obPrimary:hover    { background: #1d4ed8; }
            QPushButton#obPrimary:pressed  { background: #1e40af; }
            QPushButton#obPrimary:disabled { background: #93c5fd; }

            /* 버튼 — 보조 */
            QPushButton#obSecondary {
                background: #f1f5f9; color: #475569;
                border: 1.5px solid #cbd5e1; border-radius: 6px;
                font-size: 11px; font-family: "맑은 고딕";
            }
            QPushButton#obSecondary:hover { background: #e2e8f0; }

            /* 상품 카드 */
            QFrame#productCard {
                background: #f8fafc; border: 1.5px solid #e2e8f0;
                border-radius: 8px;
            }
            QLabel#prodName {
                color: #1e293b; font-size: 13px; font-weight: 700;
                font-family: "맑은 고딕";
            }
            QLabel#prodDesc {
                color: #64748b; font-size: 10px; font-family: "맑은 고딕";
            }
            QLabel#prodPrice {
                color: #2563eb; font-size: 20px; font-weight: 700;
                font-family: "맑은 고딕"; background: transparent;
            }
            QLabel#emailConfirm {
                color: #475569; font-size: 11px; font-family: "맑은 고딕";
                background: #f1f5f9; border-radius: 4px; padding: 4px;
            }
            QLabel#noticeText {
                color: #92400e; font-size: 10px; font-family: "맑은 고딕";
                background: #fef3c7; border-radius: 4px; padding: 4px 8px;
            }

            /* 완료 */
            QLabel#doneMsg {
                color: #15803d; font-size: 13px; font-weight: 600;
                font-family: "맑은 고딕"; line-height: 1.8;
            }

            /* 푸터 */
            QLabel#obFooter {
                color: #94a3b8; font-size: 10px;
                font-family: "맑은 고딕";
                background: #f8fafc; border-top: 1px solid #e2e8f0;
            }
        """)
