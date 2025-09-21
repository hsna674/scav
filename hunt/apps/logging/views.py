from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import ActivityLog, FlagSubmission, ChallengeCompletion
from .decorators import staff_or_committee_required
from .utils import log_admin_action
from ..main.models import Challenge, Class

User = get_user_model()


@staff_or_committee_required
def activity_dashboard(request):
    """Main dashboard showing all site activity"""

    # Get recent activity (last 24 hours by default)
    hours = int(request.GET.get("hours", 24))
    since = timezone.now() - timedelta(hours=hours)

    # Recent activities (page view logging removed for performance)
    recent_activities = ActivityLog.objects.filter(timestamp__gte=since).select_related(
        "user"
    )[:50]

    # Activity counts by type (page view logging removed for performance)
    activity_counts = (
        ActivityLog.objects.filter(timestamp__gte=since)
        .values("activity_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Flag submission stats
    flag_stats = FlagSubmission.objects.filter(timestamp__gte=since).aggregate(
        total_submissions=Count("id"),
        correct_submissions=Count("id", filter=Q(is_correct=True)),
        unique_users=Count("user", distinct=True),
        total_points=Sum("points_awarded"),
    )

    # Most active users (page view logging removed for performance)
    active_users = (
        ActivityLog.objects.filter(timestamp__gte=since)
        .values("user__id", "user__username", "user__graduation_year")
        .annotate(activity_count=Count("id"))
        .order_by("-activity_count")[:10]
    )

    # Challenge completion stats by class
    class_stats = []
    for cls in Class.objects.all():
        completions = ChallengeCompletion.objects.filter(
            class_year=cls.year, timestamp__gte=since
        ).aggregate(count=Count("id"), points=Sum("points_earned"))
        class_stats.append(
            {
                "class": cls,
                "completions": completions["count"] or 0,
                "points": completions["points"] or 0,
            }
        )

    context = {
        "recent_activities": recent_activities,
        "activity_counts": activity_counts,
        "flag_stats": flag_stats,
        "active_users": active_users,
        "class_stats": class_stats,
        "hours": hours,
        "since": since,
        "dark_mode": request.user.dark_mode,
        # Provide classes for the switcher UI
        "classes": Class.objects.all().order_by("year"),
        # Show a small confirmation after switching
        "switched": request.GET.get("switched") == "1",
        "switched_to": request.GET.get("to"),
    }

    return render(request, "logging/dashboard.html", context)


@staff_or_committee_required
def flag_submissions(request):
    """View all flag submissions with filtering"""

    submissions = FlagSubmission.objects.select_related("user", "challenge").order_by(
        "-timestamp"
    )

    # Filtering
    challenge_id = request.GET.get("challenge")
    user_id = request.GET.get("user")
    is_correct = request.GET.get("correct")
    class_year = request.GET.get("class")

    if challenge_id:
        submissions = submissions.filter(challenge_id=challenge_id)
    if user_id:
        submissions = submissions.filter(user_id=user_id)
    if is_correct is not None:
        submissions = submissions.filter(is_correct=is_correct == "true")
    if class_year:
        submissions = submissions.filter(user__graduation_year=class_year)

    # Pagination
    paginator = Paginator(submissions, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get filter options
    challenges = Challenge.objects.all().order_by("category", "order", "name")
    users = User.objects.filter(is_student=True).order_by("username")
    classes = Class.objects.all().order_by("year")

    context = {
        "page_obj": page_obj,
        "challenges": challenges,
        "users": users,
        "classes": classes,
        "current_filters": {
            "challenge": challenge_id,
            "user": user_id,
            "correct": is_correct,
            "class": class_year,
        },
        "dark_mode": request.user.dark_mode,
    }

    return render(request, "logging/flag_submissions.html", context)


@staff_or_committee_required
def challenge_submissions(request, challenge_id):
    """View all submissions for a specific challenge"""

    challenge = get_object_or_404(Challenge, id=challenge_id)
    submissions = (
        FlagSubmission.objects.filter(challenge=challenge)
        .select_related("user")
        .order_by("-timestamp")
    )

    # Pagination
    paginator = Paginator(submissions, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Stats
    stats = submissions.aggregate(
        total=Count("id"),
        correct=Count("id", filter=Q(is_correct=True)),
        unique_users=Count("user", distinct=True),
        total_points=Sum("points_awarded"),
    )

    # Calculate success rate
    if stats["total"] and stats["total"] > 0:
        stats["success_rate"] = round((stats["correct"] / stats["total"]) * 100, 1)
    else:
        stats["success_rate"] = 0

    # Success rate by class
    class_stats = []
    for cls in Class.objects.all():
        class_submissions = submissions.filter(user__graduation_year=cls.year)
        class_total = class_submissions.count()
        class_correct = class_submissions.filter(is_correct=True).count()
        class_stats.append(
            {
                "class": cls,
                "total": class_total,
                "correct": class_correct,
                "rate": (class_correct / class_total * 100) if class_total > 0 else 0,
            }
        )

    context = {
        "challenge": challenge,
        "page_obj": page_obj,
        "stats": stats,
        "class_stats": class_stats,
        "dark_mode": request.user.dark_mode,
    }

    return render(request, "logging/challenge_submissions.html", context)


@staff_or_committee_required
def user_activity(request, user_id):
    """View all activity for a specific user"""

    user = get_object_or_404(User, id=user_id)

    # Get all activities (page view logging removed for performance)
    activities = ActivityLog.objects.filter(user=user).order_by("-timestamp")
    flag_submissions = (
        FlagSubmission.objects.filter(user=user)
        .select_related("challenge")
        .order_by("-timestamp")
    )
    # Get completions with their corresponding flag submissions for invalidation
    completions_with_submissions = []
    completions = (
        ChallengeCompletion.objects.filter(user=user)
        .select_related("challenge")
        .order_by("-timestamp")
    )

    for completion in completions:
        # Find the corresponding flag submission
        try:
            flag_submission = FlagSubmission.objects.get(
                user=user,
                challenge=completion.challenge,
                is_correct=True,
                invalidated=False,
            )
            completion.flag_submission_id = flag_submission.id
        except FlagSubmission.DoesNotExist:
            completion.flag_submission_id = None
        completions_with_submissions.append(completion)

    # Pagination for activities
    paginator = Paginator(activities, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # User stats
    total_submissions = flag_submissions.count()
    correct_submissions = flag_submissions.filter(is_correct=True).count()

    # Calculate success rate
    success_rate = (
        (correct_submissions / total_submissions * 100) if total_submissions > 0 else 0
    )

    stats = {
        "total_activities": activities.count(),  # Already excludes page views
        "total_submissions": total_submissions,
        "correct_submissions": correct_submissions,
        "total_completions": completions.count(),
        "total_points": completions.aggregate(Sum("points_earned"))[
            "points_earned__sum"
        ]
        or 0,
        "success_rate": round(success_rate, 1),
    }

    context = {
        "profile_user": user,
        "page_obj": page_obj,
        "flag_submissions": flag_submissions[:20],  # Show recent 20
        "completions": completions_with_submissions[:20],  # Show recent 20
        "stats": stats,
        "dark_mode": request.user.dark_mode,
    }

    return render(request, "logging/user_activity.html", context)


@staff_or_committee_required
def class_leaderboard(request):
    """View challenge completion statistics by class"""

    # Get timeframe
    days = int(request.GET.get("days", 7))
    since = timezone.now() - timedelta(days=days)

    class_data = []
    for cls in Class.objects.all():
        # Get users in this class
        users_in_class = User.objects.filter(graduation_year=cls.year, is_student=True)

        # Get completions in timeframe
        recent_completions = ChallengeCompletion.objects.filter(
            class_year=cls.year, timestamp__gte=since
        )

        # Get top users in this class
        top_users = (
            ChallengeCompletion.objects.filter(
                class_year=cls.year, timestamp__gte=since
            )
            .values("user__username")
            .annotate(completion_count=Count("id"), total_points=Sum("points_earned"))
            .order_by("-completion_count")[:5]
        )

        class_data.append(
            {
                "class": cls,
                "user_count": users_in_class.count(),
                "total_completions": recent_completions.count(),
                "total_points": recent_completions.aggregate(Sum("points_earned"))[
                    "points_earned__sum"
                ]
                or 0,
                "unique_solvers": recent_completions.values("user").distinct().count(),
                "top_users": top_users,
            }
        )

    # Challenge difficulty analysis
    challenge_stats = Challenge.objects.annotate(
        total_submissions=Count("submissions", distinct=True),
        correct_submissions=Count(
            "submissions", filter=Q(submissions__is_correct=True), distinct=True
        ),
        completion_count=Count("completions", distinct=True),
    ).order_by("category", "order", "name")

    # Calculate success rate safely to avoid division by zero
    for challenge in challenge_stats:
        if challenge.total_submissions > 0:
            challenge.success_rate = round(
                (challenge.correct_submissions / challenge.total_submissions) * 100, 1
            )
        else:
            challenge.success_rate = 0

    context = {
        "class_data": class_data,
        "challenge_stats": challenge_stats,
        "days": days,
        "since": since,
        "dark_mode": request.user.dark_mode,
    }

    return render(request, "logging/class_leaderboard.html", context)


@staff_or_committee_required
def real_time_activity(request):
    """AJAX endpoint for real-time activity updates"""

    # Get activities from last 5 minutes (page view logging removed for performance)
    since = timezone.now() - timedelta(minutes=5)
    activities = (
        ActivityLog.objects.filter(timestamp__gte=since)
        .select_related("user")
        .order_by("-timestamp")[:20]
    )

    activity_data = []
    for activity in activities:
        activity_data.append(
            {
                "timestamp": timezone.localtime(activity.timestamp).isoformat(),
                "user": activity.user.username if activity.user else "Anonymous",
                "type": activity.get_activity_type_display(),
                "details": activity.details,
            }
        )

    return JsonResponse({"activities": activity_data})


@staff_or_committee_required
def export_data(request):
    """Export activity data (placeholder for future CSV/JSON export)"""
    # This could be expanded to export data in various formats
    pass


@staff_or_committee_required
def invalidate_submission(request, submission_id):
    """Completely remove/invalidate a flag submission and all related completion data"""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        submission = FlagSubmission.objects.get(id=submission_id)

        if not submission.is_correct or submission.points_awarded == 0:
            return JsonResponse(
                {"error": "Submission is not a valid completion"}, status=400
            )

        # Store details for logging before deletion
        submission_details = {
            "invalidated_user": submission.user.username,
            "challenge_id": submission.challenge.id,
            "challenge_name": submission.challenge.name,
            "points_removed": submission.points_awarded,
            "submission_id": submission.id,
            "submission_timestamp": timezone.localtime(
                submission.timestamp
            ).isoformat(),
        }

        challenge = submission.challenge
        user = submission.user
        class_year = str(user.graduation_year)

        # 1. Remove from user's completed challenges
        user.challenges_done.remove(challenge)

        # 2. Find and delete the corresponding ChallengeCompletion
        try:
            completion = ChallengeCompletion.objects.get(user=user, challenge=challenge)
            completion.delete()
        except ChallengeCompletion.DoesNotExist:
            pass

        # 3. Check if class should still have this challenge as completed
        class_obj = Class.objects.get(year=class_year)
        other_class_completions = ChallengeCompletion.objects.filter(
            challenge=challenge,
            class_year=class_year,
        ).exists()

        if not other_class_completions:
            # No other users from this class have completed it
            class_obj.challenges_completed.remove(challenge)

            # If this was an exclusive challenge, unlock it
            if challenge.is_exclusive and challenge.locked:
                challenge.locked = False
                challenge.save()

        # 4. Mark the submission as invalidated instead of deleting it
        submission.invalidated = True
        submission.invalidated_by = request.user
        submission.invalidated_at = timezone.now()
        submission.points_awarded = 0  # Remove points but keep the record
        submission.save()

        # 5. Log the invalidation action
        log_admin_action(
            user=request.user,
            action="invalidate_submission",
            details=submission_details,
            request=request,
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Submission for {challenge.name} by {submission_details['invalidated_user']} has been invalidated",
                "invalidated_by": request.user.username,
                "invalidated_at": submission.invalidated_at.strftime(
                    "%b %d, %Y %I:%M %p"
                ),
            }
        )

    except FlagSubmission.DoesNotExist:
        return JsonResponse({"error": "Submission not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@staff_or_committee_required
def switch_user_class(request):
    """Allow committee/staff to change their own class (graduation_year).

    This updates the user's graduation_year to the selected class year so the site
    reflects that class's perspective.
    """
    if request.method != "POST":
        return redirect("logging:dashboard")

    year = request.POST.get("year")
    if not year:
        return redirect("logging:dashboard")

    try:
        cls = Class.objects.get(year=str(year))
    except Class.DoesNotExist:
        return redirect("logging:dashboard")

    old_year = request.user.graduation_year
    try:
        new_year_int = int(cls.year)
    except (TypeError, ValueError):
        return redirect("logging:dashboard")

    # Persist the change
    request.user.graduation_year = new_year_int
    request.user.save(update_fields=["graduation_year"])

    # Log the action
    log_admin_action(
        user=request.user,
        action="switch_user_class",
        details={"from_year": old_year, "to_year": new_year_int},
        request=request,
    )

    # Redirect back to dashboard with a small flag
    dashboard_url = f"{reverse('logging:dashboard')}?switched=1&to={new_year_int}"
    return redirect(dashboard_url)


@staff_or_committee_required
def timezone_diagnostic(request):
    """Comprehensive timezone diagnostic for production debugging"""
    import os
    from django.db import connection
    from django.conf import settings

    now_django = timezone.now()

    # Get database timezone
    with connection.cursor() as cursor:
        # For SQLite
        if "sqlite" in settings.DATABASES["default"]["ENGINE"]:
            cursor.execute("SELECT datetime('now');")
            db_time_str = cursor.fetchone()[0]
            # SQLite returns string, convert to datetime
            from datetime import datetime

            db_time = datetime.fromisoformat(db_time_str.replace(" ", "T"))
        else:
            # For PostgreSQL/MySQL
            cursor.execute("SELECT NOW();")
            db_time = cursor.fetchone()[0]

    # Get latest activity to compare
    latest_activity = ActivityLog.objects.order_by("-timestamp").first()

    # System info
    system_tz = os.environ.get("TZ", "Not set")

    diagnostic_data = {
        "django_settings": {
            "TIME_ZONE": settings.TIME_ZONE,
            "USE_TZ": settings.USE_TZ,
        },
        "system_info": {
            "TZ_env_var": system_tz,
        },
        "times": {
            "django_now_utc": now_django.isoformat(),
            "django_now_local": timezone.localtime(now_django).isoformat(),
            "database_now": str(db_time),
            "django_timezone": str(timezone.get_current_timezone()),
        },
        "time_differences": {
            "django_vs_db_seconds": (
                now_django.replace(tzinfo=None) - db_time.replace(tzinfo=None)
            ).total_seconds()
            if hasattr(db_time, "replace")
            else "N/A",
        },
    }

    if latest_activity:
        diagnostic_data["latest_activity"] = {
            "timestamp_utc": latest_activity.timestamp.isoformat(),
            "timestamp_local": timezone.localtime(
                latest_activity.timestamp
            ).isoformat(),
            "age_seconds": (now_django - latest_activity.timestamp).total_seconds(),
            "details_timestamp": latest_activity.details.get("timestamp")
            if latest_activity.details
            else None,
        }

    # Test creating a new activity log entry
    test_log = ActivityLog.objects.create(
        user=request.user,
        activity_type="ADMIN_ACTION",
        details={
            "action": "timezone_diagnostic_test",
            "timestamp": timezone.localtime(timezone.now()).isoformat(),
            "test": True,
        },
    )

    diagnostic_data["test_log"] = {
        "created_timestamp_utc": test_log.timestamp.isoformat(),
        "created_timestamp_local": timezone.localtime(test_log.timestamp).isoformat(),
        "details_timestamp": test_log.details.get("timestamp"),
        "immediate_age_seconds": (now_django - test_log.timestamp).total_seconds(),
    }

    # Clean up test log
    test_log.delete()

    return JsonResponse(diagnostic_data, json_dumps_params={"indent": 2})
