from django.db import models


class Category(models.Model):
    id = models.AutoField(primary_key=True, null=False, blank=False)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.CharField(max_length=200, null=False, blank=False)

    def __str__(self):
        return self.name


class Challenge(models.Model):
    id = models.AutoField(primary_key=True, null=False, blank=False)
    name = models.CharField(max_length=100, null=False, blank=False)
    short_description = models.CharField(max_length=500, null=False, blank=False)
    flag = models.CharField(max_length=1024, null=False, blank=False)
    points = models.IntegerField(null=False, blank=False)
    exclusive = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    unblocked = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        related_name="challenges",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return "{} ({})".format(self.name, self.id)


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
        sum = 0
        for c in self.challenges_completed.all():
            sum += c.points
        return sum


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
