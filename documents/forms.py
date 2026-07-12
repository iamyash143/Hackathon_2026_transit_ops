from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit

from documents.models import Document
from documents.validators import validate_file_size


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "category", "file", "expiry_date", "vehicle", "driver"]
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        validate_file_size(uploaded_file)
        return uploaded_file

    def __init__(self, *args, **kwargs):
        initial_vehicle = kwargs.pop("initial_vehicle", None)
        initial_driver = kwargs.pop("initial_driver", None)
        super().__init__(*args, **kwargs)
        if initial_vehicle:
            self.fields["vehicle"].initial = initial_vehicle
        if initial_driver:
            self.fields["driver"].initial = initial_driver
        self.helper = FormHelper()
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.layout = Layout(
            Row(
                Column("title", css_class="w-full md:w-1/2"),
                Column("category", css_class="w-full md:w-1/2"),
            ),
            Row(
                Column("vehicle", css_class="w-full md:w-1/2"),
                Column("driver", css_class="w-full md:w-1/2"),
            ),
            Row(
                Column("expiry_date", css_class="w-full md:w-1/2"),
                Column("file", css_class="w-full md:w-1/2"),
            ),
            Submit(
                "submit",
                "Save Document",
                css_class=(
                    "mt-4 rounded-lg bg-blue-600 px-5 py-2.5 text-sm "
                    "font-medium text-white hover:bg-blue-700"
                ),
            ),
        )
