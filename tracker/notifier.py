import os
import logging
from typing import List, Dict, Any
import requests

logger = logging.getLogger("cncf_tracker")


class Notifier:
    """Dispatches real-time alerts to Discord, Telegram, or Slack webhooks."""

    def __init__(self):
        self.discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
        self.slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        self.tg_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    def notify(self, issues: List[Dict[str, Any]], hours: int = 28) -> None:
        """Sends summary notifications to all configured channels."""
        if not issues:
            logger.info("No issues found; skipping external notifications.")
            return

        summary_text = (
            f"🚀 **CNCF Daily Issue Alert (LFX Mentorship)**\n"
            f"Found **{len(issues)}** new beginner/mentorship issues in the last {hours} hours!\n\n"
        )

        # Highlight top 5 issues
        top_issues = issues[:5]
        details = []
        for iss in top_issues:
            details.append(f"• **[{iss['repo']}]** [{iss['title']}]({iss['url']}) (`{iss['language']}`)")

        message = summary_text + "\n".join(details)
        if len(issues) > 5:
            message += f"\n\n... and **{len(issues) - 5} more issues** on the GitHub dashboard."

        if self.discord_webhook:
            self._send_discord(message)

        if self.slack_webhook:
            self._send_slack(message)

        if self.tg_bot_token and self.tg_chat_id:
            self._send_telegram(message)

    def _send_discord(self, message: str) -> None:
        try:
            resp = requests.post(self.discord_webhook, json={"content": message}, timeout=10)
            if resp.status_code in (200, 204):
                logger.info("Discord notification sent successfully.")
            else:
                logger.warning(f"Discord notification failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error sending Discord webhook: {e}")

    def _send_slack(self, message: str) -> None:
        try:
            resp = requests.post(self.slack_webhook, json={"text": message}, timeout=10)
            if resp.status_code == 200:
                logger.info("Slack notification sent successfully.")
            else:
                logger.warning(f"Slack notification failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error sending Slack webhook: {e}")

    def _send_telegram(self, message: str) -> None:
        try:
            url = f"https://api.telegram.org/bot{self.tg_bot_token}/sendMessage"
            payload = {
                "chat_id": self.tg_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram notification sent successfully.")
            else:
                logger.warning(f"Telegram notification failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
