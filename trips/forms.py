from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit

from drivers.models import Driver
from fleet.models import Vehicle
from trips.models import Trip


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = [
            "vehicle",
            "driver",
            "source",
            "source_lat",
            "source_lng",
            "destination",
            "destination_lat",
            "destination_lng",
            "cargo_weight",
            "planned_distance",
        ]
        widgets = {
            "source_lat": forms.HiddenInput(),
            "source_lng": forms.HiddenInput(),
            "destination_lat": forms.HiddenInput(),
            "destination_lng": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.dispatchable()
        self.fields["driver"].queryset = Driver.eligible()
        self.fields["planned_distance"].widget.attrs.update(
            {
                "step": "0.01",
                "data-route-distance": "true",
            }
        )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("vehicle", css_class="w-full md:w-1/2"),
                Column("driver", css_class="w-full md:w-1/2"),
            ),
            Row(
                Column("source", css_class="w-full md:w-1/2"),
                Column("destination", css_class="w-full md:w-1/2"),
            ),
            "source_lat",
            "source_lng",
            "destination_lat",
            "destination_lng",
            Row(
                Column("cargo_weight", css_class="w-full md:w-1/2"),
                Column("planned_distance", css_class="w-full md:w-1/2"),
            ),
            Submit(
                "submit",
                "Save Draft",
                css_class=(
                    "mt-4 rounded-lg bg-blue-600 px-5 py-2.5 text-sm "
                    "font-medium text-white hover:bg-blue-700"
                ),
            ),
        )


# Kept as an alias for the Phase-3 workflow and its existing imports.
TripCreateForm = TripForm

class TripCompleteForm(forms.Form):
    final_odometer = forms.IntegerField(min_value=0, label='Final Odometer (km)')
    fuel_consumed  = forms.DecimalField(max_digits=8, decimal_places=2,
                                        min_value=0.1, label='Fuel Consumed (litres)')
    fuel_cost      = forms.DecimalField(max_digits=10, decimal_places=2,
                                        min_value=0, label='Fuel Cost (₹)')

    def __init__(self, *args, trip=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.trip = trip
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'final_odometer',
            'fuel_consumed',
            'fuel_cost',
            Submit('submit', 'Complete Trip',
                   css_class='text-white bg-green-600 hover:bg-green-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )

    def clean_final_odometer(self):
        odometer = self.cleaned_data['final_odometer']
        if self.trip and odometer <= self.trip.vehicle.odometer:
            raise forms.ValidationError(
                f'Final odometer must be greater than current reading '
                f'({self.trip.vehicle.odometer} km).'
            )
        return odometer
