from django.contrib import admin
from .models import User, UserProfile, Organisation

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'phone')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    ordering = ('-date_joined',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'org', 'first_name', 'last_name')
    search_fields = ('user__email', 'user__phone', 'first_name', 'last_name')
    list_filter = ('user_type', 'org')
    raw_id_fields = ('user',)

@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'created_at')
    search_fields = ('name', 'address')
    list_filter = ('created_at',)
    filter_horizontal = ('central_admins',)
