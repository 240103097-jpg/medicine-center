from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('patient@example.com', 'test-only-password', first_name='Alex', last_name='Smith')

    def test_password_and_email_authentication(self):
        self.assertNotEqual(self.user.password, 'test-only-password')
        self.assertTrue(self.user.check_password('test-only-password'))
        self.assertFalse(self.user.check_password('incorrect'))
        self.assertEqual(authenticate(email=self.user.email, password='test-only-password'), self.user)
        self.assertEqual((self.user.first_name, self.user.last_name), ('Alex', 'Smith'))

    def test_duplicate_email_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(self.user.email, 'another-test-password')

    def test_ordinary_user_has_no_admin_permissions(self):
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('admin:index')), '/admin/login/?next=/admin/')

    def test_superuser_permissions_cannot_be_disabled(self):
        for field in ('is_staff', 'is_superuser'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                User.objects.create_superuser('admin@example.com', 'test-only-password', **{field: False})

    def test_email_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user('', 'test-only-password')


class BootstrapTests(TestCase):
    def test_home(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Medicine Center', status_code=200)
        self.assertContains(response, '<html lang="en">')

    def test_anonymous_admin_is_protected(self):
        self.assertRedirects(self.client.get(reverse('admin:index')), '/admin/login/?next=/admin/')

    def test_administrator_email_login(self):
        admin = User.objects.create_superuser('admin@example.com', 'test-only-password')
        response = self.client.post(reverse('admin:login'), {'username': admin.email, 'password': 'test-only-password', 'next': '/admin/'})
        self.assertRedirects(response, reverse('admin:index'))
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:accounts_user_add')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:accounts_user_change', args=[admin.pk])).status_code, 200)


class PatientAuthenticationTests(TestCase):
    def setUp(self):
        import secrets
        self.password = secrets.token_urlsafe(24) + '!47'
        self.data = dict(first_name=' Alex ', last_name=' Smith ', email=' Alex@Example.COM ', password1=self.password, password2=self.password)

    def register(self, **changes):
        return self.client.post('/register/', self.data | changes)

    def test_pages_navigation_and_registration(self):
        self.assertContains(self.client.get('/'), '/register/')
        self.assertContains(self.client.get('/'), '/login/')
        self.assertContains(self.client.get('/register/'), 'password2')
        self.assertContains(self.client.get('/login/'), 'Email')
        response = self.register(is_staff='True', is_superuser='True', groups='1', user_permissions='1')
        self.assertRedirects(response, '/login/', fetch_redirect_response=False)
        user = User.objects.get()
        self.assertEqual((user.email, user.first_name, user.last_name), ('alex@example.com', 'Alex', 'Smith'))
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertFalse(user.groups.exists() or user.user_permissions.exists())
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(self.client.get('/login/'), 'Account created. Please sign in.')

    def test_required_fields(self):
        for field in self.data:
            with self.subTest(field=field):
                response = self.register(**{field: '   ' if field in ('first_name', 'last_name', 'email') else ''})
                self.assertIn(field, response.context['form'].errors)
                self.assertEqual(User.objects.count(), 0)

    def test_empty_registration_submission(self):
        response = self.client.post('/register/', {})
        self.assertEqual(set(response.context['form'].errors), set(self.data))
        self.assertEqual(User.objects.count(), 0)

    def test_lengths_email_and_password_confirmation(self):
        for changes in ({'first_name': 'x'*151}, {'last_name': 'x'*151}, {'email': 'invalid'}, {'email': 'x'*245+'@example.com'}, {'password2': 'mismatch'}):
            with self.subTest(changes=list(changes)):
                response = self.register(**changes)
                self.assertTrue(response.context['form'].errors)
                self.assertNotContains(response, self.password)
                self.assertEqual(User.objects.count(), 0)

    def test_all_password_validators(self):
        for password in ('aB!4', 'AlexSmith', 'password', '9374652810'):
            with self.subTest(validator_password_length=len(password)):
                response = self.register(password1=password, password2=password)
                self.assertIn('password2', response.context['form'].errors)
                self.assertEqual(User.objects.count(), 0)

    def test_duplicate_and_existing_mixed_case_login(self):
        user = User.objects.create_user('Alex@Example.COM', self.password)
        response = self.register()
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)
        response = self.client.post('/login/', {'username': ' ALEX@example.com ', 'password': self.password})
        self.assertRedirects(response, '/')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_conflicting_validated_forms_are_handled(self):
        from .forms import RegistrationForm
        first, second = RegistrationForm(self.data), RegistrationForm(self.data | {'email': 'alex@example.com'})
        self.assertTrue(first.is_valid())
        self.assertTrue(second.is_valid())
        self.assertIsNotNone(first.save())
        self.assertIsNone(second.save())
        self.assertIn('email', second.errors)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_login_same_error_and_required_fields(self):
        user = User.objects.create_user('alex@example.com', self.password)
        errors = []
        for email, password, active in [('alex@example.com', 'wrong', True), ('unknown@example.com', self.password, True), ('alex@example.com', self.password, False)]:
            user.is_active = active
            user.save()
            response = self.client.post('/login/', {'username': email, 'password': password})
            errors.append(response.context['form'].non_field_errors())
            self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(errors[1], errors[2])
        response = self.client.post('/login/', {'username': '', 'password': ''})
        self.assertEqual(set(response.context['form'].errors), {'username', 'password'})

    def test_patient_cannot_access_or_post_admin(self):
        self.register()
        self.client.post('/login/', {'username': 'alex@example.com', 'password': self.password})
        for method in (self.client.get, self.client.post):
            response = method('/admin/accounts/user/add/', {'is_staff': 'True', 'is_superuser': 'True'})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith('/admin/login/'))
        user = User.objects.get()
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertContains(self.client.get('/'), 'Signed in as alex@example.com')

    def test_safe_next_direct_post(self):
        User.objects.create_user('alex@example.com', self.password)
        cases = [('', False, '/'), ('/register/', False, '/register/'), ('http://testserver/register/', False, 'http://testserver/register/'), ('https://testserver/register/', True, 'https://testserver/register/'), ('relative', False, '/'), ('https://evil.example/', False, '/'), ('//evil.example/', False, '/'), ('javascript:alert(1)', False, '/'), ('http://testserver/', True, '/'), ('/\\evil.example/', False, '/'), ('///evil.example/', False, '/')]
        for target, secure, expected in cases:
            with self.subTest(target=target, secure=secure):
                self.client.logout()
                response = self.client.post('/login/', {'username': 'alex@example.com', 'password': self.password, 'next': target}, secure=secure)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, expected)

    def test_logout_post_only_and_feedback(self):
        user = User.objects.create_user('alex@example.com', self.password)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.client.get('/register/')
        self.client.get('/login/')
        self.assertIn('_auth_user_id', self.client.session)
        response = self.client.post('/logout/')
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(self.client.get('/'), 'You have signed out.')
        self.assertRedirects(self.client.get('/admin/'), '/admin/login/?next=/admin/')

    def test_csrf_enforcement_each_form(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        user = User.objects.create_user('existing@example.com', self.password)
        for url, data in [('/register/', self.data), ('/login/', {'username': user.email, 'password': self.password})]:
            for token in (None, 'invalid'):
                response = client.post(url, data | ({'csrfmiddlewaretoken': token} if token else {}))
                self.assertEqual(response.status_code, 403)
                self.assertEqual(User.objects.count(), 1)
                self.assertNotIn('_auth_user_id', client.session)
        client.get('/register/')
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/register/', self.data | {'csrfmiddlewaretoken': token}).status_code, 302)
        client.get('/login/')
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/login/', {'username': 'alex@example.com', 'password': self.password, 'csrfmiddlewaretoken': token}).status_code, 302)
        for token in (None, 'invalid'):
            self.assertEqual(client.post('/logout/', {'csrfmiddlewaretoken': token} if token else {}).status_code, 403)
            self.assertIn('_auth_user_id', client.session)
        client.get('/')
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/logout/', {'csrfmiddlewaretoken': token}).status_code, 302)
        self.assertNotIn('_auth_user_id', client.session)
