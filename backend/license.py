"""
HungArch AI Render — License management.

Flow:
  1. Lần chạy đầu: tạo trial 30 ngày, lưu vào %APPDATA%\\HungArch\\trial.dat (mã hoá).
  2. Sau 30 ngày: mode = "expired", chặn các API sinh ảnh.
  3. Kích hoạt: người dùng nhập key → verify ECDSA → lưu %APPDATA%\\HungArch\\license.dat.

Key format: HUNG-XXXXX-XXXXX-XXXXX-... (BASE32 của machine_prefix + expiry + ECDSA P-256 raw sig)
Total raw: 8 + 8 + 64 = 80 bytes → 128 BASE32 chars → ~26 groups of 5
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

try:
    import winreg as _winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

# ─── Public key (có thể ở trong repo — không thể giả mạo signature nếu không có private key) ───
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEAIU5KTffKUsy0XX7WGEijUpP/OzR
PUBWjMBZEVxJkefciN3+FTON3MrZW26QiHu6vuLan+l5GzhnotwYU0A4kA==
-----END PUBLIC KEY-----"""

TRIAL_DAYS = 30
_APPDATA = Path(os.environ.get("APPDATA", Path.home())) / "HungArch"


# ─── Machine fingerprint ──────────────────────────────────────────────────────

def _raw_machine_guid() -> str:
    """Dùng MachineGuid của Windows (ổn định qua cài đặt lại app)."""
    if _HAS_WINREG:
        try:
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                  r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = _winreg.QueryValueEx(key, "MachineGuid")
            _winreg.CloseKey(key)
            return guid
        except Exception:
            pass
    # Fallback cho non-Windows
    import socket, uuid
    return f"{socket.gethostname()}|{uuid.getnode()}"


def _machine_hash() -> str:
    """SHA-256 của MachineGuid, trả về hex uppercase."""
    return hashlib.sha256(_raw_machine_guid().encode()).hexdigest().upper()


def get_machine_id() -> str:
    """8-char ID hiển thị cho người dùng (để gửi cho developer xin key).
    Format: XXXX-XXXX  (ví dụ: 4A3F-E29C)
    """
    h = _machine_hash()[:8]
    return f"{h[:4]}-{h[4:8]}"


# ─── File helpers ─────────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    """Fernet key dẫn xuất từ machine hash — mã hoá file trial."""
    raw = hashlib.sha256(f"hungarch-trial-{_machine_hash()}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def _appdata() -> Path:
    _APPDATA.mkdir(parents=True, exist_ok=True)
    return _APPDATA


def _trial_path() -> Path:
    return _appdata() / "trial.dat"


def _license_path() -> Path:
    return _appdata() / "license.dat"


# ─── Trial file ───────────────────────────────────────────────────────────────

def _read_trial() -> dict | None:
    p = _trial_path()
    if not p.exists():
        return None
    try:
        data = json.loads(_fernet().decrypt(p.read_bytes()))
        # Kiểm tra file có đúng máy không (chống copy sang máy khác)
        if data.get("mid") != _machine_hash():
            return None
        return data
    except Exception:
        return None


def _write_trial(install_ts: float) -> None:
    payload = json.dumps({"install": install_ts, "mid": _machine_hash(), "v": 1}).encode()
    _trial_path().write_bytes(_fernet().encrypt(payload))


# ─── License key verification ─────────────────────────────────────────────────

def _verify_key(key_str: str) -> dict:
    """Verify ECDSA P-256 signed license key.

    Trả về: {valid: bool, expiry: str|None, days_remaining: int, error: str|None}
    Key structure (BASE32-encoded, 80 bytes total):
        bytes  0-7  : machine_prefix (8 ASCII hex chars)
        bytes  8-15 : expiry_YYYYMMDD (8 ASCII chars)
        bytes 16-47 : ECDSA r (32 bytes big-endian)
        bytes 48-79 : ECDSA s (32 bytes big-endian)
    """
    try:
        clean = key_str.upper().replace("HUNG-", "").replace("-", "").replace(" ", "")
        pad   = (8 - len(clean) % 8) % 8
        raw   = base64.b32decode(clean + "=" * pad)

        if len(raw) < 80:  # 8 + 8 + 64
            return {"valid": False, "error": "Key không đúng định dạng."}

        machine_prefix = raw[:8].decode("ascii")
        expiry_str     = raw[8:16].decode("ascii")   # YYYYMMDD
        sig_raw        = raw[16:80]                  # 64 bytes: r(32) + s(32)

        # Kiểm tra machine prefix
        if _machine_hash()[:8] != machine_prefix:
            return {"valid": False, "error": "Key không phù hợp với máy này."}

        # Chuyển raw (r||s) sang DER để verify ECDSA
        r = int.from_bytes(sig_raw[:32], "big")
        s = int.from_bytes(sig_raw[32:], "big")
        sig_der = encode_dss_signature(r, s)

        pub_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())
        message = (machine_prefix + expiry_str).encode("ascii")
        pub_key.verify(sig_der, message, ec.ECDSA(hashes.SHA256()))

        # Kiểm tra hạn
        expiry = datetime.strptime(expiry_str, "%Y%m%d").date()
        if expiry < date.today():
            return {"valid": False, "error": "License key đã hết hạn."}

        remaining = (expiry - date.today()).days
        return {
            "valid": True,
            "expiry": expiry.strftime("%d/%m/%Y"),
            "days_remaining": remaining,
        }
    except Exception:
        return {"valid": False, "error": "Key không hợp lệ."}


# ─── Public API ───────────────────────────────────────────────────────────────

def get_status() -> dict:
    """Trả về trạng thái license hiện tại.

    {
        mode: "trial" | "licensed" | "expired",
        days_remaining: int,
        expiry: str | None,
        machine_id: str,   # XXXX-XXXX để người dùng gửi cho developer
        message: str,
    }
    """
    mid_display = get_machine_id()

    # 1. Kiểm tra license đã kích hoạt
    lp = _license_path()
    if lp.exists():
        try:
            stored_key = lp.read_text(encoding="utf-8").strip()
            r = _verify_key(stored_key)
            if r["valid"]:
                return {
                    "mode": "licensed",
                    "days_remaining": r["days_remaining"],
                    "expiry": r["expiry"],
                    "machine_id": mid_display,
                    "message": f"Bản quyền hợp lệ đến {r['expiry']}.",
                }
        except Exception:
            pass

    # 2. Kiểm tra trial
    trial = _read_trial()
    if trial is None:
        _write_trial(time.time())
        trial = _read_trial()

    if trial:
        elapsed = (time.time() - trial["install"]) / 86400
        days_left = max(0, TRIAL_DAYS - int(elapsed))
        if days_left > 0:
            return {
                "mode": "trial",
                "days_remaining": days_left,
                "expiry": None,
                "machine_id": mid_display,
                "message": f"Đang dùng thử — còn {days_left} ngày.",
            }

    # 3. Hết hạn
    return {
        "mode": "expired",
        "days_remaining": 0,
        "expiry": None,
        "machine_id": mid_display,
        "message": "Hết hạn dùng thử. Liên hệ tashume.jsc@gmail.com để kích hoạt.",
    }


def activate(key: str) -> dict:
    """Kích hoạt license key. Trả về {success: bool, message: str}."""
    r = _verify_key(key)
    if not r["valid"]:
        return {"success": False, "message": r["error"]}
    _license_path().write_text(key.strip(), encoding="utf-8")
    return {
        "success": True,
        "message": f"Kích hoạt thành công! Bản quyền đến {r['expiry']} ({r['days_remaining']} ngày).",
    }
