from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    path('', views.MaintenanceListView.as_view(), name='maintenance_list'),
    path('<int:pk>/', views.MaintenanceDetailView.as_view(), name='maintenance_detail'),
    path('new/', views.MaintenanceCreateView.as_view(), name='maintenance_create'),
    path('<int:pk>/close/', views.maintenance_close, name='maintenance_close'),
]
