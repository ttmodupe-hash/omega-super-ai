"""Luqi AI - Email System

Transactional emails for subscriptions, notifications, and user engagement.
Supports SendGrid, SMTP fallback, and mock mode for development.

Setup:
    $env:SENDGRID_API_KEY="SG.your-key"
    # OR
    $env:SMTP_HOST="smtp.gmail.com"
    $env:SMTP_USER="your@email.com"
    $env:SMTP_PASS="your-app-password"
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# -- Configuration --

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "hello@luqi-ai.com")
FROM_NAME = os.environ.get("FROM_NAME", "Luqi AI")

# -- Templates --

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to Luqi AI - Your AI journey starts now",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Welcome to Luqi AI!</h1>
            <p>Hi {{name}},</p>
            <p>We're thrilled to have you on board. Luqi AI is your companion for work, learning, and life.</p>
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Here's what you can do:</h3>
                <ul>
                    <li>Chat with AI in 85 languages</li>
                    <li>Generate code in 25+ programming languages</li>
                    <li>Build websites with AI</li>
                    <li>Learn anything with adaptive tutoring</li>
                    <li>Track habits and grow daily</li>
                </ul>
            </div>
            <a href="https://luqi-ai.com" style="background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Get Started</a>
            <p style="color: #6b7280; margin-top: 30px;">Built with passion for Africa and the world.</p>
        </div>
        """,
        "text": "Welcome to Luqi AI! We're thrilled to have you. Visit https://luqi-ai.com to get started."
    },

    "subscription_welcome": {
        "subject": "You're now a Luqi AI {{plan}} member!",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Thank you for subscribing!</h1>
            <p>Hi {{name}},</p>
            <p>Your <strong>{{plan}}</strong> subscription is now active.</p>
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Your plan includes:</h3>
                <ul>{{features}}</ul>
            </div>
            <p>Next billing date: {{next_billing_date}}</p>
            <a href="https://luqi-ai.com/subscription" style="background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Manage Subscription</a>
        </div>
        """,
    },

    "payment_receipt": {
        "subject": "Receipt for your Luqi AI {{plan}} subscription",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Payment Receipt</h1>
            <table style="width: 100%; margin: 20px 0;">
                <tr><td><strong>Plan:</strong></td><td>{{plan}}</td></tr>
                <tr><td><strong>Amount:</strong></td><td>{{amount}}</td></tr>
                <tr><td><strong>Date:</strong></td><td>{{date}}</td></tr>
                <tr><td><strong>Invoice ID:</strong></td><td>{{invoice_id}}</td></tr>
            </table>
            <p>Thank you for your business!</p>
        </div>
        """,
    },

    "payment_failed": {
        "subject": "Action required: Update your payment method",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #dc2626;">Payment Failed</h1>
            <p>We couldn't process your payment for {{plan}}.</p>
            <p>Please update your payment method to avoid interruption.</p>
            <a href="https://luqi-ai.com/subscription" style="background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Update Payment</a>
        </div>
        """,
    },

    "cancellation": {
        "subject": "Your Luqi AI subscription has been cancelled",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Subscription Cancelled</h1>
            <p>Your {{plan}} subscription will end on {{end_date}}.</p>
            <p>You can resubscribe anytime to keep your data and settings.</p>
            <a href="https://luqi-ai.com/subscription" style="background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Resubscribe</a>
        </div>
        """,
    },

    "habit_reminder": {
        "subject": "Don't break the streak! {{habit_name}}",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Habit Reminder</h1>
            <p>Current streak: <strong>{{streak}} days</strong></p>
            <p>Time for: {{habit_name}}</p>
            <a href="https://luqi-ai.com?tab=habits" style="background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Track Now</a>
        </div>
        """,
    },

    "daily_digest": {
        "subject": "Your Luqi AI Daily Summary",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Daily Summary</h1>
            <div style="background: #f3f4f6; padding: 20px; border-radius: 8px;">
                <p>Messages sent: {{message_count}}</p>
                <p>Goals progress: {{goals_progress}}</p>
                <p>Habits tracked: {{habits_tracked}}</p>
            </div>
        </div>
        """,
    },

    "password_reset": {
        "subject": "Reset your Luqi AI password",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4f46e5;">Password Reset</h1>
            <p>Click the link below to reset your password:</p>
            <a href="{{reset_url}}" style="background: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a>
            <p style="color: #6b7280;">This link expires in 1 hour.</p>
        </div>
        """,
    },
}

# -- Core Functions --


def is_configured() -> bool:
    """Check if any email provider is configured."""
    return bool(SENDGRID_API_KEY) or bool(SMTP_HOST)


def render_template(template_name: str, **kwargs) -> dict:
    """Render an email template with variables."""
    template = EMAIL_TEMPLATES.get(template_name, {})
    subject = template.get("subject", "")
    html = template.get("html", "")
    text = template.get("text", "")

    for key, value in kwargs.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value))
        html = html.replace(placeholder, str(value))
        if text:
            text = text.replace(placeholder, str(value))

    return {"subject": subject, "html": html, "text": text}


def send_email(to_email: str, template_name: str, **kwargs) -> dict:
    """Send an email using the best available provider.

    Priority: SendGrid > SMTP > Mock (logs only)
    """
    if not is_configured():
        logger.info(
            "[MOCK EMAIL] To: %s, Template: %s", to_email, template_name
        )
        return {
            "sent": False,
            "mock": True,
            "message": "Email not configured. Set SENDGRID_API_KEY or SMTP_HOST.",
        }

    rendered = render_template(template_name, **kwargs)

    if SENDGRID_API_KEY:
        return _send_sendgrid(to_email, rendered)
    return _send_smtp(to_email, rendered)


def _send_sendgrid(to_email: str, rendered: dict) -> dict:
    """Send via SendGrid API."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=f"{FROM_NAME} <{FROM_EMAIL}>",
            to_emails=to_email,
            subject=rendered["subject"],
            html_content=rendered["html"],
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return {
            "sent": True,
            "provider": "sendgrid",
            "status_code": response.status_code,
        }
    except ImportError:
        logger.warning("sendgrid not installed. Falling back to SMTP/mock.")
        if SMTP_HOST:
            return _send_smtp(to_email, rendered)
        return {
            "sent": False,
            "error": "SendGrid not installed and SMTP not configured",
        }
    except Exception as exc:
        logger.error("SendGrid error: %s", exc)
        return {"sent": False, "error": str(exc)}


def _send_smtp(to_email: str, rendered: dict) -> dict:
    """Send via SMTP."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = rendered["subject"]
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to_email

        if rendered.get("text"):
            msg.attach(MIMEText(rendered["text"], "plain"))
        msg.attach(MIMEText(rendered["html"], "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())

        return {"sent": True, "provider": "smtp"}
    except Exception as exc:
        logger.error("SMTP error: %s", exc)
        return {"sent": False, "error": str(exc)}


# -- Convenience Functions --


def send_welcome_email(to_email: str, name: str = "") -> dict:
    """Send welcome email to new user."""
    return send_email(to_email, "welcome", name=name or "there")


def send_subscription_email(
    to_email: str,
    plan: str,
    name: str = "",
    next_billing_date: str = "",
    features: str = "",
) -> dict:
    """Send subscription confirmation."""
    return send_email(
        to_email,
        "subscription_welcome",
        plan=plan,
        name=name or "there",
        next_billing_date=next_billing_date,
        features=features,
    )


def send_receipt(
    to_email: str, plan: str, amount: str, date: str, invoice_id: str
) -> dict:
    """Send payment receipt."""
    return send_email(
        to_email,
        "payment_receipt",
        plan=plan,
        amount=amount,
        date=date,
        invoice_id=invoice_id,
    )


def send_payment_failure(to_email: str, plan: str) -> dict:
    """Send payment failure notification."""
    return send_email(to_email, "payment_failed", plan=plan)


def send_habit_reminder(to_email: str, habit_name: str, streak: int) -> dict:
    """Send habit streak reminder."""
    return send_email(
        to_email, "habit_reminder", habit_name=habit_name, streak=streak
    )


def send_daily_digest(
    to_email: str,
    message_count: int,
    goals_progress: str,
    habits_tracked: int,
) -> dict:
    """Send daily summary email."""
    return send_email(
        to_email,
        "daily_digest",
        message_count=message_count,
        goals_progress=goals_progress,
        habits_tracked=habits_tracked,
    )


def send_password_reset(to_email: str, reset_url: str) -> dict:
    """Send password reset email."""
    return send_email(to_email, "password_reset", reset_url=reset_url)


# -- Batch / Bulk Send (optional utility) --


def send_bulk(
    recipients: list[dict],
    template_name: str,
    per_recipient_kwargs: bool = True,
) -> list[dict]:
    """Send the same template to multiple recipients.

    Each item in *recipients* is a dict with at minimum::

        {"email": "user@example.com"}

    When *per_recipient_kwargs* is True every remaining key in the dict is
    forwarded as a template variable to :func:`send_email`.

    Returns a list of result dicts in the same order as *recipients*.
    """
    results: list[dict] = []
    for item in recipients:
        email = item.pop("email")
        if per_recipient_kwargs:
            result = send_email(email, template_name, **item)
        else:
            result = send_email(email, template_name)
        results.append(result)
    return results


if __name__ == "__main__":
    # Simple sanity-check: render every template in mock mode.
    import json

    test_cases = [
        ("welcome", {"name": "Ada"}),
        ("subscription_welcome", {
            "name": "Ada", "plan": "Pro", "features": "<li>Everything</li>",
            "next_billing_date": "2025-08-01"
        }),
        ("payment_receipt", {
            "plan": "Pro", "amount": "$9.99", "date": "2025-07-01",
            "invoice_id": "INV-12345"
        }),
        ("payment_failed", {"plan": "Pro"}),
        ("cancellation", {"plan": "Pro", "end_date": "2025-07-31"}),
        ("habit_reminder", {"habit_name": "Morning Jog", "streak": 12}),
        ("daily_digest", {
            "message_count": 42, "goals_progress": "3/5",
            "habits_tracked": 7
        }),
        ("password_reset", {"reset_url": "https://luqi-ai.com/reset?token=abc"}),
    ]

    for t_name, kwargs in test_cases:
        rendered = render_template(t_name, **kwargs)
        print(f"\n--- {t_name} ---")
        print(f"Subject : {rendered['subject']}")
        print(f"HTML len: {len(rendered['html'])}")
        if rendered.get("text"):
            print(f"Text    : {rendered['text'][:80]}...")
        else:
            print("Text    : (none)")

    print("\n\nAll templates rendered successfully.")
