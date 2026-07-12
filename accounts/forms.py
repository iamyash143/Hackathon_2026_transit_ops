from django import forms

class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput)
