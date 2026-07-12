from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import Driver

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            'name', 'license_number', 'license_category',
            'license_expiry', 'contact_number', 'safety_score',
        ]
        widgets = {
            'license_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_safety_score(self):
        score = self.cleaned_data['safety_score']
        if not (0 <= score <= 100):
            raise forms.ValidationError('Safety score must be between 0 and 100.')
        return score

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='w-full md:w-1/2'),
                Column('contact_number', css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('license_number', css_class='w-full md:w-1/3'),
                Column('license_category', css_class='w-full md:w-1/3'),
                Column('license_expiry', css_class='w-full md:w-1/3'),
            ),
            'safety_score',
            Submit('submit', 'Save Driver',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
