from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse

from accounts.mixins import FleetManagerMixin, RoleRequiredMixin
from accounts.decorators import fleet_manager_required
from .models import MaintenanceLog, MaintenanceStatus
from .forms import MaintenanceCreateForm, MaintenanceCloseForm

class MaintenanceListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Safety Officer', 'Financial Analyst']
    model = MaintenanceLog
    template_name = 'maintenance/maintenance_list.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle').order_by('-created_at')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        return qs

    def get_context_data(self, **kwargs):
        from fleet.models import Vehicle
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['vehicle_filter'] = self.request.GET.get('vehicle', '')
        context['vehicles'] = Vehicle.objects.all()
        context['status_choices'] = MaintenanceStatus.choices
        return context

class MaintenanceDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Safety Officer', 'Financial Analyst']
    model = MaintenanceLog
    template_name = 'maintenance/maintenance_detail.html'
    context_object_name = 'log'

class MaintenanceCreateView(FleetManagerMixin, CreateView):
    model = MaintenanceLog
    form_class = MaintenanceCreateForm
    template_name = 'maintenance/maintenance_form.html'

    def get_success_url(self):
        return reverse('maintenance:maintenance_detail', kwargs={'pk': self.object.pk})

@fleet_manager_required
def maintenance_close(request, pk):
    log = get_object_or_404(MaintenanceLog, pk=pk)
    if log.status == MaintenanceStatus.CLOSED:
        messages.warning(request, 'This maintenance record is already closed.')
        return redirect('maintenance:maintenance_detail', pk=pk)

    if request.method == 'POST':
        form = MaintenanceCloseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                log.cost           = form.cleaned_data['final_cost']
                log.retire_on_close = form.cleaned_data['retire_on_close']
                log.odometer_at_service = log.vehicle.odometer
                log.status         = MaintenanceStatus.CLOSED
                log.save()          # post_save signal handles vehicle FSM
            messages.success(request, 'Maintenance record closed.')
            return redirect('maintenance:maintenance_detail', pk=pk)
    else:
        form = MaintenanceCloseForm(initial={
            'final_cost': log.cost,
            'retire_on_close': log.retire_on_close,
        })

    return render(request, 'maintenance/maintenance_close_form.html', {
        'log': log,
        'form': form
    })
