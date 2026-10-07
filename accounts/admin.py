from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, LoginEvent, SystemSetting

# Custom admin site branding
admin.site.site_header = "ระบบจัดการหลังบ้าน | NovaPulse Base"
admin.site.site_title = "NovaPulse Admin"
admin.site.index_title = "แผงควบคุมระบบและความปลอดภัย (Admin Center)"


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'โปรไฟล์'
    verbose_name_plural = 'ข้อมูลโปรไฟล์เพิ่มเติม'
    fields = ('first_name', 'last_name', 'phone', 'avatar', 'bio')


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')


# Re-register User with inline profile
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name', 'phone', 'updated_at')
    search_fields = ('user__username', 'first_name', 'last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'event_type', 'username_attempt', 'ip_address', 'user')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('username_attempt', 'ip_address', 'user__username')
    readonly_fields = ('timestamp', 'event_type', 'username_attempt', 'ip_address', 'user_agent', 'user')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False  # Read-only audit log

    def has_change_permission(self, request, obj=None):
        return False  # Read-only audit log

    def has_delete_permission(self, request, obj=None):
        # Only superusers can purge audit trail if necessary
        return request.user.is_superuser


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """
    จัดการการตั้งค่าระบบและความปลอดภัยหลังบ้าน:
    - ตั้งเวลาหมดอายุของเซสชั่น (นาที) เช่น 60 นาที
    - ป้องกัน Brute-force
    - Audit Log
    """
    list_display = ('__str__', 'session_idle_timeout_minutes', 'max_login_attempts', 'enable_security_audit_log', 'updated_at')
    fieldsets = (
        ('การจัดการเซสชัน (Session Timeout)', {
            'description': 'กำหนดเวลาออกจากระบบอัตโนมัติหากผู้ใช้ไม่ได้ทำกิจกรรมใดๆ ตาม Requirement',
            'fields': ('session_idle_timeout_minutes',),
        }),
        ('ความปลอดภัยไซเบอร์ (Cyber Security)', {
            'description': 'การควบคุมความปลอดภัยและการป้องกันการโจมตี',
            'fields': ('max_login_attempts', 'enable_security_audit_log'),
        }),
        ('ข้อมูลการบันทึก', {
            'fields': ('updated_at',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        # Singleton pattern: only allow adding if no instance exists yet
        return not SystemSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
