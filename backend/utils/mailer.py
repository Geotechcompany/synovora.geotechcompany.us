"""SMTP helper for emailing generated posts."""

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, List, Optional


class EmailSender:
    """Simple SMTP wrapper with Gmail-friendly defaults."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sender_email: Optional[str] = None,
    ) -> None:
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT", 587))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.sender_email = sender_email or os.getenv("EMAIL_FROM") or self.smtp_user

        missing = [
            name
            for name, value in [
                ("SMTP_USER", self.smtp_user),
                ("SMTP_PASSWORD", self.smtp_password),
                ("EMAIL_FROM", self.sender_email),
            ]
            if not value
        ]
        if missing:
            raise ValueError(f"Missing SMTP configuration values: {', '.join(missing)}")

    def send_email(
        self,
        recipients: Iterable[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> None:
        """Send an email via SMTP with optional HTML and attachments."""
        recipients = [addr.strip() for addr in recipients if addr and addr.strip()]
        if not recipients:
            raise ValueError("At least one recipient email is required")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(recipients)
        msg.set_content(text_body)

        if html_body:
            msg.add_alternative(html_body, subtype="html")

        for attachment in attachments or []:
            content = attachment.get("content")
            filename = attachment.get("filename", "attachment")
            mime_type = attachment.get("mime_type", "application/octet-stream")
            maintype, _, subtype = mime_type.partition("/")
            msg.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype or "octet-stream",
                filename=filename,
            )

        context = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls(context=context)
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)




