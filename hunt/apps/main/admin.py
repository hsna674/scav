from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import Challenge, Class, Category


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "short_description",
        "flag",
        "points",
        "challenge_type",
        "decay_percentage",
        "unblocked",
        "category",
        "order",
    )
    list_display = (
        "name",
        "points",
        "challenge_type",
        "decay_percentage",
        "unblocked",
        "locked",
        "category",
        "order",
        "submissions_link",
    )
    list_filter = ("challenge_type", "unblocked", "locked", "category")
    list_editable = ("order",)
    readonly_fields = ("locked",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "unblocked" in form.base_fields:
            form.base_fields["unblocked"].label = "Released"
            form.base_fields[
                "unblocked"
            ].help_text = "Controls whether this challenge is available to participants"

        if "decay_percentage" in form.base_fields:
            form.base_fields[
                "decay_percentage"
            ].help_text = "Percentage by which points decrease for decreasing challenges (only applies to 'Decreasing' type)"

        return form

    class Media:
        js = ("admin/js/challenge_admin.js",)

    def submissions_link(self, obj):
        """Link to view submissions for this challenge"""
        if obj.pk:
            url = reverse("logging:challenge_submissions", args=[obj.pk])
            return format_html('<a href="{}" target="_blank">View Submissions</a>', url)
        return "-"

    submissions_link.short_description = "Submissions"

    def release_challenges(self, request, queryset):
        """Bulk action to release selected challenges"""
        updated = queryset.update(unblocked=True)
        if updated == 1:
            message_bit = "1 challenge was"
        else:
            message_bit = f"{updated} challenges were"
        self.message_user(request, f"{message_bit} successfully released.")

    release_challenges.short_description = "Release selected challenges"

    def reset_order_sequential(self, request, queryset):
        """Reset order to sequential numbers starting from 1"""
        challenges = queryset.order_by("category", "order", "id")
        current_category = None
        order_counter = 1

        for challenge in challenges:
            if challenge.category != current_category:
                current_category = challenge.category
                order_counter = 1

            challenge.order = order_counter
            challenge.save()
            order_counter += 1

        count = queryset.count()
        self.message_user(request, f"Successfully reset order for {count} challenges.")

    reset_order_sequential.short_description = (
        "Reset order to sequential numbers (1, 2, 3...)"
    )

    def set_order_to_points(self, request, queryset):
        """Set order based on points (highest points first)"""
        for challenge in queryset:
            challenge.order = challenge.points
            challenge.save()

        count = queryset.count()
        self.message_user(
            request, f"Successfully set order based on points for {count} challenges."
        )

    set_order_to_points.short_description = "Set order based on points (highest first)"

    actions = ["release_challenges", "reset_order_sequential", "set_order_to_points"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "order")
    list_editable = ("order",)
    ordering = ("order", "name")


admin.site.register(Class)

# Customize the admin index page
admin.site.site_header = "Scavenger Hunt Administration"
admin.site.site_title = "Scav Hunt Admin"
admin.site.index_title = "Welcome to Scavenger Hunt Administration"
