from django.contrib import admin

from .models import Challenge, Class, Category


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "short_description",
        "description",
        "flag",
        "points",
        "exclusive",
        "unblocked",
        "category",
    )
    list_display = ("name", "points", "exclusive", "unblocked", "locked", "category")
    list_filter = ("exclusive", "unblocked", "locked", "category")
    readonly_fields = ("locked",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "unblocked" in form.base_fields:
            form.base_fields["unblocked"].label = "Released"
            form.base_fields[
                "unblocked"
            ].help_text = "Controls whether this challenge is available to participants"
        return form

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
