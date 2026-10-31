import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import integer

load_dotenv()


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = integer("SMTP_PORT", 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Relay")

FRONTEND_URL = os.getenv("FRONTEND_URL")

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATES = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
# Copy of frontend/public/brand/relay/relay-light.png, bundled for standalone deployments.
LOGO_PATH = TEMPLATE_DIR / "assets" / "relay-light.png"


def _send_email(
    email: str,
    subject: str,
    template_name: str,
    text_content: str,
    **context,
) -> None:
    logo_cid = make_msgid(domain="relay")
    html_content = TEMPLATES.get_template(template_name).render(
        **context,
        logo_cid=logo_cid[1:-1],
        year=datetime.now(timezone.utc).year,
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = email
    message.set_content(text_content)
    message.add_alternative(html_content, subtype="html")
    # Related inline images travel with the HTML, without a public asset host.
    message.get_body(preferencelist=("html",)).add_related(
        LOGO_PATH.read_bytes(),
        maintype="image",
        subtype="png",
        cid=logo_cid,
        disposition="inline",
        filename="relay-logo.png",
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


def send_verification_email(
    email: str,
    name: str,
    token: str,
    expiration_minutes: int,
) -> None:
    verification_url = f"{FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
    minutes_label = "minute" if expiration_minutes == 1 else "minutes"
    _send_email(
        email,
        "Verify your Relay account",
        "email_verification.html",
        f"Hi {name or 'there'},\n\n"
        "Thanks for joining Relay. Confirm your email address to finish setting up "
        "your account and start building your workflows.\n\n"
        f"Verify email address: {verification_url}\n\n"
        f"This link expires in {expiration_minutes} {minutes_label}.\n\n"
        "If you didn't create a Relay account, you can safely ignore this email.\n\n"
        "Relay — Your workflows. Your control.",
        name=name,
        verification_url=verification_url,
        expiration_minutes=expiration_minutes,
    )


def send_password_reset_email(
    email: str,
    name: str,
    token: str,
    expiration_minutes: int,
) -> None:
    reset_url = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    minutes_label = "minute" if expiration_minutes == 1 else "minutes"
    _send_email(
        email,
        "Reset your Relay password",
        "password_reset.html",
        f"Hi {name or 'there'},\n\n"
        "We received a request to reset the password for your Relay account. "
        "Use the link below to choose a new password.\n\n"
        f"Reset password: {reset_url}\n\n"
        f"This link expires in {expiration_minutes} {minutes_label}.\n\n"
        "If you didn't request a password reset, you can safely ignore this email. "
        "Your password will stay the same.\n\n"
        "Relay — Your workflows. Your control.",
        name=name,
        reset_url=reset_url,
        expiration_minutes=expiration_minutes,
    )
