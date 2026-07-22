# server/app/auth.py
#
# Password hashing (bcrypt) + a small self-contained signed-token scheme.
#
# We deliberately don't use PyJWT/python-jose here: both pull in the
# `cryptography` package even for pure-HMAC (HS256) tokens, and that's an
# unnecessary heavyweight (and occasionally broken, e.g. in some minimal
# container images) dependency for something this simple. A signed token is
# just base64url(json(payload)) + "." + HMAC-SHA256(secret, that string) —
# tamper-evident and time-limited, which is all we need here.

import base64
import hashlib
import hmac
import json
import time

import bcrypt

from . import config


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_token(payload: dict, lifetime_seconds: int) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + lifetime_seconds
    body["iat"] = int(time.time())
    encoded = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(config.SECRET_KEY.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def verify_token(token: str) -> dict | None:
    """Return the decoded payload if the token's signature is valid and it
    hasn't expired, else None."""
    try:
        encoded, sig = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(config.SECRET_KEY.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(encoded))
    except (ValueError, UnicodeDecodeError):
        return None

    if payload.get("exp", 0) < time.time():
        return None

    return payload
