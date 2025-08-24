from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Group, User

# Register your models here.


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email", "graduation_year")},
        ),
        (
            "Permissions",
            {"fields": ("is_student", "is_superuser", "_is_staff", "is_committee")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Preferences", {"fields": ("dark_mode",)}),
    )
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_student",
        "is_superuser",
        "_is_staff",
        "is_committee",
    )
    list_filter = (
        "is_student",
        "is_superuser",
        "_is_staff",
        "is_committee",
        "graduation_year",
    )
    search_fields = ("username", "first_name", "last_name", "email")
    readonly_fields = ("date_joined", "last_login")
    filter_horizontal = ()  # Remove default groups and user_permissions


admin.site.register(User, UserAdmin)
admin.site.register(Group)
