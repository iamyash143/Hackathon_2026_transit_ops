from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from fleet.models import Vehicle, VehicleStatus
from .models import MaintenanceLog

class MaintenanceCreateForm(forms.ModelForm):
    class Meta:
        model = MaintenanceLog
        fields = ['vehicle', 'date', 'description', 'cost']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            # Allow all vehicles during validation so clean_vehicle can raise specific errors
            self.fields['vehicle'].queryset = Vehicle.objects.all()
        else:
            # Only display Available vehicles in the dropdown selection
            self.fields['vehicle'].queryset = Vehicle.objects.filter(
                status=VehicleStatus.AVAILABLE
            )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle', css_class='w-full md:w-1/2'),
                Column('date',    css_class='w-full md:w-1/2'),
            ),
            'description',
            'cost',
            Submit('submit', 'Open Maintenance Record',
                   css_class='text-white bg-yellow-500 hover:bg-yellow-600 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )

    def clean_vehicle(self):
        vehicle = self.cleaned_data.get('vehicle')
        if not vehicle:
            return vehicle

        open_log_exists = MaintenanceLog.objects.filter(
            vehicle=vehicle, status='Open'
        ).exists()
        if open_log_exists:
            raise forms.ValidationError(
                f'{vehicle} already has an open maintenance record.'
            )

        if vehicle.status == VehicleStatus.ON_TRIP:
            raise forms.ValidationError(
                f'{vehicle} is currently on a trip and cannot be placed under maintenance.'
            )
        return vehicle

class MaintenanceCloseForm(forms.Form):
    final_cost      = forms.DecimalField(max_digits=10, decimal_places=2,
                                         min_value=0, label='Final Cost (₹)')
    retire_on_close = forms.BooleanField(required=False, label='Retire vehicle after closing')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'final_cost',
            'retire_on_close',
            Submit('submit', 'Close Maintenance Record',
                   css_class='text-white bg-red-600 hover:bg-red-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
