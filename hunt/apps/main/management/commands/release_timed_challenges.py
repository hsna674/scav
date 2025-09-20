"""
Management command to check and release timed challenges.
This should be run periodically (e.g., via cron) to automatically release challenges.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from hunt.apps.main.models import Challenge
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check for timed challenges that should be released and release them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show what would be released without actually releasing challenges",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            help="Show detailed output including challenges that are not ready",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)

        current_time = timezone.now()

        # Find challenges that should be released
        challenges_to_release = Challenge.objects.filter(
            timed_release=True,
            release_time__lte=current_time,
            unblocked=False,  # Only release challenges that aren't already manually unblocked
        )

        # Find challenges that are scheduled but not yet ready
        scheduled_challenges = Challenge.objects.filter(
            timed_release=True, release_time__gt=current_time, unblocked=False
        )

        released_count = 0

        if challenges_to_release.exists():
            for challenge in challenges_to_release:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY RUN] Would release: {challenge.name} (ID: {challenge.id}) - "
                            f"scheduled for {challenge.release_time}, current time: {current_time}"
                        )
                    )
                else:
                    try:
                        challenge.unblocked = True
                        challenge.save(update_fields=["unblocked"])
                        released_count += 1

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Released challenge: {challenge.name} (ID: {challenge.id}) - "
                                f"scheduled for {challenge.release_time}"
                            )
                        )
                        logger.info(
                            f"Auto-released timed challenge: {challenge.name} (ID: {challenge.id})"
                        )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to release challenge {challenge.name} (ID: {challenge.id}): {e}"
                            )
                        )
                        logger.error(
                            f"Failed to auto-release challenge {challenge.id}: {e}"
                        )
        else:
            if verbose:
                self.stdout.write("No challenges ready for release at this time.")

        # Show scheduled challenges if verbose
        if verbose and scheduled_challenges.exists():
            self.stdout.write("\nScheduled challenges (not yet ready):")
            for challenge in scheduled_challenges.order_by("release_time"):
                time_until_release = challenge.release_time - current_time
                hours = int(time_until_release.total_seconds() // 3600)
                minutes = int((time_until_release.total_seconds() % 3600) // 60)

                self.stdout.write(
                    f"  - {challenge.name} (ID: {challenge.id}) - "
                    f"releases in {hours}h {minutes}m at {challenge.release_time}"
                )

        # Summary
        if not dry_run and released_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully released {released_count} challenge(s)."
                )
            )
        elif dry_run:
            potential_releases = challenges_to_release.count()
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would release {potential_releases} challenge(s)."
                )
            )

        if verbose:
            total_timed = Challenge.objects.filter(timed_release=True).count()
            already_released = Challenge.objects.filter(
                timed_release=True, unblocked=True
            ).count()
            self.stdout.write(
                f"\nTimed challenge summary: {already_released}/{total_timed} released, "
                f"{scheduled_challenges.count()} scheduled for future release"
            )
