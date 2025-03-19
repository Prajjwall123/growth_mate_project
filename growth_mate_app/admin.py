from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'role', 'email', 'phone_number')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    list_filter = ('role', 'gender')

