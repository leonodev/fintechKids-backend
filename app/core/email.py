from __future__ import annotations

import html
import logging

import httpx

from app.core.config import settings
from app.core.errors import AppHTTPException, ErrorCode

logger = logging.getLogger(__name__)

RESEND_EMAILS_URL = "https://api.resend.com/emails"


def _build_recovery_email_html(
    family_name: str,
    recovery_code: str,
    expires_in_minutes: int,
) -> str:
    """Build a clean transactional HTML email for the 6-digit recovery code."""
    safe_family = html.escape(family_name or "Family")
    safe_code = html.escape(recovery_code)
    return (
        "<!DOCTYPE html>"
        "<html lang=\"en\">"
        "<body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
        "background-color: #f6f8fb; margin: 0; padding: 24px; color: #1f2937;\">"
        "<div style=\"max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; "
        "padding: 32px; border: 1px solid #e5e7eb;\">"
        "<h2 style=\"margin: 0 0 12px; color: #111827;\">FintechKids Password Recovery</h2>"
        f"<p style=\"margin: 0 0 16px; line-height: 1.5;\">Hello <strong>{safe_family}</strong>,</p>"
        "<p style=\"margin: 0 0 20px; line-height: 1.5;\">"
        "Use the 6-digit verification code below to reset your parent account password:"
        "</p>"
        "<div style=\"text-align: center; margin: 24px 0;\">"
        f"<span style=\"display: inline-block; font-size: 32px; font-weight: 700; letter-spacing: 6px; "
        f"padding: 14px 24px; background: #f3f4f6; border-radius: 8px; color: #111827;\">{safe_code}</span>"
        "</div>"
        f"<p style=\"margin: 0 0 12px; font-size: 14px; color: #4b5563;\">"
        f"This code expires in <strong>{expires_in_minutes} minutes</strong>."
        "</p>"
        "<p style=\"margin: 0; font-size: 13px; color: #6b7280;\">"
        "If you did not request a password reset, you can safely ignore this email."
        "</p>"
        "</div>"
        "</body>"
        "</html>"
    )


def send_password_recovery_email(
    to_email: str,
    recovery_code: str,
    family_name: str,
    expires_in_minutes: int,
) -> bool:
    """Send the 6-digit password recovery email via Resend HTTPS API.

    Returns True when an email was dispatched via Resend, or False when running
    in non-production environments without RESEND_API_KEY configured.
    Raises AppHTTPException in production if unconfigured or when Resend rejects/fails.
    """
    api_key = settings.RESEND_API_KEY.strip()
    is_production = settings.ENVIRONMENT.strip().lower() == "production"

    if not api_key:
        if is_production:
            logger.error("RESEND_API_KEY is missing in production; cannot send recovery email.")
            raise AppHTTPException(error_code=ErrorCode.EMAIL_SERVICE_NOT_CONFIGURED)
        logger.info("RESEND_API_KEY not configured in %s; skipping external email delivery.", settings.ENVIRONMENT)
        return False

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": "FintechKids - Password Recovery Code",
        "html": _build_recovery_email_html(
            family_name=family_name,
            recovery_code=recovery_code,
            expires_in_minutes=expires_in_minutes,
        ),
        "text": (
            f"Hello {family_name or 'Family'},\n\n"
            f"Your FintechKids 6-digit password recovery code is: {recovery_code}\n"
            f"This code expires in {expires_in_minutes} minutes.\n\n"
            "If you did not request a password reset, you can safely ignore this email."
        ),
    }

    try:
        response = httpx.post(
            RESEND_EMAILS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.EMAIL_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.error("Resend HTTP request error while sending recovery email to %s: %s", to_email, exc)
        raise AppHTTPException(error_code=ErrorCode.EMAIL_DELIVERY_FAILED) from exc

    if response.status_code >= 400:
        logger.error(
            "Resend API rejected recovery email to %s with status %s: %s",
            to_email,
            response.status_code,
            response.text,
        )
        raise AppHTTPException(error_code=ErrorCode.EMAIL_DELIVERY_FAILED)

    return True
