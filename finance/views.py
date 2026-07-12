from django.views.generic import ListView, CreateView
from accounts.mixins import RoleRequiredMixin
from .models import FuelLog, ExpenseLog
from .forms import FuelLogForm, ExpenseLogForm

class FuelLogListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst', 'Safety Officer']
    model = FuelLog
    template_name = 'finance/fuel_log_list.html'
    context_object_name = 'fuel_logs'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle', 'trip').order_by('-date')
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        return qs

class FuelLogCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst']
    model = FuelLog
    form_class = FuelLogForm
    template_name = 'finance/fuel_log_form.html'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance:fuel_log_list')

class ExpenseLogListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst', 'Safety Officer']
    model = ExpenseLog
    template_name = 'finance/expense_log_list.html'
    context_object_name = 'expense_logs'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle', 'trip').order_by('-date')
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        expense_type = self.request.GET.get('expense_type')
        if expense_type:
            qs = qs.filter(expense_type=expense_type)
        return qs

class ExpenseLogCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst', 'Driver']
    model = ExpenseLog
    form_class = ExpenseLogForm
    template_name = 'finance/expense_log_form.html'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance:expense_log_list')
