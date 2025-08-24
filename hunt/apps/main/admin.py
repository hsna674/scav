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
    )
    list_display = (
        "name",
        "points",
        "challenge_type",
        "decay_percentage",
        "unblocked",
        "locked",
        "category",
        "submissions_link",
    )
    list_filter = ("challenge_type", "unblocked", "locked", "category")
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

    actions = ["release_challenges"]


admin.site.register(Category)
admin.site.register(Class)

# Customize the admin index page
admin.site.site_header = "Scavenger Hunt Administration"
admin.site.site_title = "Scav Hunt Admin"
admin.site.index_title = "Welcome to Scavenger Hunt Administration"
