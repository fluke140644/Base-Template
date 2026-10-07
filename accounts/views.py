"""
accounts/views.py
—————————————————————
NovaPulse Base Template — Authentication & User Profile Views:
  • home_view: Clean starter canvas using base layout for extending future projects.
  • login_view: Rate-limited authentication with audit logging and axes protection.
  • logout_view: Secure CSRF-protected logout with audit log.
  • profile_view: Overview of user details, security status, and recent activity.
  • profile_edit_view: Multi-action form handling name, phone, bio, email, and avatar.
  • password_change_view: Secure password change with session preservation.
"""
import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import (
    AvatarForm,
    EmailForm,
    LoginForm,
    ProfileForm,
    StyledPasswordChangeForm,
)
from .models import LoginEvent, SystemSetting, UserProfile

logger = logging.getLogger('accounts.security')


def _get_client_ip(request):
    """Extract real client IP address."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_event(request, event_type: str, username: str = ''):
    """Create a LoginEvent audit record if enabled in SystemSetting."""
    try:
        setting = SystemSetting.get_settings()
        if not setting.enable_security_audit_log:
            return

        user_obj = request.user if request.user.is_authenticated else None
        target_username = username or (request.user.username if request.user.is_authenticated else '')
        LoginEvent.objects.create(
            user=user_obj,
            username_attempt=target_username,
            event_type=event_type,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    except Exception as ex:
        logger.debug('Audit log error: %s', ex)


# ─── Home / Starter Page ───────────────────────────────────────────────────────

@login_required
@never_cache
def home_view(request):
    """
    หน้าแรกของระบบ (Starter Base):
    แสดงเฉพาะโครงหน้า navbar, เมนู sidebar และภาพรวมระบบ สำหรับนำไปต่อยอดในโปรเจกต์ถัดไป
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    system_setting = SystemSetting.get_settings()

    # Recent security audit events for current user
    recent_events = LoginEvent.objects.filter(user=request.user)[:5]

    context = {
        'profile': profile,
        'system_setting': system_setting,
        'recent_events': recent_events,
    }
    return render(request, 'home.html', context)


# ─── Authentication ────────────────────────────────────────────────────────────

@never_cache
@sensitive_post_parameters('password')
@require_http_methods(['GET', 'POST'])
def login_view(request):
    """Login view with brute-force defense and audit trail."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    # Check if user came from idle timeout
    if request.GET.get('timeout') == '1':
        messages.warning(request, 'เซสชันหมดอายุเนื่องจากไม่มีการใช้งาน กรุณาเข้าสู่ระบบอีกครั้ง')

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Initialize activity timestamp for idle-timeout middleware
            request.session['_last_activity'] = timezone.now().isoformat()

            _log_event(request, 'login', username)
            logger.info('LOGIN SUCCESS user=%s ip=%s', username, _get_client_ip(request))
            messages.success(request, f'ยินดีต้อนรับกลับ, {user.get_full_name() or user.username}!')

            next_url = request.GET.get('next') or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)
        else:
            _log_event(request, 'failed', username)
            logger.warning('LOGIN FAILED user=%s ip=%s', username, _get_client_ip(request))

    return render(request, 'accounts/login.html', {'form': form})


@require_http_methods(['POST'])
def logout_view(request):
    """Secure CSRF-protected POST logout with audit trail."""
    username = request.user.username if request.user.is_authenticated else ''
    _log_event(request, 'logout', username)
    logger.info('LOGOUT user=%s ip=%s', username, _get_client_ip(request))
    auth_logout(request)
    messages.info(request, 'ออกจากระบบเรียบร้อยแล้ว')
    return redirect(settings.LOGOUT_REDIRECT_URL)


# ─── Profile Views ─────────────────────────────────────────────────────────────

@login_required
@never_cache
def profile_view(request):
    """Profile detail page with security audit overview."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    recent_events = LoginEvent.objects.filter(user=request.user)[:8]

    context = {
        'profile': profile,
        'recent_events': recent_events,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def profile_edit_view(request):
    """Edit name, phone, bio, avatar, and email."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    profile_form = ProfileForm(instance=profile)
    email_form = EmailForm(instance=user)
    avatar_form = AvatarForm(instance=profile)

    if request.method == 'POST':
        action = request.POST.get('_action', '')

        # 1. Update personal info (name, phone, bio)
        if action == 'profile':
            profile_form = ProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                with transaction.atomic():
                    updated = profile_form.save()
                    user.first_name = updated.first_name
                    user.last_name = updated.last_name
                    user.save(update_fields=['first_name', 'last_name'])
                messages.success(request, 'บันทึกข้อมูลส่วนตัวเรียบร้อยแล้ว!')
                return redirect('accounts:profile_edit')

        # 2. Update email
        elif action == 'email':
            email_form = EmailForm(request.POST, instance=user)
            if email_form.is_valid():
                email_form.save()
                messages.success(request, f'อัปเดตอีเมลเป็น "{user.email}" เรียบร้อยแล้ว!')
                return redirect('accounts:profile_edit')

        # 3. Update avatar
        elif action == 'avatar':
            avatar_form = AvatarForm(request.POST, request.FILES, instance=profile)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, 'อัปโหลดรูปประจำตัวใหม่สำเร็จ!')
                return redirect('accounts:profile_edit')

    context = {
        'profile': profile,
        'profile_form': profile_form,
        'email_form': email_form,
        'avatar_form': avatar_form,
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
@never_cache
@sensitive_post_parameters('old_password', 'new_password1', 'new_password2')
@require_http_methods(['GET', 'POST'])
def password_change_view(request):
    """Change password view with session security update."""
    if request.method == 'POST':
        form = StyledPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Prevent user from being logged out after password change
            update_session_auth_hash(request, user)
            _log_event(request, 'password_change')
            messages.success(request, 'เปลี่ยนรหัสผ่านเรียบร้อยแล้ว!')
            return redirect('accounts:profile')
    else:
        form = StyledPasswordChangeForm(user=request.user)

    return render(request, 'accounts/password_change.html', {'form': form})
