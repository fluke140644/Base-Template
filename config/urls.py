"""
URL configuration for NovaPulse Base Project.

Route structure:
    /               → Home starter page (login required)
    /accounts/      → Accounts app (login, logout, profile, password change)
    /admin/         → Django Admin (backend settings, audit logs, user management)
    /media/         → Media uploads (dev mode)
    /static/        → Static assets (dev mode)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home_view

urlpatterns = [
    # Root: Starter base page (requires authentication, redirects to /accounts/login/ if unauthenticated)
    path('', home_view, name='home'),

    # Accounts app (login, logout, profile, profile edit, password change)
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # Django Admin (หลังบ้าน)
    path('admin/', admin.site.urls),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
