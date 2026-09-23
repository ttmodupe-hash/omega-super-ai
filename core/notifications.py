"""
OMEGA-LUQI Administrator Notification Gateway

Alerts the platform admin the moment any workflow freezes at the 30% gate -
via Africa's Talking SMS (sandbox or live), console-logged in dev.

FIXED from the pasted version: the endpoint was the marketing website
(africastalking.com) - the SMS API lives at api.africastalking.com/version1/messaging,
with a separate sandbox host. Every alert would have 404'd in production.

Delivery is best-effort by design: a notification failure must NEVER block
or fail the business action that triggered it.
"""
import os
import logging
from typing import Any

import httpx

logger = logging.getLogger("LuqiNotificationEngine")

_LIVE_BASE = "https://api.africastalking.com/version1/messaging"
_SANDBOX_BASE = "https://api.sandbox.africastalking.com/version1/messaging"


class LuqiNotificationGateway:
    def __init__(self):
        self.username = os.getenv("AFRICAS_TALKING_USERNAME", "sandbox")
        self.api_key = os.getenv("AFRICAS_TALKING_API_KEY")
        self.admin_phone = os.getenv("ADMIN_PHONE_NUMBER", "+27800000000")

    def _endpoint(self) -> str:
        return _SANDBOX_BASE if self.username == "sandbox" else _LIVE_BASE

    async def send_gate_lock_alert(self, task_id: str, action_type: str, item_name: str) -> bool:
        """SMS the admin that a workflow froze at the gate. Best-effort."""
        message = (
            "[Luqi-ai GATE ALERT] "
            f"{action_type} for '{item_name}' is frozen at the 30% human gate. "
            f"Task {task_id[:8]} - sign off in the Ops Cockpit."
        )

        if not self.api_key or self.username == "sandbox":
            logger.warning("[notification: stub channel] %s", message)
            return True

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self._endpoint(),
                    data={"username": self.username, "to": self.admin_phone, "message": message},
                    headers={"ApiKey": self.api_key, "Accept": "application/json",
                             "Content-Type": "application/x-www-form-urlencoded"},
                )
                if response.status_code == 201:
                    logger.info("Gate alert SMS sent to %s", self.admin_phone)
                    return True
                logger.error("Notification API error %s: %s", response.status_code, response.text)
                return False
            except httpx.HTTPError as e:
                logger.error("Notification infrastructure unreachable: %s", e)
                return False


_gateway = LuqiNotificationGateway()


def notify_gate_lock(task) -> None:
    """Fire-and-forget gate alert. Called at EVERY site that freezes a task.

    Never raises, never blocks: wrap in a background task and swallow errors."""
    import asyncio
    try:
        asyncio.get_running_loop().create_task(
            _gateway.send_gate_lock_alert(
                str(task.task_id), task.action_type,
                str(task.payload.get("item", "sensitive action")))
        )
    except RuntimeError:
        # No running loop (sync test contexts) - log synchronously instead
        logger.warning("[notification: no event loop] gate frozen: %s %s",
                       task.action_type, task.payload.get("item", ""))
    except Exception as e:  # delivery must never break the business action
        logger.error("Gate notification dispatch failed (non-fatal): %s", e)
