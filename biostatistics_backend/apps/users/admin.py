from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "email",
        "full_name",
        "group",
        "university",
        "role",
        "is_active",
        "is_staff",
    )
    list_filter = ("is_active", "is_staff", "role")
    search_fields = ("email", "full_name", "group", "university")
    ordering = ("email",)

    fieldsets = (
        ("Негізгі ақпарат", {
            "fields": (
                "email",
                "password",
                "full_name",
                "group",
                "university",
                "role",
            )
        }),
        ("Құқықтар", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
    )

    add_fieldsets = (
        ("Жаңа қолданушы", {
            "classes": ("wide",),
            "fields": (
                "email",
                "full_name",
                "group",
                "university",
                "role",
                "password1",
                "password2",
                "is_active",
                "is_staff",
            ),
        }),
    )
