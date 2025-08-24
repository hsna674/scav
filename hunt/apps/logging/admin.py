from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ActivityLog, FlagSubmission, ChallengeCompletion, PageView


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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user_link", "path", "ip_address")
    list_filter = ("timestamp", "user__graduation_year")
    search_fields = ("user__username", "path", "ip_address")
    readonly_fields = (
        "user",
        "path",
        "timestamp",
        "ip_address",
        "user_agent",
        "referer",
    )
    date_hierarchy = "timestamp"

    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:users_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "Anonymous"

    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
