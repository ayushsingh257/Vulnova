"""TOTP (Time-based One-Time Password) Service.

Provides RFC 6238 compliant TOTP secret generation, provisioning URI construction,
QR code Base64 rendering, and OTP verification with drift tolerance.
"""

import base64
from io import BytesIO

import pyotp
import qrcode
import structlog

logger = structlog.get_logger(__name__)

ISSUER_NAME = "Vulnova"


class TOTPService:
    """Service wrapping pyotp and qrcode for RFC 6238 TOTP operations."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a cryptographically secure Base32 TOTP secret key."""
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, user_email: str) -> str:
        """Generate a standard otpauth:// provisioning URI for authenticator apps."""
        totp = pyotp.TOTP(secret, name=user_email, issuer=ISSUER_NAME)
        return totp.provisioning_uri(name=user_email, issuer_name=ISSUER_NAME)

    @staticmethod
    def generate_qr_code_base64(provisioning_uri: str) -> str:
        """Generate a Base64-encoded PNG image string of the provisioning URI QR code."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    @staticmethod
    def verify_totp_code(secret: str, code: str) -> bool:
        """Verify a 6-digit OTP code against the TOTP secret key with a 30s drift window."""
        if not secret or not code:
            return False

        code_clean = code.strip().replace(" ", "")
        if not code_clean.isdigit() or len(code_clean) != 6:
            return False

        try:
            totp = pyotp.TOTP(secret)
            # valid_window=1 allows 1 step (30 sec) before or after current time
            return bool(totp.verify(code_clean, valid_window=1))
        except Exception as err:
            logger.warning("totp_verification_failed", error=str(err))
            return False
