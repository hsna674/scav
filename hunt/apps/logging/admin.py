from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ActivityLog, FlagSubmission, ChallengeCompletion


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user_link",
        "activity_type",
        "ip_address",
        "details_summary",
    )
    list_filter = ("activity_type", "timestamp", "user__graduation_year")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "ip_address",
    )
    readonly_fields = (
        "user",
        "activity_type",
        "timestamp",
        "ip_address",
        "user_agent",
        "details",
    )
    date_hierarchy = "timestamp"

    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:users_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "Anonymous"

    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def details_summary(self, obj):
        if obj.details:
            # Show first 100 chars of details
            return (
                str(obj.details)[:100] + "..."
                if len(str(obj.details)) > 100
                else str(obj.details)
            )
        return "-"

    details_summary.short_description = "Details"

    def has_add_permission(self, request):
        return False  # Don't allow manual creation

    def has_change_permission(self, request, obj=None):
        return False  # Read-only


@admin.register(FlagSubmission)
class FlagSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user_link",
        "challenge_link",
        "is_correct",
        "points_awarded",
        "submitted_flag_preview",
    )
    list_filter = (
        "is_correct",
        "timestamp",
        "challenge__category",
        "user__graduation_year",
        "points_awarded",
    )
    search_fields = ("user__username", "challenge__name", "submitted_flag")
    readonly_fields = (
        "user",
        "challenge",
        "submitted_flag",
        "is_correct",
        "timestamp",
        "ip_address",
        "points_awarded",
    )
    date_hierarchy = "timestamp"

    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def challenge_link(self, obj):
        url = reverse("admin:main_challenge_change", args=[obj.challenge.pk])
        return format_html('<a href="{}">{}</a>', url, obj.challenge.name)

    challenge_link.short_description = "Challenge"
    challenge_link.admin_order_field = "challenge__name"

    def submitted_flag_preview(self, obj):
        flag = obj.submitted_flag
        if len(flag) > 50:
            return flag[:50] + "..."
        return flag

    submitted_flag_preview.short_description = "Submitted Flag"

    def invalidate_submissions(self, request, queryset):
        """Admin action to invalidate flag submissions"""
        count = 0
        for submission in queryset:
            if submission.is_correct and submission.points_awarded > 0:
                # Find and remove the corresponding ChallengeCompletion
                try:
                    completion = ChallengeCompletion.objects.get(
                        user=submission.user, challenge=submission.challenge
                    )
                    completion.delete()

                    # Remove from user's completed challenges
                    submission.user.challenges_done.remove(submission.challenge)

                    # Remove from class completed challenges if no other completions exist
                    from ..main.models import Class

                    class_obj = Class.objects.get(
                        year=str(submission.user.graduation_year)
                    )
                    other_completions = ChallengeCompletion.objects.filter(
                        challenge=submission.challenge,
                        class_year=submission.user.graduation_year,
                    ).exists()
                    if not other_completions:
                        class_obj.challenges_completed.remove(submission.challenge)

                        # If this was an exclusive challenge, unlock it
                        if submission.challenge.is_exclusive:
                            submission.challenge.locked = False
                            submission.challenge.save()

                    # Log the invalidation action
                    from .utils import log_admin_action

                    log_admin_action(
                        user=request.user,
                        action="invalidate_submission",
                        details={
                            "invalidated_user": submission.user.username,
                            "challenge_id": submission.challenge.id,
                            "challenge_name": submission.challenge.name,
                            "points_removed": submission.points_awarded,
                            "submission_id": submission.id,
                        },
                        request=request,
                    )

                except ChallengeCompletion.DoesNotExist:
                    pass

                # Mark submission as invalidated
                submission.points_awarded = 0
                submission.save()
                count += 1

        if count == 1:
            message = "1 submission was invalidated."
        else:
            message = f"{count} submissions were invalidated."
        self.message_user(request, message)

    invalidate_submissions.short_description = (
        "Invalidate selected submissions (remove points & completions)"
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    actions = ["invalidate_submissions"]


@admin.register(ChallengeCompletion)
class ChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user_link",
        "challenge_link",
        "class_year",
        "points_earned",
        "first_completion_for_class",
    )
    list_filter = (
        "class_year",
        "timestamp",
        "challenge__category",
        "first_completion_for_class",
        "points_earned",
    )
    search_fields = ("user__username", "challenge__name")
    readonly_fields = (
        "user",
        "challenge",
        "class_year",
        "timestamp",
        "points_earned",
        "first_completion_for_class",
    )
    date_hierarchy = "timestamp"

    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def challenge_link(self, obj):
        url = reverse("admin:main_challenge_change", args=[obj.challenge.pk])
        return format_html('<a href="{}">{}</a>', url, obj.challenge.name)

    challenge_link.short_description = "Challenge"
    challenge_link.admin_order_field = "challenge__name"

    def invalidate_completions(self, request, queryset):
        """Admin action to invalidate challenge completions"""
        count = 0
        for completion in queryset:
            # Remove from user's completed challenges
            completion.user.challenges_done.remove(completion.challenge)

            # Remove from class completed challenges if no other completions exist
            from ..main.models import Class

            class_obj = Class.objects.get(year=completion.class_year)
            other_completions = (
                ChallengeCompletion.objects.filter(
                    challenge=completion.challenge, class_year=completion.class_year
                )
                .exclude(id=completion.id)
                .exists()
            )
            if not other_completions:
                class_obj.challenges_completed.remove(completion.challenge)

                # If this was an exclusive challenge, unlock it
                if completion.challenge.is_exclusive:
                    completion.challenge.locked = False
                    completion.challenge.save()

            # Zero out points on corresponding flag submission
            FlagSubmission.objects.filter(
                user=completion.user, challenge=completion.challenge, is_correct=True
            ).update(points_awarded=0)

            # Log the invalidation action
            from .utils import log_admin_action

            log_admin_action(
                user=request.user,
                action="invalidate_completion",
                details={
                    "invalidated_user": completion.user.username,
                    "challenge_id": completion.challenge.id,
                    "challenge_name": completion.challenge.name,
                    "points_removed": completion.points_earned,
                    "completion_id": completion.id,
                    "class_year": completion.class_year,
                },
                request=request,
            )

            # Delete the completion
            completion.delete()
            count += 1

        if count == 1:
            message = "1 completion was invalidated."
        else:
            message = f"{count} completions were invalidated."
        self.message_user(request, message)

    invalidate_completions.short_description = (
        "Invalidate selected completions (remove points)"
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    actions = ["invalidate_completions"]


# PageViewAdmin removed - PageView model was removed for performance
