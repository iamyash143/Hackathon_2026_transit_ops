from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from accounts.mixins import SafetyOfficerMixin, RoleRequiredMixin
from accounts.decorators import safety_officer_required
from .models import Driver, DriverStatus
from .forms import DriverForm

class DriverListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Driver
    template_name = 'drivers/driver_list.html'
    context_object_name = 'drivers'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('name')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(license_number__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = DriverStatus.choices
        return ctx

class DriverDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Driver
    template_name = 'drivers/driver_detail.html'

class DriverCreateView(SafetyOfficerMixin, CreateView):
    model = Driver
    form_class = DriverForm
    template_name = 'drivers/driver_form.html'

class DriverUpdateView(SafetyOfficerMixin, UpdateView):
    model = Driver
    form_class = DriverForm
    template_name = 'drivers/driver_form.html'

@safety_officer_required
def driver_suspend(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.suspend()
        driver.save()
        messages.warning(request, f'{driver.name} has been suspended.')
    return redirect('drivers:driver_detail', pk=pk)

@safety_officer_required
def driver_reinstate(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.reinstate()
        driver.save()
        messages.success(request, f'{driver.name} has been reinstated.')
    return redirect('drivers:driver_detail', pk=pk)
