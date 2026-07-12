from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from accounts.mixins import RoleRequiredMixin
from django.views.generic import View
from django.http import HttpResponse
from django.test import override_settings

User = get_user_model()

class DummyView(RoleRequiredMixin, View):
    allowed_roles = ['Fleet Manager']
    def get(self, request):
        return HttpResponse('Success')

class AuthenticationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password123')
        self.group = Group.objects.create(name='Fleet Manager')

    def test_login_redirect(self):
        # Just test login page
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_wrong_credentials(self):
        response = self.client.post(reverse('login'), {'email': 'test@example.com', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].non_field_errors()[0], 'Invalid email or password.')

    def test_correct_credentials(self):
        response = self.client.post(reverse('login'), {'email': 'test@example.com', 'password': 'password123'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')

    def test_role_required_mixin_wrong_role(self):
        # User has no role
        self.client.login(email='test@example.com', password='password123')
        # We need a URL to test the mixin
        # For now, let's just test the dispatch method directly
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        view = DummyView.as_view()
        # Should raise PermissionDenied which results in 403 when handled by middleware, but directly it raises exception
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            view(request)

    def test_role_required_mixin_correct_role(self):
        self.user.groups.add(self.group)
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        view = DummyView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_superuser_bypass(self):
        superuser = User.objects.create_superuser(email='admin@example.com', password='password123')
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = superuser
        
        view = DummyView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
