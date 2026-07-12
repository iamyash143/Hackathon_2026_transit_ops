"""URL configuration for the TransitOps project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import include, path
from django.views.generic import RedirectView

from core import views as core_views


def unavailable_feature(request):
    """Return a safe response for a Phase 1 navigation placeholder."""
    return HttpResponseNotFound('This feature is not available yet.')

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard:home', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('documents/', include('documents.urls', namespace='documents')),
    path('vehicles/', include('fleet.urls', namespace='fleet')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('drivers/', include('drivers.urls', namespace='drivers')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('trips/', include('trips.urls', namespace='trips')),
    path('maintenance/', include('maintenance.urls', namespace='maintenance')),
    path('reports/', include('reports.urls', namespace='reports')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'accounts.views.permission_denied_view'
