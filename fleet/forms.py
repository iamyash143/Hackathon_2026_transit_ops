from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import Vehicle

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'registration_number', 'name', 'vehicle_type',
            'max_load_capacity', 'odometer', 'acquisition_cost',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('registration_number', css_class='w-full md:w-1/2'),
                Column('name', css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('vehicle_type', css_class='w-full md:w-1/3'),
                Column('max_load_capacity', css_class='w-full md:w-1/3'),
                Column('acquisition_cost', css_class='w-full md:w-1/3'),
            ),
            'odometer',
            Submit('submit', 'Save Vehicle',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
