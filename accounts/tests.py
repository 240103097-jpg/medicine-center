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
