import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile


# ─── Helpers ──────────────────────────────────────────────────────────────────

PHONE_RE = re.compile(r'^[0-9\-\+\(\)\s]{7,20}$')
AVATAR_MAX_BYTES = 5 * 1024 * 1024   # 5 MB


# ─── Login Form ───────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    """Custom login form with styled widgets."""
    username = forms.CharField(
        label='ชื่อผู้ใช้ (Username)',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'กรอก username ของคุณ',
            'autofocus': True,
            'autocomplete': 'username',
            'id': 'id_login_username',
        }),
    )
    password = forms.CharField(
        label='รหัสผ่าน',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
            'id': 'id_login_password',
        }),
    )


# ─── Profile Edit Form ────────────────────────────────────────────────────────

class ProfileForm(forms.ModelForm):
    """Edit UserProfile fields: name, phone, bio."""

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'phone', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'ชื่อจริง',
                'id': 'id_profile_first_name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'นามสกุล',
                'id': 'id_profile_last_name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'เช่น 081-234-5678',
                'id': 'id_profile_phone',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'แนะนำตัวสั้นๆ เกี่ยวกับคุณ...',
                'id': 'id_profile_bio',
                'maxlength': 500,
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not PHONE_RE.match(phone):
            raise ValidationError('รูปแบบเบอร์โทรศัพท์ไม่ถูกต้อง (ตัวอย่าง: 081-234-5678)')
        return phone


class AvatarForm(forms.ModelForm):
    """Separate mini-form to handle avatar upload with size and format validation."""

    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={
                'class': 'avatar-file-input',
                'accept': 'image/png, image/jpeg, image/webp',
                'id': 'id_avatar_upload',
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > AVATAR_MAX_BYTES:
                raise ValidationError('ขนาดไฟล์รูปภาพต้องไม่เกิน 5 MB')
            content_type = getattr(avatar, 'content_type', '')
            if content_type and content_type not in ('image/jpeg', 'image/png', 'image/webp'):
                raise ValidationError('รองรับเฉพาะไฟล์รูปภาพ PNG, JPG หรือ WebP เท่านั้น')
        return avatar


class EmailForm(forms.ModelForm):
    """Dedicated form to change email (with uniqueness check)."""

    email = forms.EmailField(
        label='อีเมล',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'yourname@example.com',
            'autocomplete': 'email',
            'id': 'id_profile_email',
        }),
    )

    class Meta:
        model = User
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if not email:
            raise ValidationError('กรุณาระบุที่อยู่อีเมล')
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('อีเมลนี้ถูกใช้งานแล้วในระบบ กรุณาใช้อีเมลอื่น')
        return email


class StyledPasswordChangeForm(PasswordChangeForm):
    """Sleek password change form with styled widgets."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input'})
