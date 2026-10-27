import hashlib
import hmac

from app.config import settings


def verify_github_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verifies that an incoming webhook payload was signed by GitHub using our secret.

    Prevents spoofing and timing attacks.
    """
    secret = settings.GITHUB_WEBHOOK_SECRET

    # If no secret is configured in development, skip or fail safely
    if not secret:
        # In production this should always be configured
        return False

    if not signature_header:
        return False

    # The header format is "sha256=<hex_digest>"
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header.split("sha256=")[1].strip()

    # Calculate HMAC-SHA256 over the raw bytes
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    )
    computed_signature = mac.hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, expected_signature)
