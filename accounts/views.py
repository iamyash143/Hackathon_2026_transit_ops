from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .forms import EmailLoginForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = EmailLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        form.add_error(None, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def permission_denied_view(request, exception=None):
    return render(request, 'accounts/403.html', status=403)
