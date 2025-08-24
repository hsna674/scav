from django.core.management.base import BaseCommand
from hunt.apps.main.models import Challenge, Class


class Command(BaseCommand):
    help = "Test decreasing challenge points calculation"

    def handle(self, *args, **options):
        # Find a decreasing challenge
        decreasing_challenges = Challenge.objects.filter(challenge_type="decreasing")

        if not decreasing_challenges.exists():
            self.stdout.write(self.style.WARNING("No decreasing challenges found"))
            return

        challenge = decreasing_challenges.first()
        self.stdout.write(f"Testing challenge: {challenge.name} (ID: {challenge.id})")
        self.stdout.write(f"Original points: {challenge.points}")
        self.stdout.write(f"Decay percentage: {challenge.decay_percentage}%")

        # Check how many classes have completed it
        completed_classes = Class.objects.filter(challenges_completed=challenge).count()
        self.stdout.write(f"Classes completed: {completed_classes}")

        # Calculate current points
        current_points = challenge.get_current_points()
        self.stdout.write(f"Current points: {current_points}")

        # Simulate what points each class would get
        for i in range(4):  # For 4 classes
            decay_factor = (100 - challenge.decay_percentage) / 100
            points_for_class = challenge.points * (decay_factor**i)
            points_for_class = max(1, round(points_for_class))
            self.stdout.write(f"Class {i + 1} would get: {points_for_class} points")
