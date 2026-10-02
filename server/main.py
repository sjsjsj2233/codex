"""
Network Automation 라이센스 서버
FastAPI + SQLite

엔드포인트:
  POST /api/activate        — 앱에서 라이센스키 활성화
  POST /api/admin/generate  — 관리자: 라이센스키 생성
  GET  /api/admin/licenses  — 관리자: 전체 목록 조회
  POST /api/admin/revoke    — 관리자: 특정 키 비활성화
"""

import os
import hmac
import hashlib
import base64
import json
import secrets
import string
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends, Request, Form, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import database

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── 설정 ────────────────────────────────────────────────────────
APP_SECRET   = os.environ.get("APP_SECRET",   "anta_net_2026_secret_key")
ADMIN_TOKEN  = os.environ.get("ADMIN_TOKEN",  "change_this_admin_token_now")

# Gumroad 설정 (.env 에서 로드)
GUMROAD_WEBHOOK_TOKEN = os.environ.get("GUMROAD_WEBHOOK_TOKEN", "")  # 직접 정한 비밀 토큰
GUMROAD_PRODUCT_URL   = os.environ.get("GUMROAD_PRODUCT_URL", "")    # https://gumroad.com/l/xxx
SITE_URL              = os.environ.get("SITE_URL", "https://auto-network.co.kr")

# 이메일 설정 (Gmail 권장)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "doaslove962@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "")   # Gmail 앱 비밀번호

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Network Automation License Server", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 시작 시 DB 초기화 ────────────────────────────────────────────
@app.on_event("startup")
def startup():
    database.init_db()
    log.info("DB 초기화 완료")

# ─── 토큰 서명 (앱과 동일한 로직) ────────────────────────────────
def _sign_token(payload: dict) -> str:
    """앱이 APP_SECRET 으로 검증하는 토큰 생성"""
    secret = APP_SECRET.encode()
    b64 = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False).encode()
    ).decode().rstrip("=")
    sig = hmac.new(secret, b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"

# ─── 관리자 인증 ──────────────────────────────────────────────────
def require_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="관리자 인증 실패")

# ─── 요청/응답 스키마 ──────────────────────────────────────────────
class ActivateRequest(BaseModel):
    license_key: str
    machine_id:  str

class GenerateRequest(BaseModel):
    count:      int    = 1
    email:      str    = ""
    expires_at: str    = "9999-12-31"   # YYYY-MM-DD
    memo:       str    = ""

class RevokeRequest(BaseModel):
    license_key: str

class AgreementRequest(BaseModel):
    version:    str
    machine_id: str
    hostname:   str = ""
    os:         str = ""
    agreed_at:  str = ""

# ─── 공개 API ─────────────────────────────────────────────────────
@app.post("/api/agreement")
def record_agreement(req: AgreementRequest, request: Request):
    """
    이용 약관 동의 기록
    - 클라이언트 IP 자동 수집
    - 동의 기록을 agreements 테이블에 저장
    - 서명된 토큰 반환 (앱 로컬 캐시용)
    """
    client_ip = request.headers.get("X-Forwarded-For",
                request.client.host if request.client else "unknown")
    agreed_at = req.agreed_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row_id = database.insert_agreement(
        version    = req.version,
        machine_id = req.machine_id,
        hostname   = req.hostname,
        os_info    = req.os,
        client_ip  = client_ip,
        agreed_at  = agreed_at,
    )
    log.info(f"[Agreement] 동의 기록 #{row_id} | {req.machine_id} | {client_ip} | v{req.version}")

    # 앱 캐시 검증용 토큰 (서명 포함)
    token = _sign_token({
        "type":       "agreement",
        "version":    req.version,
        "machine_id": req.machine_id,
        "agreed_at":  agreed_at,
        "record_id":  row_id,
    })
    return {"token": token, "record_id": row_id}


@app.post("/api/activate")
def activate(req: ActivateRequest):
    """앱에서 라이센스키 + 기기ID를 보내면 토큰 반환"""
    key        = req.license_key.strip().upper()
    machine_id = req.machine_id.strip().upper()

    if not key or not machine_id:
        raise HTTPException(status_code=400, detail="필수 값 누락")

    lic = database.get_license(key)

    # 존재하지 않는 키
    if not lic:
        log.warning(f"[ACTIVATE] 잘못된 키: {key[:9]}***")
        raise HTTPException(status_code=404,
                            detail="유효하지 않은 라이센스키입니다.")

    # 비활성화된 키
    if not lic["active"]:
        raise HTTPException(status_code=403,
                            detail="비활성화된 라이센스키입니다.")

    # 이미 다른 기기에서 활성화됨
    existing = lic.get("machine_id")
    if existing and existing != machine_id:
        log.warning(f"[ACTIVATE] 기기 불일치: {key[:9]}*** "
                    f"registered={existing} tried={machine_id}")
        raise HTTPException(
            status_code=409,
            detail="이미 다른 기기에서 활성화된 키입니다."
        )

    # 최초 활성화 — 기기 ID 등록
    if not existing:
        database.bind_machine(key, machine_id)
        log.info(f"[ACTIVATE] 신규 활성화: {key[:9]}*** machine={machine_id}")

    # 서명된 토큰 발급
    token = _sign_token({
        "license_key": key,
        "machine_id":  machine_id,
        "email":       lic.get("email", ""),
        "activated_at": datetime.now().strftime("%Y-%m-%d"),
        "expires_at":  lic.get("expires_at", "9999-12-31"),
    })

    return {
        "token":      token,
        "email":      lic.get("email", ""),
        "expires_at": lic.get("expires_at", "9999-12-31"),
        "message":    "활성화 완료",
    }

# ─── 사용자 흐름 API ─────────────────────────────────────────────

class UserCheckRequest(BaseModel):
    email:      str
    machine_id: str

class TempPayRequest(BaseModel):
    email:      str
    machine_id: str


@app.post("/api/user/status")
def user_status(req: UserCheckRequest):
    """
    앱 온보딩: 이 이메일이 이미 결제했는지 확인
    - 결제 이력 있음 + 같은 기기  → 토큰 재발급 (재설치 대응)
    - 결제 이력 있음 + 다른 기기  → already_activated
    - 결제 이력 없음              → not_paid
    """
    email      = req.email.strip().lower()
    machine_id = req.machine_id.strip().upper()

    lic = database.get_license_by_email(email)

    if not lic:
        return {"status": "not_paid"}

    if not lic["active"]:
        return {"status": "revoked"}

    # 같은 기기 or 아직 미등록
    if not lic["machine_id"] or lic["machine_id"] == machine_id:
        if not lic["machine_id"]:
            database.bind_machine(lic["key"], machine_id)
        token = _sign_token({
            "license_key":  lic["key"],
            "machine_id":   machine_id,
            "email":        email,
            "activated_at": datetime.now().strftime("%Y-%m-%d"),
            "expires_at":   lic.get("expires_at", "9999-12-31"),
        })
        return {"status": "active", "token": token,
                "expires_at": lic.get("expires_at", "9999-12-31")}

    # 다른 기기
    return {"status": "already_activated"}


@app.post("/api/payment/temp")
def temp_payment(req: TempPayRequest):
    """
    임시 결제 엔드포인트 (실제 PG 연동 전 테스트용)
    나중에 Toss Payments 웹훅으로 교체
    """
    email      = req.email.strip().lower()
    machine_id = req.machine_id.strip().upper()

    if not email:
        raise HTTPException(status_code=400, detail="이메일 필요")

    # 이미 결제한 이메일이면 재발급
    existing = database.get_license_by_email(email)
    if existing and existing["active"]:
        if existing["machine_id"] and existing["machine_id"] != machine_id:
            raise HTTPException(status_code=409,
                                detail="이미 다른 기기에서 활성화된 계정입니다.")
        key = existing["key"]
    else:
        key = _make_key()
        database.insert_license(key=key, email=email,
                                memo="temp_payment")

    database.bind_machine(key, machine_id)

    token = _sign_token({
        "license_key":  key,
        "machine_id":   machine_id,
        "email":        email,
        "activated_at": datetime.now().strftime("%Y-%m-%d"),
        "expires_at":   "9999-12-31",
    })

    log.info(f"[TEMP_PAY] 결제완료(임시): email={email} key={key[:9]}***")
    return {"token": token, "license_key": key,
            "expires_at": "9999-12-31", "message": "결제 완료"}


# ─── 관리자 API ───────────────────────────────────────────────────
@app.post("/api/admin/generate", dependencies=[Depends(require_admin)])
def generate(req: GenerateRequest):
    """라이센스키 발급 (결제 후 호출)"""
    if req.count < 1 or req.count > 100:
        raise HTTPException(status_code=400, detail="count: 1~100")

    keys = []
    for _ in range(req.count):
        key = _make_key()
        database.insert_license(
            key        = key,
            email      = req.email,
            expires_at = req.expires_at,
            memo       = req.memo,
        )
        keys.append(key)
        log.info(f"[GENERATE] 키 발급: {key} / email={req.email}")

    return {"keys": keys, "count": len(keys)}


@app.get("/api/admin/licenses", dependencies=[Depends(require_admin)])
def list_licenses(page: int = 1, per_page: int = 50):
    """전체 라이센스 목록"""
    total, rows = database.list_licenses(page, per_page)
    return {"total": total, "page": page, "items": rows}


@app.post("/api/admin/revoke", dependencies=[Depends(require_admin)])
def revoke(req: RevokeRequest):
    """키 비활성화"""
    key = req.license_key.strip().upper()
    if not database.get_license(key):
        raise HTTPException(status_code=404, detail="키를 찾을 수 없습니다.")
    database.revoke_license(key)
    log.info(f"[REVOKE] {key}")
    return {"message": f"{key} 비활성화 완료"}


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

# ─── 키 생성 유틸 ─────────────────────────────────────────────────
def _make_key() -> str:
    """ANTA-XXXX-XXXX-XXXX 형식 랜덤 키 생성"""
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(chars) for _ in range(4))
             for _ in range(3)]
    return "ANTA-" + "-".join(parts)


# ─── 이메일 발송 ──────────────────────────────────────────────────
def _send_license_email(to_email: str, license_key: str):
    """결제 완료 후 라이센스 키를 이메일로 발송"""
    if not SMTP_PASS:
        log.warning(f"[EMAIL] SMTP_PASS 미설정 — 이메일 발송 건너뜀 (키: {license_key})")
        return

    subject = "[Network Automation] 라이센스 키 발급 안내"
    html_body = f"""
<div style="font-family:'Malgun Gothic',sans-serif;max-width:560px;margin:0 auto;background:#f8fafc;padding:32px 24px;border-radius:12px">
  <div style="background:linear-gradient(135deg,#0f172a,#1e40af);border-radius:10px;padding:28px 24px;margin-bottom:24px">
    <h1 style="color:#fff;font-size:20px;margin:0">🔑 Network Automation</h1>
    <p style="color:#94a3b8;font-size:13px;margin:6px 0 0">라이센스 키 발급 완료</p>
  </div>

  <p style="color:#334155;font-size:14px;line-height:1.7">
    결제해 주셔서 감사합니다.<br>
    아래 라이센스 키를 프로그램의 <b>정보 탭 → 라이센스 활성화</b>에 입력해주세요.
  </p>

  <div style="background:#fff;border:2px solid #3b82f6;border-radius:10px;padding:20px;text-align:center;margin:20px 0">
    <p style="color:#64748b;font-size:12px;margin:0 0 8px">라이센스 키</p>
    <p style="font-family:monospace;font-size:22px;font-weight:700;color:#1e40af;letter-spacing:2px;margin:0">
      {license_key}
    </p>
  </div>

  <div style="background:#fef3c7;border-radius:8px;padding:14px 16px;margin-bottom:20px">
    <p style="color:#92400e;font-size:13px;margin:0">
      ⚠️ 이 키는 <b>1대의 PC</b>에서만 사용 가능합니다.<br>
      PC를 교체하신 경우 <a href="mailto:doaslove962@gmail.com" style="color:#1d4ed8">doaslove962@gmail.com</a>으로 문의해주세요.
    </p>
  </div>

  <p style="color:#94a3b8;font-size:12px;text-align:center;margin:0">
    문의: <a href="mailto:doaslove962@gmail.com" style="color:#3b82f6">doaslove962@gmail.com</a>
    &nbsp;|&nbsp; <a href="https://auto-network.co.kr" style="color:#3b82f6">auto-network.co.kr</a>
  </p>
</div>
"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, to_email, msg.as_string())

        log.info(f"[EMAIL] 발송 완료 → {to_email}")
    except Exception as e:
        log.error(f"[EMAIL] 발송 실패 → {to_email}: {e}")


# ─── Gumroad 결제 ─────────────────────────────────────────────────

@app.get("/buy", response_class=HTMLResponse)
def buy_page():
    """구매 페이지 — Gumroad 상품 페이지로 이동"""
    if not GUMROAD_PRODUCT_URL:
        return HTMLResponse("<h2>결제 시스템이 준비 중입니다.</h2>", status_code=503)
    return RedirectResponse(GUMROAD_PRODUCT_URL, status_code=302)


@app.post("/api/gumroad/webhook")
async def gumroad_webhook(request: Request, token: str = ""):
    """
    Gumroad Webhook 수신 (판매 완료 ping)

    Gumroad 대시보드 → Settings → Advanced → Ping URL 에 등록:
      https://auto-network.co.kr/api/gumroad/webhook?token=YOUR_SECRET_TOKEN

    판매 완료 시 Gumroad 가 아래 form-data 를 POST 로 전송:
      email, sale_id, product_name, price, currency, test, refunded ...
    """
    # ── 토큰 검증 ──────────────────────────────────────────────────
    if GUMROAD_WEBHOOK_TOKEN and token != GUMROAD_WEBHOOK_TOKEN:
        log.warning(f"[GUMROAD] 잘못된 토큰: {token!r}")
        raise HTTPException(status_code=403, detail="Invalid token")

    # ── 페이로드 파싱 (form-data 또는 JSON 모두 대응) ───────────────
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    email      = (data.get("email") or "").strip().lower()
    sale_id    = data.get("sale_id", "")
    is_test    = str(data.get("test", "false")).lower() == "true"
    refunded   = str(data.get("refunded", "false")).lower() == "true"
    product    = data.get("product_name", "")
    price      = data.get("price", "0")

    log.info(f"[GUMROAD] ping — email={email} sale_id={sale_id} test={is_test}")

    # 환불된 경우 라이센스 비활성화
    if refunded:
        lic = database.get_license_by_email(email)
        if lic:
            database.revoke_license(lic["key"])
            log.info(f"[GUMROAD] 환불 처리 — {email} 라이센스 비활성화")
        return {"received": True, "action": "revoked"}

    if not email:
        log.error("[GUMROAD] 이메일 없음")
        raise HTTPException(status_code=400, detail="email missing")

    # 테스트 ping 은 DB 저장 없이 응답
    if is_test:
        log.info("[GUMROAD] 테스트 ping — 실제 처리 건너뜀")
        return {"received": True, "action": "test_skip"}

    # ── 라이센스 키 생성 (중복 방지) ──────────────────────────────
    existing = database.get_license_by_email(email)
    if existing and existing["active"]:
        key = existing["key"]
        log.info(f"[GUMROAD] 기존 키 재발송: {email} → {key[:9]}***")
    else:
        key = _make_key()
        database.insert_license(
            key  = key,
            email= email,
            memo = f"gumroad:{sale_id}",
        )
        log.info(f"[GUMROAD] 결제완료: {email} → {key[:9]}*** / {product} / {price}")

    # ── 이메일 발송 ────────────────────────────────────────────────
    _send_license_email(email, key)

    return {"received": True, "action": "issued"}


@app.get("/payment/success", response_class=HTMLResponse)
def payment_success():
    """Gumroad 결제 완료 후 리다이렉트 페이지 (선택적)"""
    page = """<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8"><title>결제 완료</title>
<style>
  body{font-family:'Malgun Gothic',sans-serif;background:#0f172a;
       display:flex;align-items:center;justify-content:center;min-height:100vh}
  .card{background:#fff;border-radius:16px;padding:48px 36px;max-width:440px;
        width:90%;text-align:center}
  h1{font-size:22px;font-weight:700;color:#16a34a;margin-bottom:10px}
  p{color:#475569;font-size:14px;line-height:1.8;margin-bottom:20px}
  .btn{display:inline-block;padding:12px 28px;background:#2563eb;color:#fff;
       border-radius:8px;text-decoration:none;font-weight:700;font-size:14px}
</style></head>
<body>
<div class="card">
  <div style="font-size:56px;margin-bottom:16px">✅</div>
  <h1>결제가 완료되었습니다!</h1>
  <p>
    입력하신 이메일로 <b>라이센스 키</b>가 발송되었습니다.<br>
    스팸 폴더도 확인해주세요.<br><br>
    프로그램의 <b>정보 탭 → 🔑 라이센스 활성화</b> 버튼을 눌러<br>
    발급된 키를 입력하면 즉시 사용 가능합니다.
  </p>
  <a href="https://auto-network.co.kr" class="btn">홈으로 돌아가기</a>
</div>
</body></html>"""
    return HTMLResponse(page)


# ─── 어드민 웹 UI ─────────────────────────────────────────────────
_ADMIN_COOKIE = "admin_session"

def _check_session(token: str = Cookie(default=None, alias=_ADMIN_COOKIE)):
    return token == ADMIN_TOKEN

def _base_html(title: str, body: str, authed: bool = True) -> str:
    logout = '<a href="/admin/logout" style="float:right;color:#888;font-size:13px;">로그아웃</a>' if authed else ''
    return f"""<!DOCTYPE html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — License Admin</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Malgun Gothic',sans-serif;background:#f1f5f9;color:#1e293b}}
  .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px}}
  h1{{font-size:20px;font-weight:700;margin-bottom:20px;color:#0f172a}}
  h2{{font-size:15px;font-weight:600;margin:20px 0 10px;color:#334155}}
  .card{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:20px;margin-bottom:20px}}
  input,select{{width:100%;padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px}}
  button,a.btn{{display:inline-block;padding:8px 18px;border-radius:6px;border:none;cursor:pointer;font-size:13px;font-weight:600;text-decoration:none}}
  .btn-primary{{background:#3b82f6;color:#fff}} .btn-primary:hover{{background:#2563eb}}
  .btn-danger {{background:#ef4444;color:#fff}} .btn-danger:hover{{background:#dc2626}}
  .btn-green  {{background:#22c55e;color:#fff}} .btn-green:hover{{background:#16a34a}}
  table{{width:100%;border-collapse:collapse;font-size:12px}}
  th{{background:#f8fafc;padding:8px 10px;text-align:left;border-bottom:2px solid #e2e8f0;font-weight:600}}
  td{{padding:7px 10px;border-bottom:1px solid #f1f5f9;vertical-align:middle}}
  tr:hover td{{background:#f8fafc}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}}
  .badge-ok{{background:#dcfce7;color:#166534}}
  .badge-off{{background:#fee2e2;color:#991b1b}}
  .key{{font-family:monospace;font-size:12px;letter-spacing:.5px}}
  .msg-ok{{background:#dcfce7;color:#166534;padding:10px;border-radius:6px;margin-bottom:12px}}
  .msg-err{{background:#fee2e2;color:#991b1b;padding:10px;border-radius:6px;margin-bottom:12px}}
  .stats{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
  .stat{{background:#fff;border-radius:8px;padding:14px 20px;flex:1;min-width:120px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
  .stat-n{{font-size:26px;font-weight:700;color:#3b82f6}}
  .stat-l{{font-size:12px;color:#64748b;margin-top:2px}}
  nav{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
  nav a{{padding:7px 14px;background:#fff;border-radius:6px;font-size:13px;color:#334155;text-decoration:none;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
  nav a:hover{{background:#e0f2fe;color:#0369a1}}
</style></head>
<body><div class="wrap">
<h1>🔑 License Admin {logout}</h1>
<nav>
  <a href="/admin/dashboard">대시보드</a>
  <a href="/admin/licenses">라이센스 목록</a>
  <a href="/admin/agreements">동의 기록</a>
  <a href="/admin/generate">키 발급</a>
  <a href="/admin/search">검색</a>
</nav>
{body}
</div></body></html>"""

# ── 로그인 ────────────────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page():
    body = """<div class="card" style="max-width:380px;margin:60px auto">
    <h2 style="margin-bottom:16px">관리자 로그인</h2>
    <form method="post" action="/admin/login">
      <input type="password" name="token" placeholder="Admin Token" autofocus>
      <button class="btn-primary" style="width:100%">로그인</button>
    </form></div>"""
    return HTMLResponse(_base_html("로그인", body, authed=False))

@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(token: str = Form(...)):
    if token != ADMIN_TOKEN:
        body = '<div class="msg-err">❌ 토큰이 올바르지 않습니다.</div>' + """
        <div class="card" style="max-width:380px;margin:0 auto">
        <form method="post" action="/admin/login">
          <input type="password" name="token" placeholder="Admin Token" autofocus>
          <button class="btn-primary" style="width:100%">다시 시도</button>
        </form></div>"""
        return HTMLResponse(_base_html("로그인", body, authed=False))
    resp = RedirectResponse("/admin/dashboard", status_code=303)
    resp.set_cookie(_ADMIN_COOKIE, token, httponly=True, samesite="lax")
    return resp

@app.get("/admin/logout")
def admin_logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(_ADMIN_COOKIE)
    return resp

# ── 대시보드 ──────────────────────────────────────────────────────
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(authed: bool = Depends(_check_session)):
    if not authed:
        return RedirectResponse("/admin/login")
    total, rows = database.list_licenses(1, 9999)
    active  = sum(1 for r in rows if r["active"])
    bound   = sum(1 for r in rows if r["machine_id"])
    expired = sum(1 for r in rows
                  if r["expires_at"] < datetime.now().strftime("%Y-%m-%d"))
    recent  = sorted(rows, key=lambda r: r["created_at"] or "", reverse=True)[:10]

    rows_html = "".join(f"""<tr>
      <td class="key">{r['key']}</td>
      <td>{r['email'] or '-'}</td>
      <td><span class="badge {'badge-ok' if r['active'] else 'badge-off'}">
          {'활성' if r['active'] else '비활성'}</span></td>
      <td>{r['activated_at'][:10] if r['activated_at'] else '-'}</td>
      <td>{r['expires_at']}</td>
    </tr>""" for r in recent)

    body = f"""
    <div class="stats">
      <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">전체 키</div></div>
      <div class="stat"><div class="stat-n" style="color:#22c55e">{active}</div><div class="stat-l">활성</div></div>
      <div class="stat"><div class="stat-n" style="color:#64748b">{total-active}</div><div class="stat-l">비활성</div></div>
      <div class="stat"><div class="stat-n" style="color:#3b82f6">{bound}</div><div class="stat-l">기기 등록됨</div></div>
      <div class="stat"><div class="stat-n" style="color:#ef4444">{expired}</div><div class="stat-l">만료</div></div>
    </div>
    <div class="card">
      <h2>최근 발급 키 (10개)</h2>
      <table><tr><th>키</th><th>이메일</th><th>상태</th><th>활성화일</th><th>만료일</th></tr>
      {rows_html}</table>
      <div style="margin-top:12px"><a href="/admin/licenses" class="btn btn-primary">전체 목록 →</a></div>
    </div>"""
    return HTMLResponse(_base_html("대시보드", body))

# ── 전체 목록 ──────────────────────────────────────────────────────
@app.get("/admin/licenses", response_class=HTMLResponse)
def admin_list(page: int = 1, authed: bool = Depends(_check_session)):
    if not authed:
        return RedirectResponse("/admin/login")
    per = 50
    total, rows = database.list_licenses(page, per)
    pages = (total + per - 1) // per

    rows_html = "".join(f"""<tr>
      <td class="key">{r['key']}</td>
      <td>{r['email'] or '-'}</td>
      <td><span class="badge {'badge-ok' if r['active'] else 'badge-off'}">
          {'활성' if r['active'] else '비활성'}</span></td>
      <td style="font-size:11px;color:#64748b">{r['machine_id'][:16] + '...' if r['machine_id'] and len(r['machine_id'])>16 else (r['machine_id'] or '-')}</td>
      <td>{r['activated_at'][:10] if r['activated_at'] else '-'}</td>
      <td>{r['expires_at']}</td>
      <td>{r['memo'] or '-'}</td>
      <td>{"" if not r['active'] else f'<form method="post" action="/admin/revoke" style="margin:0"><input type="hidden" name="key" value="{r["key"]}"><button class="btn btn-danger" style="padding:3px 10px;font-size:11px">취소</button></form>'}</td>
    </tr>""" for r in rows)

    pager = " ".join(
        f'<a href="/admin/licenses?page={p}" class="btn btn-primary" style="padding:5px 10px">{p}</a>'
        for p in range(1, pages + 1))

    body = f"""<div class="card">
      <h2>전체 라이센스 ({total}개)</h2>
      <table><tr><th>키</th><th>이메일</th><th>상태</th><th>기기ID</th>
        <th>활성화일</th><th>만료일</th><th>메모</th><th>액션</th></tr>
      {rows_html}</table>
      <div style="margin-top:14px;display:flex;gap:6px;flex-wrap:wrap">{pager}</div>
    </div>"""
    return HTMLResponse(_base_html("라이센스 목록", body))

# ── 키 발급 ────────────────────────────────────────────────────────
@app.get("/admin/generate", response_class=HTMLResponse)
def admin_generate_page(authed: bool = Depends(_check_session)):
    if not authed:
        return RedirectResponse("/admin/login")
    body = """<div class="card" style="max-width:480px">
    <h2>라이센스 키 발급</h2>
    <form method="post" action="/admin/generate">
      <label style="font-size:12px;color:#64748b">이메일 (선택)</label>
      <input type="email" name="email" placeholder="user@example.com">
      <label style="font-size:12px;color:#64748b">발급 수량</label>
      <input type="number" name="count" value="1" min="1" max="100">
      <label style="font-size:12px;color:#64748b">만료일</label>
      <input type="date" name="expires_at" value="9999-12-31">
      <label style="font-size:12px;color:#64748b">메모</label>
      <input type="text" name="memo" placeholder="구매자 메모">
      <button class="btn-green" style="width:100%;margin-top:4px">키 발급</button>
    </form></div>"""
    return HTMLResponse(_base_html("키 발급", body))

@app.post("/admin/generate", response_class=HTMLResponse)
def admin_generate_submit(
    email: str = Form(default=""),
    count: int = Form(default=1),
    expires_at: str = Form(default="9999-12-31"),
    memo: str = Form(default=""),
    authed: bool = Depends(_check_session),
):
    if not authed:
        return RedirectResponse("/admin/login")
    count = max(1, min(100, count))
    keys = []
    for _ in range(count):
        k = _make_key()
        database.insert_license(key=k, email=email, expires_at=expires_at, memo=memo)
        keys.append(k)
        log.info(f"[WEB_GENERATE] {k} / {email}")

    keys_html = "".join(f'<div class="key" style="padding:6px 0;border-bottom:1px solid #f1f5f9">{k}</div>' for k in keys)
    body = f"""
    <div class="msg-ok">✅ {len(keys)}개 키가 발급되었습니다.</div>
    <div class="card" style="max-width:480px">
      <h2>발급된 키</h2>
      {keys_html}
      <div style="margin-top:14px;display:flex;gap:8px">
        <a href="/admin/generate" class="btn btn-green">추가 발급</a>
        <a href="/admin/licenses" class="btn btn-primary">목록 보기</a>
      </div>
    </div>"""
    return HTMLResponse(_base_html("키 발급 완료", body))

# ── 키 취소 ────────────────────────────────────────────────────────
@app.post("/admin/revoke", response_class=HTMLResponse)
def admin_revoke(key: str = Form(...), authed: bool = Depends(_check_session)):
    if not authed:
        return RedirectResponse("/admin/login")
    if not database.get_license(key):
        return RedirectResponse("/admin/licenses?err=notfound", status_code=303)
    database.revoke_license(key)
    log.info(f"[WEB_REVOKE] {key}")
    return RedirectResponse("/admin/licenses", status_code=303)

# ── 검색 ──────────────────────────────────────────────────────────
@app.get("/admin/agreements", response_class=HTMLResponse)
def admin_agreements(page: int = 1, authed: bool = Depends(_check_session)):
    if not authed:
        return RedirectResponse("/admin/login")
    total, rows = database.list_agreements(page, 50)
    total_pages = max(1, (total + 49) // 50)

    rows_html = "".join(f"""<tr>
      <td style="color:#64748b;font-size:11px">#{r['id']}</td>
      <td><span class="badge badge-ok">{r['version']}</span></td>
      <td style="font-family:monospace;font-size:11px">{r['machine_id']}</td>
      <td>{r['hostname'] or '-'}</td>
      <td style="font-size:11px;color:#64748b">{r['os_info'] or '-'}</td>
      <td style="font-family:monospace;font-size:11px">{r['client_ip']}</td>
      <td style="font-size:11px">{r['agreed_at']}</td>
    </tr>""" for r in rows)

    pager = " ".join(
        f'<a href="/admin/agreements?page={p}" class="btn btn-primary" style="padding:5px 10px">{p}</a>'
        for p in range(1, total_pages + 1)
    )
    body = f"""<div class="card">
      <h2>⚖️ 이용약관 동의 기록 — 총 {total}건</h2>
      <p style="font-size:12px;color:#64748b;margin-bottom:12px">
        사용자가 이용약관에 동의할 때 서버에 자동 기록됩니다.
        법적 분쟁 시 증거로 활용될 수 있습니다.
      </p>
      <table>
        <tr>
          <th>#</th><th>버전</th><th>기기 ID</th><th>호스트명</th>
          <th>OS</th><th>IP</th><th>동의 일시</th>
        </tr>
        {rows_html}
      </table>
      <div style="margin-top:14px;display:flex;gap:6px;flex-wrap:wrap">{pager}</div>
    </div>"""
    return HTMLResponse(_base_html("동의 기록", body))


@app.get("/admin/search", response_class=HTMLResponse)
def admin_search(q: str = "", authed: bool = Depends(_check_session)):
    if not authed:
        return RedirectResponse("/admin/login")
    result_html = ""
    if q:
        # 이메일 또는 키로 검색
        row = database.get_license(q.strip().upper())
        if not row:
            row = database.get_license_by_email(q.strip().lower())
        if row:
            result_html = f"""<div class="card" style="max-width:600px">
              <h2>검색 결과</h2>
              <table>
                <tr><th>항목</th><th>값</th></tr>
                <tr><td>키</td><td class="key">{row['key']}</td></tr>
                <tr><td>이메일</td><td>{row['email'] or '-'}</td></tr>
                <tr><td>상태</td><td><span class="badge {'badge-ok' if row['active'] else 'badge-off'}">
                    {'활성' if row['active'] else '비활성'}</span></td></tr>
                <tr><td>기기 ID</td><td style="font-size:11px">{row['machine_id'] or '-'}</td></tr>
                <tr><td>활성화일</td><td>{row['activated_at'] or '-'}</td></tr>
                <tr><td>만료일</td><td>{row['expires_at']}</td></tr>
                <tr><td>메모</td><td>{row['memo'] or '-'}</td></tr>
                <tr><td>생성일</td><td>{row['created_at'] or '-'}</td></tr>
              </table>
              {"" if not row['active'] else f'''<form method="post" action="/admin/revoke" style="margin-top:12px">
                <input type="hidden" name="key" value="{row['key']}">
                <button class="btn btn-danger">이 키 비활성화</button></form>'''}
            </div>"""
        else:
            result_html = f'<div class="msg-err">"{q}" 검색 결과 없음</div>'

    body = f"""<div class="card" style="max-width:480px">
      <h2>키 / 이메일 검색</h2>
      <form method="get" action="/admin/search">
        <input type="text" name="q" value="{q}" placeholder="ANTA-XXXX-XXXX-XXXX  또는  user@email.com" autofocus>
        <button class="btn-primary" style="width:100%">검색</button>
      </form></div>
    {result_html}"""
    return HTMLResponse(_base_html("검색", body))
