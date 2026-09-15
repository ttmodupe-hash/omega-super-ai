"""
OMEGA-LUQI Progress Alerts - notify students when a module unlocks.

Channels (all env-gated, fail-closed, delivery failures never break the
unlock path):
  - WhatsApp via Twilio (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN /
    TWILIO_WHATSAPP_FROM=whatsapp:+...); requires the student's phone on
    their profile (PHONE_NUMBER field added to memory-style store).
  - SMS via the existing Africa's Talking gateway as fallback channel.
No creds -> silent skip (by design, like all engine alerting).
"""
import os
from typing import Optional

import requests

from .auth import UserSessionProfile

_student_phones: dict = {}


def set_student_phone(user_id: str, phone: str) -> None:
    _student_phones[user_id] = phone


def get_student_phone(user_id: str) -> Optional[str]:
    return _student_phones.get(user_id)


def format_unlock_message(skill: str, total_skills: int, hours: int) -> str:
    return (f"Congratulations! Module unlocked: {skill}. "
            f"You now hold {total_skills} verified skills ({hours} credit hours) "
            f"on Luqi-AI. View your certificates on the dashboard.")


def notify_module_unlock(user: UserSessionProfile, skill: str, total: int, hours: int) -> dict:
    """Fire-and-forget student notification. Never raises."""
    msg = format_unlock_message(skill, total, hours)
    phone = get_student_phone(str(user.user_id))
    sent = {"whatsapp": False, "sms": False}
    if not phone:
        return {"notified": False, "reason": "no phone on profile", **sent}

    sid, tok, wa_from = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"),
                         os.getenv("TWILIO_WHATSAPP_FROM"))
    if sid and tok and wa_from:
        try:
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data={"From": wa_from, "To": f"whatsapp:{phone}", "Body": msg},
                auth=(sid, tok), timeout=10)
            sent["whatsapp"] = r.status_code in (200, 201)
        except requests.exceptions.RequestException:
            pass
    if not sent["whatsapp"]:
        try:
            from .notifications import _gateway
            import asyncio
            asyncio.get_running_loop().create_task(_gateway.send_gate_lock_alert("UNLOCK", "module", msg))
            sent["sms"] = True
        except Exception:
            pass
    return {"notified": any(sent.values()), "phone_tail": phone[-4:], **sent}
