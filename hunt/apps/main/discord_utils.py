"""
Discord utilities for first-blood notifications
"""

import logging
import requests
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


def send_first_blood_notification(user, challenge, class_year, points_earned):
    """
    Send a Discord notification for first blood on a challenge.

    Args:
        user: The User object who solved the challenge
        challenge: The Challenge object that was solved
        class_year: The class year (e.g., "2026")
        points_earned: Points awarded for the solve
    """
    # Check if Discord notifications are enabled
    if not getattr(settings, "DISCORD_NOTIFICATIONS_ENABLED", False):
        logger.info("Discord notifications disabled, skipping first blood notification")
        return

    webhook_url = getattr(settings, "DISCORD_WEBHOOK_URL", None)
    if not webhook_url:
        logger.warning(
            "Discord webhook URL not configured, skipping first blood notification"
        )
        return

    try:
        # Get class name from the year choices
        class_names = {
            "2026": "Seniors",
            "2027": "Juniors",
            "2028": "Sophomores",
            "2029": "Freshmen",
        }
        class_name = class_names.get(class_year, f"Class of {class_year}")

        # Format timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        # Create the embed for rich formatting
        embed = {
            "title": "🩸 **FIRST BLOOD!** 🩸",
            "color": 0xFF0000,  # Red color
            "fields": [
                {"name": "Challenge", "value": challenge.name, "inline": True},
                {
                    "name": "Class",
                    "value": f"{class_name} (Class of {class_year})",
                    "inline": True,
                },
                {"name": "Points", "value": str(points_earned), "inline": True},
                {
                    "name": "Category",
                    "value": challenge.category.name
                    if challenge.category
                    else "Uncategorized",
                    "inline": True,
                },
                {"name": "Solver", "value": user.get_full_name(), "inline": True},
                {"name": "Time", "value": timestamp, "inline": True},
            ],
            "footer": {
                "text": f"The {class_name} are the first to solve this challenge! 🎉"
            },
        }

        # Build the message content without role ping
        content = ""

        # Prepare the webhook payload
        payload = {
            "content": content,
            "embeds": [embed],
        }

        # Send the webhook
        response = requests.post(webhook_url, json=payload, timeout=10)

        if response.status_code == 204:
            logger.info(
                f"Successfully sent first blood notification for {challenge.name} to {class_name}"
            )
        else:
            logger.error(
                f"Discord webhook failed with status {response.status_code}: {response.text}"
            )

    except Exception as e:
        # Never let Discord notifications break the actual challenge solving
        logger.error(f"Error sending Discord first blood notification: {e}")
