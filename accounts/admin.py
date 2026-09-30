from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "department", "employee_code")
    search_fields = (
        "user__username",
        "employee_code",
        "organization__name",
        "department__name",
    )
    list_filter = ("organization", "department")
    list_select_related = ("user", "organization", "department")
    autocomplete_fields = ("user",)
