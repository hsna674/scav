#!/usr/bin/env python
"""
Management command to test time synchronization and database operations.
This helps verify that the time correction middleware and database backend are working correctly.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from hunt.apps.logging.models import ActivityLog, ActivityType
from hunt.apps.main.models import Challenge


class Command(BaseCommand):
    help = "Test time synchronization and database operations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-test-log",
            action="store_true",
            help="Create a test activity log entry",
        )
        parser.add_argument(
            "--check-time-sync",
            action="store_true",
            help="Check current time synchronization status",
        )
        parser.add_argument(
            "--test-challenge-timing",
            action="store_true",
            help="Test challenge timed release functionality",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== Time Correction Test ===\n"))

        # Show current time information
        current_time = timezone.now()
        original_time = getattr(timezone, "_original_now", lambda: None)()

        self.stdout.write(f"Current corrected time: {current_time}")
        if original_time:
            offset = current_time - original_time
            self.stdout.write(f"Original system time: {original_time}")
            self.stdout.write(
                f"Applied time offset: {offset.total_seconds():.2f} seconds"
            )
        else:
            self.stdout.write("Time correction middleware not active")

        # Test database time functions
        self.stdout.write("\n=== Database Time Test ===")
        with connection.cursor() as cursor:
            cursor.execute("SELECT corrected_now() as corrected_time")
            db_time = cursor.fetchone()[0]
            self.stdout.write(f"Database corrected_now(): {db_time}")

        # Test challenge timing if requested
        if options.get("test_challenge_timing"):
            self._test_challenge_timing()

        # Create test log if requested
        if options.get("create_test_log"):
            self._create_test_log()

        # Check time sync status
        if options.get("check_time_sync"):
            self._check_time_sync()

    def _test_challenge_timing(self):
        self.stdout.write("\n=== Challenge Timing Test ===")

        # Count challenges with timed releases
        timed_challenges = Challenge.objects.filter(timed_release=True)
        self.stdout.write(f"Total timed challenges: {timed_challenges.count()}")

        current_time = timezone.now()

        # Challenges ready for release
        ready_challenges = timed_challenges.filter(
            release_time__lte=current_time, unblocked=False
        )
        self.stdout.write(f"Challenges ready for release: {ready_challenges.count()}")

        # Scheduled challenges
        scheduled_challenges = timed_challenges.filter(
            release_time__gt=current_time, unblocked=False
        )
        self.stdout.write(f"Scheduled challenges: {scheduled_challenges.count()}")

        # Already released timed challenges
        released_challenges = timed_challenges.filter(unblocked=True)
        self.stdout.write(f"Already released: {released_challenges.count()}")

        if ready_challenges.exists():
            self.stdout.write("\nChallenges ready for release:")
            for challenge in ready_challenges[:5]:  # Show first 5
                self.stdout.write(
                    f"  - {challenge.name} (scheduled: {challenge.release_time})"
                )

    def _create_test_log(self):
        self.stdout.write("\n=== Creating Test Log Entry ===")

        try:
            # Try to find a user to use for the test log
            from django.contrib.auth import get_user_model

            User = get_user_model()

            test_user = User.objects.first()
            if not test_user:
                self.stdout.write(
                    self.style.WARNING("No users found - skipping test log creation")
                )
                return

            log_entry = ActivityLog.objects.create(
                user=test_user,
                activity_type=ActivityType.ADMIN_ACTION,
                details={
                    "action": "time_correction_test",
                    "test_timestamp": timezone.now().isoformat(),
                    "description": "Test log entry created by time correction test command",
                },
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Test log entry created with ID: {log_entry.id}, timestamp: {log_entry.timestamp}"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create test log: {e}"))

    def _check_time_sync(self):
        self.stdout.write("\n=== Time Sync Status ===")

        # Check if middleware is properly loaded
        from django.conf import settings

        middleware_list = settings.MIDDLEWARE
        time_middleware = "hunt.middleware.time_offset.TimeOffsetMiddleware"

        if time_middleware in middleware_list:
            position = middleware_list.index(time_middleware)
            self.stdout.write(f"Time offset middleware loaded at position {position}")
        else:
            self.stdout.write(
                self.style.ERROR("Time offset middleware not found in MIDDLEWARE")
            )

        # Check database backend
        db_engine = settings.DATABASES["default"]["ENGINE"]
        if "sqlite_corrected" in db_engine:
            self.stdout.write("Custom SQLite backend is active")
        else:
            self.stdout.write(
                self.style.WARNING(f"Using standard database backend: {db_engine}")
            )

        # Test some recent log entries to see if timing looks correct
        recent_logs = ActivityLog.objects.order_by("-timestamp")[:3]
        if recent_logs.exists():
            self.stdout.write("\nRecent activity log timestamps:")
            for log in recent_logs:
                self.stdout.write(f"  - {log.timestamp} ({log.activity_type})")
        else:
            self.stdout.write("No recent activity logs found")
