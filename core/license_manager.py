"""
라이센스 관리 모듈

흐름:
  최초 실행  →  라이센스키 입력 필요 (이메일 문의)
  활성화 후  →  기기 바인딩 토큰 로컬 저장
  이후 실행  →  로컬 토큰 서명 검증 + 기기ID 확인 (오프라인 가능)
"""

import os
import sys
import json
import hmac
import hashlib
import base64
import platform
import subprocess
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


# ─── 설정 ────────────────────────────────────────────────────────
SERVER_URL = "https://auto-network.co.kr/api"

# 앱 내장 서명 검증 키
# !! 서버 .env 의 APP_SECRET 값과 반드시 동일해야 합니다 !!
APP_SECRET = b"anta_net_2026_secret_key"


def _license_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "NetworkAutomation"
    d.mkdir(parents=True, exist_ok=True)
    return d


LICENSE_FILE = _license_dir() / "license.dat"


class LicenseManager:
    """라이센스 확인·활성화·저장 처리"""

    # ── 기기 고유 ID ─────────────────────────────────────────────

    def get_machine_id(self) -> str:
        """이 PC의 고유 ID (변하지 않는 하드웨어 정보 기반)"""
        parts = []

        # 1) 마더보드 시리얼 (가장 안정적)
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

        # 2) MAC 주소
        parts.append(hex(uuid.getnode()))

        # 3) 호스트명
        parts.append(platform.node())

        fingerprint = "|".join(parts).encode()
        return hashlib.sha256(fingerprint).hexdigest()[:20].upper()

    # ── 토큰 검증 ────────────────────────────────────────────────

    def _verify_token(self, token: str) -> Optional[dict]:
        """
        토큰 형식: base64url(payload).hmac_sha256_hex
        서버가 APP_SECRET 으로 서명 → 앱이 동일 키로 검증
        """
        try:
            b64_payload, signature = token.rsplit(".", 1)
            expected = hmac.new(
                APP_SECRET, b64_payload.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                return None
            padding = "=" * (-len(b64_payload) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(b64_payload + padding)
            )
            return payload
        except Exception:
            return None

    # ── 로컬 저장/로드 ───────────────────────────────────────────

    def _save(self, token: str):
        """토큰을 XOR 난독화 후 파일 저장"""
        raw = token.encode()
        obf = bytes(raw[i] ^ APP_SECRET[i % len(APP_SECRET)]
                    for i in range(len(raw)))
        LICENSE_FILE.write_bytes(base64.b64encode(obf))

    def _load(self) -> Optional[str]:
        """저장된 토큰 복호화 후 반환"""
        if not LICENSE_FILE.exists():
            return None
        try:
            obf = base64.b64decode(LICENSE_FILE.read_bytes())
            return bytes(
                obf[i] ^ APP_SECRET[i % len(APP_SECRET)]
                for i in range(len(obf))
            ).decode()
        except Exception:
            return None

    # ── 메인 체크 ────────────────────────────────────────────────

    def is_licensed(self) -> bool:
        """유효한 라이센스 토큰이 있으면 True"""
        token = self._load()
        if not token:
            return False
        data = self._verify_token(token)
        if not data:
            logging.warning("[License] 서명 검증 실패")
            return False
        if data.get("machine_id") != self.get_machine_id():
            logging.warning("[License] 기기 ID 불일치")
            return False
        exp = data.get("expires_at", "9999-12-31")
        try:
            if datetime.now() <= datetime.strptime(exp, "%Y-%m-%d"):
                return True
            logging.warning("[License] 라이센스 기간 만료")
            return False
        except ValueError:
            return True

    def get_info(self) -> Optional[dict]:
        """라이센스 정보 반환 (UI 표시용)"""
        token = self._load()
        if not token:
            return None
        data = self._verify_token(token)
        if data and data.get("machine_id") == self.get_machine_id():
            return data
        return None

    # ── 활성화 ───────────────────────────────────────────────────

    def activate(self, license_key: str) -> Tuple[bool, str]:
        """
        라이센스키 활성화
        Returns: (성공여부, 사용자에게 보여줄 메시지)
        """
        import urllib.request
        import urllib.error
        import json as _json

        key = license_key.strip().upper().replace(" ", "")

        if not self._valid_format(key):
            return False, (
                "올바른 형식이 아닙니다.\n"
                "예)  ANTA-A3F9-B2C1-9D4E"
            )

        machine_id = self.get_machine_id()

        try:
            data = _json.dumps(
                {"license_key": key, "machine_id": machine_id}
            ).encode()
            req = urllib.request.Request(
                f"{SERVER_URL}/activate",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = _json.loads(resp.read().decode())
                token  = result.get("token")
                if not token:
                    return False, "서버 응답 오류: 토큰이 없습니다."
                self._save(token)
                logging.info(f"[License] 활성화 성공: {key[:9]}***")
                return True, "활성화 완료!\n지금부터 프로그램을 사용할 수 있습니다."

        except urllib.error.HTTPError as e:
            try:
                body       = _json.loads(e.read().decode())
                error_code = body.get("error", "")
            except Exception:
                body, error_code = {}, ""

            if e.code == 409 or error_code == "already_activated":
                return False, (
                    "이미 다른 기기에서 활성화된 키입니다.\n"
                    "키는 1개의 기기에서만 사용 가능합니다.\n\n"
                    "다른 기기에서 이전한 경우 고객센터로 문의해주세요."
                )
            if e.code == 404 or error_code == "invalid_key":
                return False, "유효하지 않은 라이센스키입니다.\n키를 다시 확인해주세요."
            msg = body.get("message", f"서버 오류 (코드: {e.code})")
            return False, msg

        except urllib.error.URLError:
            return False, (
                "서버에 연결할 수 없습니다.\n"
                "인터넷 연결을 확인하거나 잠시 후 다시 시도해주세요."
            )
        except TimeoutError:
            return False, "서버 응답 시간 초과. 잠시 후 다시 시도해주세요."
        except Exception as e:
            return False, f"네트워크 오류:\n{e}"

    @staticmethod
    def _valid_format(key: str) -> bool:
        """ANTA-XXXX-XXXX-XXXX 형식 확인"""
        parts = key.split("-")
        if len(parts) != 4:
            return False
        if parts[0] != "ANTA":
            return False
        return all(len(p) == 4 for p in parts[1:])

    def revoke(self):
        """라이센스 삭제 (재설치 / 기기 교체 시)"""
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
            logging.info("[License] 라이센스 삭제됨")
