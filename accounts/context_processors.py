from django.conf import settings


def system_settings(request):
    """
    Expose dynamic system settings (like session idle timeout) to all templates.
    """
    timeout_minutes = getattr(settings, 'SESSION_IDLE_TIMEOUT_MINUTES', 60)
    try:
        from accounts.models import SystemSetting
        setting = SystemSetting.get_settings()
        timeout_minutes = setting.session_idle_timeout_minutes
    except Exception:
        pass

    return {
        'session_timeout_minutes': timeout_minutes,
    }
