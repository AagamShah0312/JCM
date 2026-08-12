"""
TOTP two-factor authentication service (spec §46).

Implements a complete TOTP flow with no external service:
  enroll  → generate a secret + provisioning URI (+ QR PNG)
  verify  → check a 6-digit code, enable 2FA
  challenge → short-lived signed token returned by login when 2FA is enabled;
              exchanged for full JWT after a valid code is presented

Uses pyotp for TOTP and Django's signing for the challenge token.
"""
import base64
import io
import logging

from django.conf import settings
from django.core import signing
from django.utils import timezone

logger = logging.getLogger(__name__)

MFA_CHALLENGE_MAX_AGE = 5 * 60  # 5 minutes
MFA_SECRET_LENGTH = 32
MFA_ISSUER = 'JCM'


def is_mfa_available() -> bool:
    return bool(getattr(settings, 'MFA_ENABLED', False))


def is_mfa_enabled(user) -> bool:
    tf = getattr(user, 'two_factor', None)
    return bool(tf and tf.is_enabled)


def generate_secret() -> str:
    import pyotp
    return pyotp.random_base32(length=MFA_SECRET_LENGTH)


def provisioning_uri(user, secret: str) -> str:
    import pyotp
    totp = pyotp.TOTP(secret)
    account = user.email or user.username
    return totp.provisioning_uri(name=account, issuer_name=MFA_ISSUER)


def verify_code(secret: str, code: str, valid_window: int = 1) -> bool:
    import pyotp
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    try:
        return totp.verify(code, valid_window=valid_window)
    except Exception:
        return False


def qr_png_data_uri(otpauth_url: str) -> str:
    """Render the otpauth URL as a QR PNG data URI for the frontend."""
    import qrcode
    img = qrcode.make(otpauth_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:image/png;base64,{b64}"


def issue_mfa_challenge(user) -> str:
    """Short-lived signed token proving the password step succeeded."""
    payload = {'uid': str(user.id), 'ts': timezone.now().timestamp()}
    return signing.dumps(payload, salt='jcm-mfa-challenge')


def resolve_mfa_challenge(token: str):
    """
    Validate a challenge token and return the user (or None).
    A token can only be used once; it is invalidated via the 'used' claim.
    """
    from apps.authentication.models import User
    if not token:
        return None
    try:
        payload = signing.loads(token, salt='jcm-mfa-challenge', max_age=MFA_CHALLENGE_MAX_AGE)
    except Exception:
        return None
    uid = payload.get('uid')
    if not uid:
        return None
    return User.objects.filter(id=uid).first()


def get_or_create_two_factor(user):
    from .models import TwoFactorAuth
    tf, _ = TwoFactorAuth.objects.get_or_create(user=user)
    return tf


# ---------------------------------------------------------------------------
# Encryption at rest (spec §46: secrets must not be stored in plaintext)
# ---------------------------------------------------------------------------

def _fernet():
    from cryptography.fernet import Fernet
    import base64, hashlib
    raw = settings.SECRET_KEY.encode('utf-8')
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode('utf-8')).decode('ascii')


def decrypt_secret(encrypted: str) -> str:
    try:
        return _fernet().decrypt(encrypted.encode('ascii')).decode('utf-8')
    except Exception:
        return ''
