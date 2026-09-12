from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organizacion", "departamento", "employee_code")
    search_fields = (
        "user__username",
        "employee_code",
        "organizacion__nombre",
        "departamento__nombre",
    )
    list_filter = ("organizacion", "departamento")
    list_select_related = ("user", "organizacion", "departamento")
    autocomplete_fields = ("user",)