# utils/hls_signing.py
import os
import time
import hmac
import json
import base64
import hashlib
from typing import Optional, Tuple

# Configure via env; fall back to a dev-safe default (override in prod!)
_HLS_SECRET = (os.environ.get("HLS_SIGNING_SECRET") or "dev-only-please-change").encode("utf-8")

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))

def _now() -> int:
    return int(time.time())

def make_hls_token(*, user_id: int, song_id: int, ttl_seconds: int = 300) -> str:
    """
    Create a signed token encoding (user_id, song_id, exp).
    TTL defaults to 5 minutes — safe for HLS fetching bursts.
    """
    payload = {"u": user_id, "s": song_id, "exp": _now() + ttl_seconds}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    p = _b64url_encode(payload_bytes)
    sig = hmac.new(_HLS_SECRET, p.encode("ascii"), hashlib.sha256).digest()
    return f"{p}.{_b64url_encode(sig)}"

def verify_hls_token(token: str, expected_song_id: int) -> Tuple[bool, Optional[str]]:
    """
    Verify signature, expiry, and song binding.
    Returns (ok, error_message_if_any).
    """
    try:
        p, s = token.split(".", 1)
    except ValueError:
        return False, "Malformed token"

    try:
        sig_ok = hmac.compare_digest(
            _b64url_decode(s),
            hmac.new(_HLS_SECRET, p.encode("ascii"), hashlib.sha256).digest(),
        )
        if not sig_ok:
            return False, "Bad signature"

        payload = json.loads(_b64url_decode(p))
        if not isinstance(payload, dict):
            return False, "Bad payload"

        exp = int(payload.get("exp", 0))
        if _now() > exp:
            return False, "Token expired"

        song_id = int(payload.get("s", -1))
        if song_id != int(expected_song_id):
            return False, "Song mismatch"

        # user_id is available in payload.get("u") if you want to log/attach later
        return True, None
    except Exception as e:
        return False, f"Invalid token: {e}"
