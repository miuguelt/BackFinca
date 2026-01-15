import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from flask import current_app

logger = logging.getLogger(__name__)


def _get_config(name: str, default=None):
    try:
        return current_app.config.get(name, default)
    except Exception:
        return os.getenv(name, default)


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _append_token(url: str, token: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["token"] = token
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def build_password_reset_link(reset_token: str) -> str:
    if not reset_token:
        return ""

    url_template = _get_config("PASSWORD_RESET_URL")
    if url_template:
        if "{token}" in url_template:
            return url_template.replace("{token}", quote(reset_token))
        return _append_token(url_template, reset_token)

    frontend_url = _get_config("FRONTEND_URL")
    if not frontend_url:
        frontend_url = (
            _get_config("BACKEND_URL")
            or _get_config("API_BASE_URL_NO_VERSION")
            or _get_config("API_BASE_URL")
        )
    if not frontend_url:
        scheme = _get_config("FRONTEND_PROTOCOL") or _get_config("BACKEND_PROTOCOL") or "http"
        host = _get_config("FRONTEND_HOST") or _get_config("BACKEND_HOST")
        port = _get_config("FRONTEND_PORT") or _get_config("BACKEND_PORT")
        if host:
            frontend_url = f"{scheme}://{host}"
            if port:
                frontend_url = f"{frontend_url}:{port}"

    reset_path = _get_config("FRONTEND_PASSWORD_RESET_PATH", "/reset-password") or "/reset-password"
    if frontend_url:
        base = str(frontend_url).rstrip("/")
        if not str(reset_path).startswith("/"):
            reset_path = f"/{reset_path}"
        return _append_token(f"{base}{reset_path}", reset_token)

    return _append_token(str(reset_path), reset_token)


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    if not to_email:
        return False, "missing_recipient"

    if not _as_bool(_get_config("EMAIL_ENABLED", True), default=True):
        return False, "email_disabled"

    host = _get_config("SMTP_HOST")
    if not host:
        return False, "smtp_host_missing"

    port = _get_config("SMTP_PORT", 587)
    try:
        port = int(port)
    except Exception:
        port = 587

    username = _get_config("SMTP_USERNAME") or _get_config("SMTP_USER")
    password = _get_config("SMTP_PASSWORD")
    from_email = _get_config("SMTP_FROM_EMAIL") or username
    from_name = _get_config("SMTP_FROM_NAME") or ""
    if not from_email:
        return False, "smtp_from_missing"

    use_ssl = _as_bool(_get_config("SMTP_USE_SSL", False), default=False)
    use_tls = _as_bool(_get_config("SMTP_USE_TLS", True), default=True)
    timeout = _get_config("SMTP_TIMEOUT", 10)
    try:
        timeout = int(timeout)
    except Exception:
        timeout = 10

    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["Subject"] = subject or ""
    msg.set_content(body_text or "")
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
        return True, None
    except Exception as exc:
        logger.error("Error sending email: %s", exc, exc_info=True)
        return False, str(exc)
