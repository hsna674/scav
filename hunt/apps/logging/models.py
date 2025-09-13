from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class ActivityType(models.TextChoices):
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    FLAG_SUBMIT_CORRECT = "flag_correct", "Correct Flag Submission"
    FLAG_SUBMIT_INCORRECT = "flag_incorrect", "Incorrect Flag Submission"
    CHALLENGE_COMPLETED = "challenge_completed", "Challenge Completed"
    ADMIN_ACTION = "admin_action", "Admin Action"


class ActivityLog(models.Model):
    """Log all user activities on the site"""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="activity_logs"
    )
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Additional context data stored as JSON-like text
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["activity_type", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} at {self.timestamp}"


class FlagSubmission(models.Model):
    """Detailed logging of flag submissions"""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="flag_submissions"
    )
    challenge = models.ForeignKey(
        "main.Challenge", on_delete=models.CASCADE, related_name="submissions"
    )
    submitted_flag = models.CharField(max_length=1024)
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Points awarded (0 if incorrect or already completed)
    points_awarded = models.IntegerField(default=0)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["challenge", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["is_correct", "timestamp"]),
        ]

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.user.username} -> {self.challenge.name} at {self.timestamp}"


class ChallengeCompletion(models.Model):
    """Track when challenges are first completed by users/classes"""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="completions")
    challenge = models.ForeignKey(
        "main.Challenge", on_delete=models.CASCADE, related_name="completions"
    )
    class_year = models.CharField(max_length=20)  # Store the class year when completed
    timestamp = models.DateTimeField(default=timezone.now)
    points_earned = models.IntegerField()

    # Track if this was the first completion for the class
    first_completion_for_class = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        unique_together = ["user", "challenge"]  # Prevent duplicate completions
        indexes = [
            models.Index(fields=["challenge", "timestamp"]),
            models.Index(fields=["class_year", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} completed {self.challenge.name} ({self.points_earned} pts)"


# PageView model removed for performance - was creating database record for every page load
