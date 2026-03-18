"""
면책 조항 및 이용 약관 다이얼로그

동의 흐름:
  최초 동의  →  서버 기록 (필수)  →  로컬 캐시 저장 (30일)
  재실행     →  로컬 캐시 유효    →  서버 통신 없이 통과
  캐시 만료  →  서버 재확인       →  갱신
"""

import os
import json
import hashlib
import platform
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QTextEdit, QFrame, QWidget,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush, QPen

# ── 설정 ─────────────────────────────────────────────────────────────────────
AGREEMENT_VERSION = "8.0"
SERVER_URL        = "https://auto-network.co.kr/api"
CACHE_DAYS        = 30   # 로컬 캐시 유효 기간

_CACHE_FILE = Path(
    os.environ.get("APPDATA") or str(Path.home())
) / "NetworkAutomation" / "agreement_cache.json"


# ── 기기 ID (license_manager 와 동일 방식) ────────────────────────────────────
def _machine_id() -> str:
    import subprocess
    parts = []
    try:
        raw = subprocess.check_output(
            "wmic baseboard get serialnumber",
            shell=True, timeout=3, stderr=subprocess.DEVNULL
        ).decode(errors="ignore")
        lines = [l.strip() for l in raw.splitlines()
                 if l.strip() and "SerialNumber" not in l]
        if lines and lines[0] not in ("", "None", "To be filled by O.E.M."):
            parts.append(lines[0])
    except Exception:
        pass
    parts.append(hex(uuid.getnode()))
    parts.append(platform.node())
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20].upper()


# ── 로컬 캐시 ─────────────────────────────────────────────────────────────────
def _load_cache() -> dict:
    try:
        if _CACHE_FILE.exists():
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(server_token: str):
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps({
        "version":      AGREEMENT_VERSION,
        "machine_id":   _machine_id(),
        "server_token": server_token,
        "cached_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at":   (datetime.now() + timedelta(days=CACHE_DAYS)
                         ).strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def has_agreed() -> bool:
    """
    True  → 유효한 로컬 캐시 존재 (서버 통신 없이 통과)
    False → 캐시 없음/만료/버전 불일치 → 서버 동의 필요
    """
    c = _load_cache()
    if not c:
        return False
    if c.get("version") != AGREEMENT_VERSION:
        return False
    if c.get("machine_id") != _machine_id():
        return False
    try:
        exp = datetime.strptime(c["expires_at"], "%Y-%m-%d %H:%M:%S")
        return datetime.now() < exp
    except Exception:
        return False


# ── 서버 전송 워커 ────────────────────────────────────────────────────────────
class _SendWorker(QThread):
    done  = pyqtSignal(bool, str)   # 성공여부, 토큰 or 오류메시지

    def run(self):
        import urllib.request
        import json as _json

        payload = {
            "version":    AGREEMENT_VERSION,
            "machine_id": _machine_id(),
            "hostname":   platform.node(),
            "os":         platform.system() + " " + platform.release(),
            "agreed_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            data = _json.dumps(payload).encode()
            req  = urllib.request.Request(
                f"{SERVER_URL}/agreement",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body  = _json.loads(resp.read().decode())
                token = body.get("token", "ok")
                self.done.emit(True, token)
        except urllib.error.HTTPError as e:
            self.done.emit(False, f"서버 오류 (HTTP {e.code})")
        except urllib.error.URLError as e:
            self.done.emit(False, f"서버에 연결할 수 없습니다.\n인터넷 연결을 확인해주세요.\n({e.reason})")
        except TimeoutError:
            self.done.emit(False, "서버 응답 시간 초과.\n잠시 후 다시 시도해주세요.")
        except Exception as e:
            self.done.emit(False, f"오류: {e}")


# ── 헤더 위젯 ─────────────────────────────────────────────────────────────────
class _Header(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor('#0f172a'))
        g.setColorAt(1.0, QColor('#7c1d1d'))
        p.fillRect(self.rect(), QBrush(g))
        p.setOpacity(0.07)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self.width() - 90, -40, 160, 160)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor('#ffffff')))
        p.setFont(QFont('맑은 고딕', 22))
        p.drawText(24, 54, '⚖️')
        p.setFont(QFont('맑은 고딕', 15, QFont.Bold))
        p.drawText(62, 49, '이용 약관 및 면책 조항')
        p.setPen(QPen(QColor('#94a3b8')))
        p.setFont(QFont('맑은 고딕', 9))
        p.drawText(63, 68, 'Network Automation v8.0  —  사용 전 반드시 읽어주세요.')
        p.end()


# ── 메인 다이얼로그 ───────────────────────────────────────────────────────────
class DisclaimerDialog(QDialog):

    def __init__(self, parent=None, view_only=False):
        super().__init__(parent)
        self._view_only = view_only
        self._worker    = None
        self.setWindowTitle("이용 약관 및 면책 조항")
        self.setFixedWidth(560)
        self.setMinimumHeight(580)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet("QDialog{background:#f8fafc}")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = _Header()
        hdr.setFixedHeight(88)
        root.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background:#f8fafc")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(24, 18, 24, 12)
        bv.setSpacing(12)

        if not self._view_only:
            notice = QLabel(
                "본 소프트웨어를 사용하기 전에 아래 약관을 읽어주십시오.\n"
                "동의 기록은 서버에 안전하게 저장되며, 라이센스 확인 목적으로만 사용됩니다."
            )
            notice.setFont(QFont('맑은 고딕', 9))
            notice.setWordWrap(True)
            notice.setStyleSheet(
                "color:#92400e;background:#fff7ed;"
                "border:1px solid #fed7aa;border-radius:6px;padding:8px 12px"
            )
            bv.addWidget(notice)

        terms = QTextEdit()
        terms.setReadOnly(True)
        terms.setFont(QFont('맑은 고딕', 9))
        terms.setStyleSheet(
            "QTextEdit{background:#ffffff;border:1px solid #e2e8f0;"
            "border-radius:8px;padding:12px;color:#334155}"
        )
        terms.setMinimumHeight(320)
        terms.setHtml(_TERMS_HTML)
        bv.addWidget(terms, 1)

        root.addWidget(body, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#e2e8f0")
        root.addWidget(sep)

        footer = QWidget()
        footer.setStyleSheet("background:#f1f5f9")
        fv = QVBoxLayout(footer)
        fv.setContentsMargins(24, 14, 24, 16)
        fv.setSpacing(10)

        if self._view_only:
            # 약관 보기 전용 — 닫기만
            btn_row = QHBoxLayout()
            close_btn = QPushButton('닫기')
            close_btn.setFixedHeight(36)
            close_btn.setFont(QFont('맑은 고딕', 10, QFont.Bold))
            close_btn.setStyleSheet(
                "QPushButton{background:#1e293b;color:#fff;"
                "border:none;border-radius:7px;padding:0 28px}"
                "QPushButton:hover{background:#334155}"
            )
            close_btn.clicked.connect(self.accept)
            btn_row.addStretch()
            btn_row.addWidget(close_btn)
            fv.addLayout(btn_row)
        else:
            # 동의 모드
            self.chk = QCheckBox(
                "위 약관을 모두 읽었으며, 이에 동의합니다."
            )
            self.chk.setFont(QFont('맑은 고딕', 10, QFont.Bold))
            self.chk.setStyleSheet("color:#1e293b;background:transparent")
            self.chk.toggled.connect(self._on_check)
            fv.addWidget(self.chk)

            # 상태 메시지
            self.lbl_status = QLabel("")
            self.lbl_status.setFont(QFont('맑은 고딕', 9))
            self.lbl_status.setWordWrap(True)
            self.lbl_status.setMinimumHeight(28)
            self.lbl_status.setStyleSheet("background:transparent;color:#64748b")
            fv.addWidget(self.lbl_status)

            btn_row = QHBoxLayout()
            self.btn_decline = QPushButton("동의 안 함 (종료)")
            self.btn_decline.setFixedHeight(36)
            self.btn_decline.setFont(QFont('맑은 고딕', 9))
            self.btn_decline.setStyleSheet(
                "QPushButton{background:#f1f5f9;color:#64748b;"
                "border:1.5px solid #cbd5e1;border-radius:7px;padding:0 16px}"
                "QPushButton:hover{background:#e2e8f0}"
            )
            self.btn_decline.clicked.connect(self.reject)

            self.btn_agree = QPushButton("동의하고 시작")
            self.btn_agree.setFixedHeight(36)
            self.btn_agree.setEnabled(False)
            self.btn_agree.setFont(QFont('맑은 고딕', 10, QFont.Bold))
            self.btn_agree.setStyleSheet(
                "QPushButton{background:#1e293b;color:#fff;"
                "border:none;border-radius:7px;padding:0 24px}"
                "QPushButton:hover{background:#334155}"
                "QPushButton:disabled{background:#cbd5e1;color:#94a3b8}"
            )
            self.btn_agree.clicked.connect(self._on_agree)

            btn_row.addWidget(self.btn_decline)
            btn_row.addStretch()
            btn_row.addWidget(self.btn_agree)
            fv.addLayout(btn_row)

        root.addWidget(footer)

    # ── 이벤트 ───────────────────────────────────────────────────────────────

    def _on_check(self, checked: bool):
        self.btn_agree.setEnabled(checked)
        if checked:
            self.lbl_status.setText(
                "✅ 동의 내용을 서버에 전송합니다. 라이센스 확인 이외의 목적으로 사용되지 않습니다.")
            self.lbl_status.setStyleSheet("color:#16a34a;background:transparent")
        else:
            self.lbl_status.setText("")

    def _on_agree(self):
        self._set_loading(True)
        self.lbl_status.setText("⏳ 서버에 동의 기록을 전송 중입니다…")
        self.lbl_status.setStyleSheet(
            "color:#1d4ed8;background:#eff6ff;"
            "border-radius:4px;padding:4px 8px")
        self._worker = _SendWorker()
        self._worker.done.connect(self._on_send_done)
        self._worker.start()

    def _on_send_done(self, ok: bool, token: str):
        self._set_loading(False)
        if ok:
            _save_cache(token)
            self.lbl_status.setText(
                "✅ 동의가 서버에 기록되었습니다. 프로그램을 시작합니다.")
            self.lbl_status.setStyleSheet(
                "color:#15803d;background:#f0fdf4;"
                "border-radius:4px;padding:4px 8px")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(800, self.accept)
        else:
            self.lbl_status.setText(f"❌ {token.splitlines()[0]}")
            self.lbl_status.setStyleSheet(
                "color:#b91c1c;background:#fef2f2;"
                "border-radius:4px;padding:4px 8px")
            self.lbl_status.setToolTip(token)

    def _set_loading(self, loading: bool):
        self.btn_agree.setEnabled(not loading)
        self.btn_decline.setEnabled(not loading)
        self.chk.setEnabled(not loading)
        self.btn_agree.setText("전송 중…" if loading else "동의하고 시작")


# ── 약관 HTML ─────────────────────────────────────────────────────────────────
_TERMS_HTML = """
<style>
  body { font-family: '맑은 고딕', sans-serif; font-size: 9pt;
         color: #334155; line-height: 1.7; }
  h3   { color: #0f172a; font-size: 10pt; margin-top: 14px; margin-bottom: 4px; }
  p    { margin: 0 0 6px 0; }
  ul   { margin: 4px 0 8px 0; padding-left: 18px; }
  li   { margin-bottom: 3px; }
  .warn { color: #b45309; font-weight: bold; }
  .red  { color: #dc2626; font-weight: bold; }
</style>

<h3>제1조 (소프트웨어 성격 및 목적)</h3>
<p>본 소프트웨어 <b>Network Automation v8.0</b>(이하 "본 소프트웨어")은
네트워크 장비 관리 자동화를 지원하는 도구로서, <b>사용자의 책임 하에</b>
사용됩니다. 본 소프트웨어는 현재 상태(AS-IS)로 제공되며, 어떠한 명시적
또는 묵시적 보증도 제공하지 않습니다.</p>

<h3>제2조 (면책 조항)</h3>
<p class="warn">본 소프트웨어의 개발자(이하 "제공자")는 다음 각 호의 사항에 대하여
어떠한 법적 책임도 지지 않습니다.</p>
<ul>
  <li>본 소프트웨어 사용으로 인한 네트워크 장애, 서비스 중단 또는 운영 장애</li>
  <li>명령어 실행 결과로 발생하는 설정 오류, 데이터 손실 또는 장비 손상</li>
  <li>자동화 스크립트 실행 중 발생하는 의도하지 않은 명령어 적용</li>
  <li>수집·저장된 데이터의 유출, 훼손 또는 무단 접근</li>
  <li>본 소프트웨어의 버그, 오류, 취약점으로 인한 직·간접적 피해</li>
  <li>운영 환경(OS, Python, 라이브러리 등)과의 호환 문제로 인한 손해</li>
  <li>사용자의 부주의, 오입력, 잘못된 사용 방법으로 인한 모든 결과</li>
</ul>

<h3>제3조 (사용자 책임)</h3>
<p>사용자는 본 소프트웨어를 사용하기 전 다음 사항을 확인하고 이에 대한
<b>모든 책임을 본인이 부담</b>함에 동의합니다.</p>
<ul>
  <li>접속 대상 장비에 대한 <b>정당한 접근 권한</b>을 보유하고 있음</li>
  <li>실행하는 명령어의 영향 범위를 사전에 충분히 검토하였음</li>
  <li>중요 설정 변경 전 <b>백업 및 롤백 계획</b>을 수립하였음</li>
  <li>운영 환경(프로덕션/개발/테스트)에 맞는 절차를 준수하였음</li>
  <li>관련 법령, 사내 규정, 네트워크 보안 정책을 준수하였음</li>
</ul>

<h3>제4조 (손해배상 범위 제한)</h3>
<p>어떠한 경우에도 제공자가 부담하는 손해배상액은 사용자가 본 소프트웨어에
대해 지불한 라이센스 금액을 초과하지 않습니다. 제공자는 <b>간접 손해,
파생 손해, 특별 손해, 징벌적 손해</b>에 대해 일절 책임을 지지 않습니다.</p>

<h3>제5조 (불법적 사용 금지)</h3>
<p class="red">본 소프트웨어를 권한 없는 시스템에 대한 무단 접근, 해킹,
정보 탈취 등 불법적 목적으로 사용하는 것을 엄격히 금지합니다.
이로 인한 민·형사상 모든 책임은 사용자에게 있으며, 제공자는
관련 기관에 협조할 의무를 가집니다.</p>

<h3>제6조 (동의 기록 및 개인정보)</h3>
<p>사용자가 본 약관에 동의하는 시점에 <b>동의 일시, 기기 식별 정보, OS 정보</b>가
제공자 서버에 기록됩니다. 이 기록은 <b>라이센스 확인 및 서비스 제공 목적으로만</b>
사용되며, 제3자에게 제공되지 않습니다.</p>

<h3>제7조 (약관의 변경)</h3>
<p>제공자는 소프트웨어 업데이트 시 본 약관을 변경할 수 있습니다.
변경된 약관은 신규 버전 최초 실행 시 사용자의 재동의를 통해 효력이 발생합니다.</p>

<p style="margin-top:14px; color:#94a3b8; font-size:8pt;">
  본 약관은 대한민국 법률에 따라 해석·적용됩니다.
  분쟁 발생 시 제공자의 주소지를 관할하는 법원을 제1심 관할 법원으로 합니다.
</p>
"""
