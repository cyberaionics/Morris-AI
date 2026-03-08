"""
Simulated email communication service.
Generates and logs professional HR emails.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory email log
_sent_emails: list[dict] = []


def send_email(recipient: str, subject: str, body: str) -> str:
    """Simulate sending a professional email.

    Logs the email and returns a confirmation. In production, this would
    integrate with an SMTP service or email API.

    Args:
        recipient: Recipient email address.
        subject: Email subject line.
        body: Email body content.

    Returns:
        Confirmation message with timestamp.
    """
    try:
        timestamp = datetime.now().isoformat()
        email_record = {
            "to": recipient,
            "subject": subject,
            "body": body,
            "sent_at": timestamp,
            "status": "delivered",
        }
        _sent_emails.append(email_record)

        logger.info("Email sent to %s: %s", recipient, subject)

        return (
            f"✅ Email Sent Successfully\n"
            f"  To: {recipient}\n"
            f"  Subject: {subject}\n"
            f"  Sent at: {timestamp}\n"
            f"  Status: Delivered (simulated)"
        )
    except Exception as e:
        logger.error("Email sending failed: %s", e)
        return f"Failed to send email: {str(e)}"


def get_sent_emails() -> list[dict]:
    """Return all sent email records."""
    return list(_sent_emails)
