"""
accounts/middleware.py
—————————————————————————————
SessionIdleTimeoutMiddleware:
  - Logs user out automatically after idle session timeout.
  - The timeout value is read dynamically from SystemSetting (configurable via Django Admin 'หลังบ้าน').
  - On logout, records a 'timeout' event in LoginEvent audit log.
"""
from django.conf import settings
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
import datetime
import logging

logger = logging.getLogger('accounts.security')


class SessionIdleTimeoutMiddleware:
    """
    Enforces idle session expiry independent of SESSION_COOKIE_AGE.
    Runs on every authenticated request and reads configuration from backend.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Read dynamic timeout from SystemSetting (หลังบ้าน), fallback to settings.py
            timeout_minutes = getattr(settings, 'SESSION_IDLE_TIMEOUT_MINUTES', 60)
            try:
                from accounts.models import SystemSetting
                timeout_minutes = SystemSetting.get_settings().session_idle_timeout_minutes
            except Exception:
                pass

            last_activity_str = request.session.get('_last_activity')

            if last_activity_str:
                try:
                    last_activity = datetime.datetime.fromisoformat(last_activity_str)
                    if last_activity.tzinfo is None:
                        last_activity = last_activity.replace(tzinfo=datetime.timezone.utc)

                    idle_duration = timezone.now() - last_activity
                    if idle_duration > datetime.timedelta(minutes=timeout_minutes):
                        self._record_timeout(request)
                        logout(request)
                        messages.warning(
                            request,
                            f'เซสชันหมดอายุเนื่องจากไม่มีการใช้งานเป็นเวลา {timeout_minutes} นาที กรุณาเข้าสู่ระบบใหม่อีกครั้ง'
                        )
                        return redirect(settings.LOGIN_URL)
                except Exception as ex:
                    logger.debug('Error checking idle timeout: %s', ex)

            # Update last activity timestamp on every authenticated request
            request.session['_last_activity'] = timezone.now().isoformat()

        return self.get_response(request)

    @staticmethod
    def _record_timeout(request):
        """Write a 'timeout' event to LoginEvent if available."""
        try:
            from accounts.models import LoginEvent, SystemSetting
            setting = SystemSetting.get_settings()
            if not setting.enable_security_audit_log:
                return

            ip = _get_client_ip(request)
            LoginEvent.objects.create(
                user=request.user,
                username_attempt=request.user.username,
                event_type='timeout',
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            logger.info('SESSION TIMEOUT user=%s ip=%s', request.user.username, ip)
        except Exception:
            pass


def _get_client_ip(request):
    """Extract the real client IP, honoring X-Forwarded-For behind reverse proxies."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
