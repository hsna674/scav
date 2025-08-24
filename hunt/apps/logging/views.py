from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

from .models import ActivityLog, FlagSubmission, ChallengeCompletion
from ..main.models import Challenge, Class

User = get_user_model()


@staff_member_required
def activity_dashboard(request):
    """Main dashboard showing all site activity"""

    # Get recent activity (last 24 hours by default)
    hours = int(request.GET.get("hours", 24))
    since = timezone.now() - timedelta(hours=hours)

    # Recent activities
    recent_activities = ActivityLog.objects.filter(timestamp__gte=since).select_related(
        "user"
    )[:50]

    # Activity counts by type
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

    # Most active users
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
    }

    return render(request, "logging/dashboard.html", context)


@staff_member_required
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
    challenges = Challenge.objects.all().order_by("name")
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
    }

    return render(request, "logging/flag_submissions.html", context)


@staff_member_required
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
    }

    return render(request, "logging/challenge_submissions.html", context)


@staff_member_required
def user_activity(request, user_id):
    """View all activity for a specific user"""

    user = get_object_or_404(User, id=user_id)

    # Get all activities
    activities = ActivityLog.objects.filter(user=user).order_by("-timestamp")
    flag_submissions = (
        FlagSubmission.objects.filter(user=user)
        .select_related("challenge")
        .order_by("-timestamp")
    )
    completions = (
        ChallengeCompletion.objects.filter(user=user)
        .select_related("challenge")
        .order_by("-timestamp")
    )

    # Pagination for activities
    paginator = Paginator(activities, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # User stats
    stats = {
        "total_activities": activities.count(),
        "total_submissions": flag_submissions.count(),
        "correct_submissions": flag_submissions.filter(is_correct=True).count(),
        "total_completions": completions.count(),
        "total_points": completions.aggregate(Sum("points_earned"))[
            "points_earned__sum"
        ]
        or 0,
    }

    context = {
        "profile_user": user,
        "page_obj": page_obj,
        "flag_submissions": flag_submissions[:20],  # Show recent 20
        "completions": completions[:20],  # Show recent 20
        "stats": stats,
    }

    return render(request, "logging/user_activity.html", context)


@staff_member_required
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
        total_submissions=Count("submissions"),
        correct_submissions=Count(
            "submissions", filter=Q(submissions__is_correct=True)
        ),
        completion_count=Count("completions"),
    ).order_by("-total_submissions")

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
    }

    return render(request, "logging/class_leaderboard.html", context)


@staff_member_required
def real_time_activity(request):
    """AJAX endpoint for real-time activity updates"""

    # Get activities from last 5 minutes
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
                "timestamp": activity.timestamp.isoformat(),
                "user": activity.user.username if activity.user else "Anonymous",
                "type": activity.get_activity_type_display(),
                "details": activity.details,
            }
        )

    return JsonResponse({"activities": activity_data})


@staff_member_required
def export_data(request):
    """Export activity data (placeholder for future CSV/JSON export)"""
    # This could be expanded to export data in various formats
    pass
