from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('fuel/',          views.FuelLogListView.as_view(),    name='fuel_log_list'),
    path('fuel/new/',      views.FuelLogCreateView.as_view(),  name='fuel_log_create'),
    path('expenses/',      views.ExpenseLogListView.as_view(), name='expense_log_list'),
    path('expenses/new/',  views.ExpenseLogCreateView.as_view(), name='expense_log_create'),
]
