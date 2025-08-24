from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from hunt.apps.users.models import User
from hunt.apps.main.models import Challenge
from hunt.apps.logging.models import (
    ActivityLog,
    FlagSubmission,
    ChallengeCompletion,
    ActivityType,
)


class Command(BaseCommand):
    help = "Generate sample logging data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--activities",
            type=int,
            default=50,
            help="Number of activities to generate",
        )
        parser.add_argument(
            "--submissions",
            type=int,
            default=30,
            help="Number of flag submissions to generate",
        )

    def handle(self, *args, **options):
        users = list(User.objects.filter(is_student=True))
        challenges = list(Challenge.objects.all())

        if not users:
            self.stdout.write(
                self.style.ERROR("No student users found. Create some users first.")
            )
            return

        if not challenges:
            self.stdout.write(
                self.style.ERROR("No challenges found. Create some challenges first.")
            )
            return

        # Generate activities
        activities_count = options["activities"]
        for i in range(activities_count):
            user = random.choice(users)
            activity_type = random.choice(
                [
                    ActivityType.LOGIN,
                    ActivityType.PAGE_VIEW,
                    ActivityType.LOGOUT,
                ]
            )

            # Random timestamp within last 7 days
            timestamp = timezone.now() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            ActivityLog.objects.create(
                user=user,
                activity_type=activity_type,
                timestamp=timestamp,
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                details={
                    "path": random.choice(
                        ["/main/", "/main/challenge/1", "/main/support"]
                    ),
                    "method": "GET",
                },
            )

        # Generate flag submissions
        submissions_count = options["submissions"]
        for i in range(submissions_count):
            user = random.choice(users)
            challenge = random.choice(challenges)

            # 70% chance of correct submission
            is_correct = random.random() < 0.7
            submitted_flag = (
                challenge.flag
                if is_correct
                else f"wrong_flag_{random.randint(1, 1000)}"
            )

            # Random timestamp within last 7 days
            timestamp = timezone.now() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            points_awarded = challenge.points if is_correct else 0

            # Create flag submission
            FlagSubmission.objects.create(
                user=user,
                challenge=challenge,
                submitted_flag=submitted_flag,
                is_correct=is_correct,
                timestamp=timestamp,
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                points_awarded=points_awarded,
            )

            # If correct, maybe create completion (avoid duplicates)
            if (
                is_correct
                and not ChallengeCompletion.objects.filter(
                    user=user, challenge=challenge
                ).exists()
            ):
                # Check if this is first for class
                first_for_class = not ChallengeCompletion.objects.filter(
                    challenge=challenge, class_year=str(user.graduation_year)
                ).exists()

                ChallengeCompletion.objects.create(
                    user=user,
                    challenge=challenge,
                    class_year=str(user.graduation_year),
                    timestamp=timestamp,
                    points_earned=points_awarded,
                    first_completion_for_class=first_for_class,
                )

            # Create activity log for submission
            activity_type = (
                ActivityType.FLAG_SUBMIT_CORRECT
                if is_correct
                else ActivityType.FLAG_SUBMIT_INCORRECT
            )
            ActivityLog.objects.create(
                user=user,
                activity_type=activity_type,
                timestamp=timestamp,
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                details={
                    "challenge_id": challenge.id,
                    "challenge_name": challenge.name,
                    "points_awarded": points_awarded,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {activities_count} activities and {submissions_count} flag submissions"
            )
        )
