from django.core.management.base import BaseCommand
from django.utils import timezone
import logging
import os

from hunt.apps.main.context_processors import is_hunt_active

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check if hunt has ended and send Discord notification if needed"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Force send hunt end notification regardless of hunt status",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            dest="reset",
            help="Reset the notification lock file to allow sending notification again",
        )

    def handle(self, *args, **options):
        """
        Check if the hunt has just ended and send Discord notification.
        Uses a lock file to ensure notification is only sent once.
        """
        force_send = options.get("force", False)
        reset_lock = options.get("reset", False)

        # Define lock file path
        lock_file_path = "/tmp/hunt_end_notification_sent.lock"

        # Reset lock file if requested
        if reset_lock:
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
                self.stdout.write(
                    self.style.SUCCESS(
                        "Lock file removed. Notification can be sent again."
                    )
                )
            else:
                self.stdout.write(self.style.WARNING("Lock file does not exist."))
            return

        # Check if notification has already been sent
        if os.path.exists(lock_file_path) and not force_send:
            self.stdout.write(
                self.style.WARNING("Hunt end notification has already been sent.")
            )
            return

        # Check if hunt is still active
        hunt_active = is_hunt_active()

        if hunt_active and not force_send:
            self.stdout.write(
                self.style.SUCCESS("Hunt is still active. No notification needed.")
            )
            return

        # Hunt has ended (or force flag is used), send notification
        try:
            from hunt.apps.main.discord_utils import send_hunt_end_notification

            self.stdout.write("Sending hunt end notification to Discord...")
            send_hunt_end_notification()

            # Create lock file to prevent duplicate notifications
            with open(lock_file_path, "w") as f:
                f.write(f"Hunt end notification sent at {timezone.now()}")

            self.stdout.write(
                self.style.SUCCESS("Successfully sent hunt end notification!")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to send hunt end notification: {e}")
            )
            logger.error(f"Error in hunt end notification command: {e}")
