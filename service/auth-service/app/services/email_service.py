import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Template


load_dotenv()


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Relay")

FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")

TEMPLATE_DIR = (
    Path(__file__).resolve().parent.parent / "templates"
)


def send_verification_email(
    email: str,
    name: str,
    token: str,
    expiration_minutes: int,
) -> None:

    verification_url = (
        f"{FRONTEND_URL}/verify-email?token={token}"
    )

    template_path = TEMPLATE_DIR / "email_verification.html"

    template = Template(
        template_path.read_text(encoding="utf-8")
    )

    html_content = template.render(
        name=name,
        verification_url=verification_url,
        expiration_minutes=expiration_minutes,
    )

    message = EmailMessage()

    message["Subject"] = "Verify your Relay account"
    message["From"] = (
        f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    )
    message["To"] = email

    message.set_content(
        "Please verify your Relay account using "
        "the verification link."
    )

    message.add_alternative(
        html_content,
        subtype="html",
    )

    try:
        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
        ) as smtp:

            smtp.starttls()

            smtp.login(
                SMTP_USERNAME,
                SMTP_PASSWORD,
            )

            smtp.send_message(message)
    except Exception as exc:
        print(f"Error sending verification email to {email}: {exc}")
        raise


def send_password_reset_email(
    email: str,
    name: str,
    token: str,
    expiration_minutes: int,
) -> None:

    reset_url = (
        f"{FRONTEND_URL}/reset-password?token={token}"
    )

    template_path = (
        TEMPLATE_DIR / "password_reset.html"
    )

    template = Template(
        template_path.read_text(encoding="utf-8")
    )

    html_content = template.render(
        name=name,
        reset_url=reset_url,
        expiration_minutes=expiration_minutes,
    )

    message = EmailMessage()

    message["Subject"] = "Reset your Relay password"
    message["From"] = (
        f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    )
    message["To"] = email

    message.set_content(
        "Use the password reset link to reset "
        "your Relay account password."
    )

    message.add_alternative(
        html_content,
        subtype="html",
    )

    try:
        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
        ) as smtp:

            smtp.starttls()

            smtp.login(
                SMTP_USERNAME,
                SMTP_PASSWORD,
            )

            smtp.send_message(message)

    except Exception as exc:
        print(
            f"Error sending password reset email "
            f"to {email}: {exc}"
        )
        raise