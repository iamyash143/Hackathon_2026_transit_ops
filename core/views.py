from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    """Render the temporary authenticated dashboard shell."""
    return render(request, 'core/dashboard.html')
