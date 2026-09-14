import os
import logging
from typing import List, Dict, Any
import requests

logger = logging.getLogger("cncf_tracker")


class Notifier:
    """Dispatches alerts to Discord, Telegram, or Slack webhooks."""

    def __init__(self):
        self.discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
        self.slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        self.tg_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    def notify(self, issues: List[Dict[str, Any]], hours: int = 28) -> None:
        """Sends clean notifications to configured channels."""
        if not issues:
            return

        lines = [f"New issues found in last {hours} hours:"]
        for iss in issues:
            lines.append(f"- [{iss['repo']}] #{iss['number']} {iss['title']} ({iss['url']})")

        message = "\n".join(lines)

        if self.discord_webhook:
            try:
                requests.post(self.discord_webhook, json={"content": message}, timeout=10)
            except Exception as e:
                logger.error(f"Discord notification error: {e}")

        if self.slack_webhook:
            try:
                requests.post(self.slack_webhook, json={"text": message}, timeout=10)
            except Exception as e:
                logger.error(f"Slack notification error: {e}")

        if self.tg_bot_token and self.tg_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.tg_bot_token}/sendMessage"
                payload = {
                    "chat_id": self.tg_chat_id,
                    "text": message,
                    "disable_web_page_preview": True,
                }
                requests.post(url, json=payload, timeout=10)
            except Exception as e:
                logger.error(f"Telegram notification error: {e}")
