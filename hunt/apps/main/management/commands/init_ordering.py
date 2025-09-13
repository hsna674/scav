from django.core.management.base import BaseCommand
from hunt.apps.main.models import Challenge, Category


class Command(BaseCommand):
    help = "Initialize challenge and category ordering based on current database order"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset all ordering to sequential numbers",
        )
        parser.add_argument(
            "--by-points",
            action="store_true",
            help="Order challenges by points (highest first)",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.reset_sequential_order()
        elif options["by_points"]:
            self.order_by_points()
        else:
            self.initialize_order()

    def initialize_order(self):
        """Set initial order values based on current database order"""
        self.stdout.write("Initializing ordering...")

        # Order categories
        for i, category in enumerate(Category.objects.all().order_by("name"), 1):
            category.order = i * 10  # Leave gaps for easy reordering
            category.save()
            self.stdout.write(f"Category '{category.name}': order = {category.order}")

        # Order challenges within categories
        for category in Category.objects.all():
            challenges = category.challenges.all().order_by("id")
            for i, challenge in enumerate(challenges, 1):
                challenge.order = i * 10  # Leave gaps for easy reordering
                challenge.save()
                self.stdout.write(
                    f"Challenge '{challenge.name}': order = {challenge.order}"
                )

        self.stdout.write(self.style.SUCCESS("Successfully initialized ordering!"))

    def reset_sequential_order(self):
        """Reset all ordering to sequential numbers starting from 1"""
        self.stdout.write("Resetting to sequential order...")

        # Reset categories
        for i, category in enumerate(
            Category.objects.all().order_by("order", "name"), 1
        ):
            category.order = i
            category.save()
            self.stdout.write(f"Category '{category.name}': order = {category.order}")

        # Reset challenges
        for category in Category.objects.all().order_by("order"):
            challenges = category.challenges.all().order_by("order", "id")
            for i, challenge in enumerate(challenges, 1):
                challenge.order = i
                challenge.save()
                self.stdout.write(
                    f"Challenge '{challenge.name}': order = {challenge.order}"
                )

        self.stdout.write(self.style.SUCCESS("Successfully reset all ordering!"))

    def order_by_points(self):
        """Order challenges by points (highest first)"""
        self.stdout.write("Ordering by points...")

        for category in Category.objects.all():
            challenges = category.challenges.all().order_by("-points", "name")
            for challenge in challenges:
                # Use points as order (higher points = lower order number for "first")
                challenge.order = challenge.points
                challenge.save()
                self.stdout.write(
                    f"Challenge '{challenge.name}': order = {challenge.order} (points: {challenge.points})"
                )

        self.stdout.write(
            self.style.SUCCESS("Successfully ordered challenges by points!")
        )
