from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django import forms
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from .models import Challenge, Class, Category


class ReleaseStatusFilter(admin.SimpleListFilter):
    title = "release status"
    parameter_name = "release_status"

    def lookups(self, request, model_admin):
        return (
            ("released", "Released"),
            ("scheduled", "Scheduled (Timed)"),
            ("not_released", "Not Released"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "released":
            return queryset.filter(
                Q(unblocked=True) | Q(timed_release=True, release_time__lte=now)
            )
        elif self.value() == "scheduled":
            return queryset.filter(
                timed_release=True, release_time__gt=now, unblocked=False
            )
        elif self.value() == "not_released":
            return queryset.filter(
                Q(unblocked=False)
                & (
                    Q(timed_release=False)
                    | Q(release_time__isnull=True)
                    | Q(release_time__gt=now)
                )
            )


class ChallengeAdminForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = "__all__"
        widgets = {
            "required_challenges": forms.SelectMultiple(attrs={"size": "10"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "required_challenges" in self.fields:
            # Always start with all challenges, JavaScript will filter appropriately
            if self.instance and self.instance.pk:
                # For existing challenges, exclude self
                self.fields["required_challenges"].queryset = Challenge.objects.exclude(
                    pk=self.instance.pk
                ).select_related("category")
            else:
                # For new challenges, show all challenges initially
                self.fields[
                    "required_challenges"
                ].queryset = Challenge.objects.all().select_related("category")

    def clean(self):
        cleaned_data = super().clean()
        challenge_type = cleaned_data.get("challenge_type")
        required_challenges = cleaned_data.get("required_challenges")
        required_challenges_count = cleaned_data.get("required_challenges_count")

        # Only validate for unlocking type
        if challenge_type == "unlocking":
            if required_challenges:
                # Check for circular dependencies
                def would_create_cycle(challenge, required_challenges_list):
                    """Check if adding these required challenges would create a dependency cycle"""
                    for req_challenge in required_challenges_list:
                        if req_challenge == challenge:
                            return True
                        # Check if req_challenge depends on challenge (directly or indirectly)
                        if req_challenge.is_unlocking:
                            req_deps = list(req_challenge.required_challenges.all())
                            if challenge in req_deps or would_create_cycle(
                                challenge, req_deps
                            ):
                                return True
                    return False

                if self.instance and would_create_cycle(
                    self.instance, list(required_challenges)
                ):
                    raise forms.ValidationError(
                        "The selected required challenges would create a circular dependency."
                    )

            # Validate required_challenges_count
            if required_challenges_count is not None and required_challenges_count > 0:
                if not required_challenges:
                    raise forms.ValidationError(
                        "You must select required challenges if specifying a required count."
                    )
                elif required_challenges_count > len(required_challenges):
                    raise forms.ValidationError(
                        f"Required challenges count ({required_challenges_count}) cannot be greater than the number of selected challenges ({len(required_challenges)})."
                    )

        # Validate timed release fields
        timed_release = cleaned_data.get("timed_release")
        release_time = cleaned_data.get("release_time")

        if timed_release and not release_time:
            raise forms.ValidationError(
                "Release time must be specified when timed release is enabled."
            )

        return cleaned_data


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    form = ChallengeAdminForm
    fields = (
        "name",
        "short_description",
        "flag",
        "points",
        "challenge_type",
        "decay_percentage",
        "category",
        "required_challenges",
        "required_challenges_count",
        "unblocked",
        "timed_release",
        "release_time",
    )
    list_display = (
        "name",
        "points",
        "challenge_type_display",
        "release_status",
        "locked",
        "category",
        "submissions_link",
    )
    list_filter = ("challenge_type", ReleaseStatusFilter, "locked", "category")
    list_editable = ("points",)
    ordering = ("category", "order", "name")
    readonly_fields = ("locked",)
    search_fields = ("name", "short_description")

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

        if "required_challenges" in form.base_fields:
            form.base_fields[
                "required_challenges"
            ].help_text = "Hold Ctrl (or Cmd on Mac) to select multiple challenges that must be completed before this unlocking challenge becomes available. Only challenges from the same category are shown. (Only applies to 'Unlocking' type)"

        if "required_challenges_count" in form.base_fields:
            form.base_fields[
                "required_challenges_count"
            ].help_text = "How many of the selected required challenges must be completed to unlock this challenge. Leave as 0 to require all selected challenges. (Only applies to 'Unlocking' type)"

        if "timed_release" in form.base_fields:
            form.base_fields[
                "timed_release"
            ].help_text = "Enable automatic release at a scheduled date and time"

        if "release_time" in form.base_fields:
            form.base_fields[
                "release_time"
            ].help_text = "Date and time when this challenge should be automatically released (only used if timed release is enabled)"

        return form

    class Media:
        js = ("admin/js/challenge_admin.js",)
        css = {"all": ("admin/css/challenge_admin.css",)}

    def submissions_link(self, obj):
        """Link to view submissions for this challenge"""
        if obj.pk:
            url = reverse("logging:challenge_submissions", args=[obj.pk])
            return format_html('<a href="{}" target="_blank">View Submissions</a>', url)
        return "-"

    submissions_link.short_description = "Submissions"

    def decay_percentage_display(self, obj):
        """Show decay percentage only for decreasing challenges"""
        if obj.challenge_type == "decreasing":
            return f"{obj.decay_percentage}%"
        return "-"

    decay_percentage_display.short_description = "Decay %"
    decay_percentage_display.admin_order_field = "decay_percentage"

    def release_status(self, obj):
        """Show release status combining manual and timed release"""
        if obj.unblocked:
            return format_html('<span style="color: green;">✓ Released</span>')
        elif obj.timed_release and obj.release_time:
            from django.utils import timezone

            if timezone.now() >= obj.release_time:
                return format_html(
                    '<span style="color: green;">✓ Released (Timed)</span>'
                )
            else:
                return format_html('<span style="color: orange;">⏰ Scheduled</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Released</span>')

    release_status.short_description = "Release Status"

    def challenge_type_display(self, obj):
        """Show challenge type with additional info for special types"""
        type_display = obj.get_challenge_type_display()

        if obj.challenge_type == "decreasing":
            return f"{type_display} ({obj.decay_percentage}%)"
        elif obj.challenge_type == "unlocking" and obj.required_challenges.exists():
            count = obj.required_challenges.count()
            needed = (
                obj.required_challenges_count
                if obj.required_challenges_count > 0
                else count
            )
            return f"{type_display} ({needed}/{count})"
        elif obj.challenge_type == "exclusive":
            return f"{type_display}"
        else:
            return type_display

    challenge_type_display.short_description = "Type"
    challenge_type_display.admin_order_field = "challenge_type"

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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "get_category_challenges/",
                self.admin_site.admin_view(self.get_category_challenges),
                name="challenge_get_category_challenges",
            ),
        ]
        return custom_urls + urls

    def get_category_challenges(self, request):
        """AJAX endpoint to get challenges for a specific category"""
        category_id = request.GET.get("category_id")
        if not category_id:
            return JsonResponse({"challenges": []})

        try:
            challenges = Challenge.objects.filter(category_id=category_id).values(
                "id", "name"
            )
            return JsonResponse({"challenges": list(challenges)})
        except Exception:
            return JsonResponse({"challenges": []})


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
