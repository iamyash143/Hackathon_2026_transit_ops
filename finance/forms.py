from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from fleet.models import Vehicle
from .models import FuelLog, ExpenseLog

class FuelLogForm(forms.ModelForm):
    class Meta:
        model = FuelLog
        fields = ['vehicle', 'trip', 'liters', 'cost', 'date']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trip'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle', css_class='w-full md:w-1/2'),
                Column('trip',    css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('liters', css_class='w-full md:w-1/3'),
                Column('cost',   css_class='w-full md:w-1/3'),
                Column('date',   css_class='w-full md:w-1/3'),
            ),
            Submit('submit', 'Add Fuel Log',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )

class ExpenseLogForm(forms.ModelForm):
    class Meta:
        model = ExpenseLog
        fields = ['vehicle', 'trip', 'expense_type', 'amount', 'date', 'notes']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trip'].required = False
        self.fields['notes'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle',      css_class='w-full md:w-1/2'),
                Column('trip',         css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('expense_type', css_class='w-full md:w-1/3'),
                Column('amount',       css_class='w-full md:w-1/3'),
                Column('date',         css_class='w-full md:w-1/3'),
            ),
            'notes',
            Submit('submit', 'Add Expense',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
