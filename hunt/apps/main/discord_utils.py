"""
Discord utilities for first-blood notifications and hunt end notifications
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

        # Send the webhook with reduced timeout for better performance
        response = requests.post(webhook_url, json=payload, timeout=3)

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


def send_hunt_end_notification():
    """
    Send a Discord notification when the hunt ends with final leaderboard.
    """
    # Check if Discord notifications are enabled
    if not getattr(settings, "DISCORD_NOTIFICATIONS_ENABLED", False):
        logger.info("Discord notifications disabled, skipping hunt end notification")
        return

    webhook_url = getattr(settings, "DISCORD_WEBHOOK_URL", None)
    if not webhook_url:
        logger.warning(
            "Discord webhook URL not configured, skipping hunt end notification"
        )
        return

    try:
        from .models import Class

        # Get all classes with their points, sorted by points (highest first)
        classes_data = []
        for class_obj in Class.objects.all():
            class_name = dict(Class.YEAR_CHOICES).get(
                class_obj.year, f"Class of {class_obj.year}"
            )
            points = class_obj.get_points()
            classes_data.append((class_name, class_obj.year, points))

        # Sort by points (descending)
        classes_data.sort(key=lambda x: x[2], reverse=True)

        # Determine rankings and create leaderboard text
        leaderboard_fields = []
        medals = ["🥇", "🥈", "🥉", "4️⃣"]

        for i, (class_name, year, points) in enumerate(classes_data):
            medal = medals[i] if i < len(medals) else f"{i + 1}️⃣"

            # Create field for each class
            leaderboard_fields.append(
                {
                    "name": f"{medal} {class_name}",
                    "value": f"**{points:,} points**",
                    "inline": True,
                }
            )

        # Format timestamp
        hunt_year = getattr(settings, "HUNT_YEAR", datetime.now().year)
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        # Create the embed for rich formatting
        embed = {
            "title": f"🏁 **HUNT {hunt_year} HAS ENDED!** 🏁",
            "description": "The scavenger hunt has officially concluded! Here are the final results:",
            "color": 0x00FF00,  # Green color
            "fields": leaderboard_fields,
            "footer": {"text": f"Congratulations to all participants! • {timestamp}"},
            "thumbnail": {
                "url": "https://cdn.discordapp.com/emojis/🏆.png"  # Trophy emoji as thumbnail
            },
        }

        # Add a special congratulations for the winner
        if classes_data:
            winner_name = classes_data[0][0]
            winner_points = classes_data[0][2]
            content = f"🎉 **Congratulations to the {winner_name}!** 🎉\nThey've won Hoco Hunt {hunt_year} with **{winner_points:,} points**!"
        else:
            content = f"🏁 **Hoco Hunt {hunt_year} has ended!**"

        # Prepare the webhook payload
        payload = {
            "content": content,
            "embeds": [embed],
        }

        # Send the webhook with reduced timeout for better performance
        response = requests.post(webhook_url, json=payload, timeout=3)

        if response.status_code == 204:
            logger.info(f"Successfully sent hunt end notification for Hunt {hunt_year}")
        else:
            logger.error(
                f"Discord webhook failed with status {response.status_code}: {response.text}"
            )

    except Exception as e:
        # Never let Discord notifications break anything critical
        logger.error(f"Error sending Discord hunt end notification: {e}")
