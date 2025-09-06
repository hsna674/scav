"""
Utility functions for logging activities throughout the application
"""

import logging
from django.utils import timezone

from .models import ActivityLog, FlagSubmission, ChallengeCompletion, ActivityType

logger = logging.getLogger(__name__)


def log_flag_submission(
    user, challenge, submitted_flag, is_correct, points_awarded=0, request=None
):
    """Log a flag submission"""
    try:
        ip_address = None
        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0]
            else:
                ip_address = request.META.get("REMOTE_ADDR")

        # Create flag submission record
        submission = FlagSubmission.objects.create(
            user=user,
            challenge=challenge,
            submitted_flag=submitted_flag,
            is_correct=is_correct,
            ip_address=ip_address,
            points_awarded=points_awarded,
        )

        # Create activity log entry
        activity_type = (
            ActivityType.FLAG_SUBMIT_CORRECT
            if is_correct
            else ActivityType.FLAG_SUBMIT_INCORRECT
        )
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            ip_address=ip_address,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            details={
                "challenge_id": challenge.id,
                "challenge_name": challenge.name,
                "points_awarded": points_awarded,
                "submitted_flag_length": len(submitted_flag),
                "category": challenge.category.name if challenge.category else None,
            },
        )

        return submission

    except Exception as e:
        logger.error(f"Error logging flag submission: {e}")
        return None


def log_challenge_completion(
    user, challenge, points_earned, class_year, first_for_class=False, request=None
):
    """Log when a user completes a challenge"""
    try:
        ip_address = None
        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0]
            else:
                ip_address = request.META.get("REMOTE_ADDR")

        # Create completion record
        completion = ChallengeCompletion.objects.create(
            user=user,
            challenge=challenge,
            class_year=class_year,
            points_earned=points_earned,
            first_completion_for_class=first_for_class,
        )

        # Create activity log entry
        ActivityLog.objects.create(
            user=user,
            activity_type=ActivityType.CHALLENGE_COMPLETED,
            ip_address=ip_address,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            details={
                "challenge_id": challenge.id,
                "challenge_name": challenge.name,
                "points_earned": points_earned,
                "class_year": class_year,
                "first_for_class": first_for_class,
                "category": challenge.category.name if challenge.category else None,
            },
        )

        # Send Discord first blood notification if this is the first solve for the class
        if first_for_class:
            try:
                from ..main.discord_utils import send_first_blood_notification

                send_first_blood_notification(
                    user, challenge, class_year, points_earned
                )
            except Exception as e:
                # Discord notifications should never break challenge solving
                logger.error(f"Discord notification failed: {e}")

        return completion

    except Exception as e:
        logger.error(f"Error logging challenge completion: {e}")
        return None


def log_admin_action(user, action, details=None, request=None):
    """Log admin actions"""
    try:
        ip_address = None
        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0]
            else:
                ip_address = request.META.get("REMOTE_ADDR")

        ActivityLog.objects.create(
            user=user,
            activity_type=ActivityType.ADMIN_ACTION,
            ip_address=ip_address,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            details={
                "action": action,
                "timestamp": timezone.now().isoformat(),
                **(details or {}),
            },
        )

    except Exception as e:
        logger.error(f"Error logging admin action: {e}")


def get_user_stats(user):
    """Get comprehensive stats for a user"""
    try:
        from django.db.models import Sum

        # Get basic counts
        total_activities = ActivityLog.objects.filter(user=user).count()
        total_submissions = FlagSubmission.objects.filter(user=user).count()
        correct_submissions = FlagSubmission.objects.filter(
            user=user, is_correct=True
        ).count()
        total_completions = ChallengeCompletion.objects.filter(user=user).count()

        # Get points
        total_points = (
            ChallengeCompletion.objects.filter(user=user).aggregate(
                Sum("points_earned")
            )["points_earned__sum"]
            or 0
        )

        # Calculate success rate
        success_rate = (
            (correct_submissions / total_submissions * 100)
            if total_submissions > 0
            else 0
        )

        return {
            "total_activities": total_activities,
            "total_submissions": total_submissions,
            "correct_submissions": correct_submissions,
            "total_completions": total_completions,
            "total_points": total_points,
            "success_rate": round(success_rate, 2),
        }

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {}


def get_challenge_stats(challenge):
    """Get comprehensive stats for a challenge"""
    try:
        # Get submission stats
        submissions = FlagSubmission.objects.filter(challenge=challenge)
        total_submissions = submissions.count()
        correct_submissions = submissions.filter(is_correct=True).count()
        unique_users = submissions.values("user").distinct().count()

        # Calculate success rate
        success_rate = (
            (correct_submissions / total_submissions * 100)
            if total_submissions > 0
            else 0
        )

        # Get completion stats
        completions = ChallengeCompletion.objects.filter(challenge=challenge)
        total_completions = completions.count()

        # Class breakdown
        from ..main.models import Class

        class_breakdown = {}
        for cls in Class.objects.all():
            class_submissions = submissions.filter(user__graduation_year=cls.year)
            class_completions = completions.filter(class_year=cls.year)
            class_breakdown[cls.year] = {
                "submissions": class_submissions.count(),
                "correct": class_submissions.filter(is_correct=True).count(),
                "completions": class_completions.count(),
            }

        return {
            "total_submissions": total_submissions,
            "correct_submissions": correct_submissions,
            "unique_users": unique_users,
            "success_rate": round(success_rate, 2),
            "total_completions": total_completions,
            "class_breakdown": class_breakdown,
        }

    except Exception as e:
        logger.error(f"Error getting challenge stats: {e}")
        return {}
