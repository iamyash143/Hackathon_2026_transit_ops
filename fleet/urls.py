from django.urls import path
from accounts.decorators import fleet_manager_required
from . import views

app_name = 'fleet'

urlpatterns = [
    path('', views.VehicleListView.as_view(), name='vehicle_list'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('new/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('<int:pk>/retire/', views.vehicle_retire, name='vehicle_retire'),
]
