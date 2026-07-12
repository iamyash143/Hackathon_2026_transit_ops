from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.TripListView.as_view(), name='trip_list'),
    path('<int:pk>/', views.TripDetailView.as_view(), name='trip_detail'),
    path('new/', views.TripCreateView.as_view(), name='trip_create'),
    path('<int:pk>/dispatch/', views.trip_dispatch, name='trip_dispatch'),
    path('<int:pk>/complete/', views.trip_complete, name='trip_complete'),
    path('<int:pk>/cancel/', views.trip_cancel, name='trip_cancel'),
]
