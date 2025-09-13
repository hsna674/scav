from django.db import models
from django.apps import apps
from django.db.models import Sum, Max


class Category(models.Model):
    id = models.AutoField(primary_key=True, null=False, blank=False)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.CharField(max_length=200, null=False, blank=False)
    order = models.IntegerField(
        default=0,
        help_text="Order on the main page (lower numbers appear first)",
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Challenge(models.Model):
    CHALLENGE_TYPE_CHOICES = [
        ("normal", "Normal"),
        ("exclusive", "Exclusive"),
        ("decreasing", "Decreasing"),
    ]

    id = models.AutoField(primary_key=True, null=False, blank=False)
    name = models.CharField(max_length=100, null=False, blank=False)
    short_description = models.CharField(max_length=500, null=False, blank=False)
    flag = models.CharField(max_length=1024, null=False, blank=False)
    points = models.IntegerField(null=False, blank=False)
    challenge_type = models.CharField(
        max_length=20,
        choices=CHALLENGE_TYPE_CHOICES,
        default="normal",
        help_text="Normal: Standard challenge. Exclusive: Only one class can solve. Decreasing: Points decrease after each class solves it.",
    )
    exclusive = models.BooleanField(
        default=False, help_text="Deprecated: Use challenge_type instead"
    )
    decay_percentage = models.IntegerField(
        default=10,
        help_text="Percentage by which points decrease for decreasing challenges (1-99)",
    )
    locked = models.BooleanField(default=False)
    unblocked = models.BooleanField(default=False)
    order = models.IntegerField(
        default=0,
        help_text="Order within category (lower numbers appear first)",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        related_name="challenges",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["category", "order", "id"]

    def __str__(self):
        return "{} ({})".format(self.name, self.id)

    def save(self, *args, **kwargs):
        # If this is a new challenge (no ID yet) and no order is set,
        # automatically place it at the end of its category
        if not self.pk and self.order == 0 and self.category:
            # Get the highest order number in this category
            max_order = (
                Challenge.objects.filter(category=self.category).aggregate(
                    Max("order")
                )["order__max"]
                or 0
            )
            self.order = max_order + 1

        super().save(*args, **kwargs)

    @property
    def is_exclusive(self):
        """Check if challenge is exclusive (backwards compatibility or new type)"""
        return self.exclusive or self.challenge_type == "exclusive"

    @property
    def is_decreasing(self):
        """Check if challenge has decreasing points"""
        return self.challenge_type == "decreasing"

    def _completed_classes_count(self) -> int:
        """Return the number of distinct classes that have completed this challenge.
        Uses ChallengeCompletion to avoid M2M timing issues.
        Only counts the first completion for each class.
        """
        try:
            ChallengeCompletion = apps.get_model("logging", "ChallengeCompletion")
            return (
                ChallengeCompletion.objects.filter(
                    challenge=self, first_completion_for_class=True
                )
                .values("class_year")
                .distinct()
                .count()
            )
        except Exception:
            # Fallback to M2M if logging app unavailable
            return self.classes_completed.count()

    def get_points_for_class(self, class_year):
        """Get the points this challenge is worth for a specific class (current value)."""
        if not self.is_decreasing:
            return self.points

        classes_completed = self._completed_classes_count()
        decay_factor = (100 - self.decay_percentage) / 100
        current_points = self.points * (decay_factor**classes_completed)
        return max(1, round(current_points))

    def get_current_points(self):
        """Get the current point value for the next class to solve (same as get_points_for_class)."""
        return self.get_points_for_class(None)


class Class(models.Model):
    YEAR_CHOICES = (
        ("2026", "Seniors"),
        ("2027", "Juniors"),
        ("2028", "Sophomores"),
        ("2029", "Freshmen"),
    )

    id = models.AutoField(primary_key=True, null=False, blank=False)
    year = models.CharField(
        max_length=20, choices=YEAR_CHOICES, null=False, blank=False, unique=True
    )
    challenges_completed = models.ManyToManyField(
        Challenge, related_name="classes_completed", blank=True
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.year

    def get_points(self):
        """Total points for this class computed from ChallengeCompletion records."""
        try:
            ChallengeCompletion = apps.get_model("logging", "ChallengeCompletion")
            total = (
                ChallengeCompletion.objects.filter(class_year=self.year)
                .aggregate(Sum("points_earned"))
                .get("points_earned__sum")
            )
            return int(total or 0)
        except Exception:
            # Fallback to legacy M2M-based sum
            sum_ = 0
            for c in self.challenges_completed.all():
                if c.is_decreasing:
                    sum_ += self.get_points_earned_for_challenge(c)
                else:
                    sum_ += c.points
            return sum_

    def get_points_earned_for_challenge(self, challenge):
        """Get the points this class earned for a specific challenge"""
        if not challenge.is_decreasing:
            return challenge.points

        try:
            ChallengeCompletion = apps.get_model("logging", "ChallengeCompletion")
            completions = (
                ChallengeCompletion.objects.filter(
                    challenge=challenge, first_completion_for_class=True
                )
                .order_by("timestamp")
                .values("class_year")
            )

            seen_order = []
            for row in completions:
                cy = row["class_year"]
                if cy not in seen_order:
                    if cy == self.year:
                        break
                    seen_order.append(cy)

            class_completion_order = len(seen_order)
            decay_factor = (100 - challenge.decay_percentage) / 100
            points_earned = challenge.points * (decay_factor**class_completion_order)
            return max(1, round(points_earned))
        except Exception:
            return challenge.get_current_points()


class SiteConfig(models.Model):
    """Singleton-style model to store site-wide configuration flags.

    Only one row is expected. If no row exists, the site is considered enabled.
    """

    site_enabled = models.BooleanField(default=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def __str__(self):
        return f"Site enabled: {self.site_enabled} (updated: {self.updated})"

    @classmethod
    def is_enabled(cls):
        """Return True if the site is enabled. Defaults to True when no config exists."""
        try:
            obj = cls.objects.first()
            return True if obj is None else bool(obj.site_enabled)
        except Exception:
            # If DB is not accessible for any reason, fall back to enabled to avoid accidental lockout.
            return True
