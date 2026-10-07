from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


def profile_avatar_path(instance, filename):
    """Organize avatar uploads under media/avatars/<user_id>/"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f'avatars/{instance.user.pk}/avatar.{ext}'


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='ผู้ใช้งาน',
    )
    first_name = models.CharField(max_length=150, blank=True, verbose_name='ชื่อ')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='นามสกุล')
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='เบอร์โทรศัพท์',
        help_text='เช่น 0812345678',
    )
    avatar = models.ImageField(
        upload_to=profile_avatar_path,
        blank=True,
        null=True,
        verbose_name='รูปประจำตัว',
        help_text='รองรับไฟล์ PNG, JPG, WEBP (ขนาดไม่เกิน 5MB)',
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='คำแนะนำตัวสั้นๆ (Bio)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='สร้างเมื่อ')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='แก้ไขล่าสุด')

    class Meta:
        verbose_name = 'โปรไฟล์ผู้ใช้'
        verbose_name_plural = 'โปรไฟล์ผู้ใช้ทั้งหมด'

    def __str__(self):
        return f'โปรไฟล์ของ {self.user.username}'

    def get_full_name(self):
        name = f'{self.first_name} {self.last_name}'.strip()
        return name or self.user.get_full_name() or self.user.username

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None


class LoginEvent(models.Model):
    """Audit log for login/logout/security events (read-only audit trail)."""
    EVENT_CHOICES = [
        ('login', 'เข้าสู่ระบบสำเร็จ'),
        ('logout', 'ออกจากระบบ'),
        ('failed', 'เข้าสู่ระบบล้มเหลว'),
        ('locked', 'ถูกล็อคบัญชีชั่วคราว'),
        ('timeout', 'เซสชันหมดอายุ (Idle Timeout)'),
        ('password_change', 'เปลี่ยนรหัสผ่านสำเร็จ'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_events',
        verbose_name='ผู้ใช้',
    )
    username_attempt = models.CharField(max_length=150, blank=True, verbose_name='ชื่อผู้ใช้ที่ระบุ')
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES, verbose_name='ประเภทเหตุการณ์')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Address')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='เวลาที่บันทึก')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'บันทึกเหตุการณ์ความปลอดภัย'
        verbose_name_plural = 'บันทึกเหตุการณ์ความปลอดภัยทั้งหมด'

    def __str__(self):
        return f'[{self.get_event_type_display()}] {self.username_attempt or self.user} @ {self.ip_address}'


class SystemSetting(models.Model):
    """
    การตั้งค่าระบบและความปลอดภัยที่สามารถจัดการได้ผ่านหลังบ้าน (Django Admin)
    ตาม Requirement: มีเซสชั่น 60 นาทีหากไม่ทำอะไรให้ logout สามารถจัดการตั้งเวลาได้ ในหลังบ้าน
    """
    session_idle_timeout_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='ระยะเวลาเซสชันหมดอายุเมื่อไม่ใช้งาน (นาที)',
        help_text='ระบบจะบังคับให้ออกจากระบบอัตโนมัติเมื่อผู้ใช้ไม่มีการใช้งานตามเวลาที่กำหนด (ค่าเริ่มต้น 60 นาที)',
    )
    max_login_attempts = models.PositiveIntegerField(
        default=5,
        verbose_name='จำนวนครั้งล็อกอินผิดพลาดสูงสุดก่อนระงับ (ครั้ง)',
        help_text='เกณฑ์สำหรับป้องกันการโจมตีแบบ Brute-force (เช่น 5 ครั้ง)',
    )
    enable_security_audit_log = models.BooleanField(
        default=True,
        verbose_name='เปิดใช้งานระบบ Audit Log บันทึกเหตุการณ์ความปลอดภัย',
        help_text='บันทึก IP, User-Agent, เวลา เมื่อมีกิจกรรมเข้า-ออกจากระบบ',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='แก้ไขล่าสุดเมื่อ')

    class Meta:
        verbose_name = 'การตั้งค่าระบบและความปลอดภัย'
        verbose_name_plural = 'การตั้งค่าระบบและความปลอดภัย'

    def __str__(self):
        return f'การตั้งค่าระบบ (เซสชันหมดอายุ: {self.session_idle_timeout_minutes} นาที)'

    @classmethod
    def get_settings(cls):
        """Singleton pattern for system settings."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'session_idle_timeout_minutes': 60,
                'max_login_attempts': 5,
                'enable_security_audit_log': True,
            }
        )
        return obj
