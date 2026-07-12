"""
URL configuration for transit_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponseNotFound
from core import views as core_views

def unavailable_feature(request):
    return HttpResponseNotFound('This feature is not available yet.')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('vehicles/', include('fleet.urls', namespace='fleet')),
    path('', include('accounts.urls')),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('trips/', unavailable_feature, name='trip_list'),
    path('maintenance/', include('maintenance.urls', namespace='maintenance')),
    path('drivers/', include('drivers.urls', namespace='drivers')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('reports/', unavailable_feature, name='reports'),
]

handler403 = 'accounts.views.permission_denied_view'
