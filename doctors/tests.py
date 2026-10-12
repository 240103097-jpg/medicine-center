from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .models import Doctor


class DoctorTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name="Ada", specialty="Medicine", description="Profile")
        self.add = reverse("admin:doctors_doctor_add")
        self.change = reverse("admin:doctors_doctor_change", args=[self.doctor.pk])
        self.list = reverse("admin:doctors_doctor_changelist")
        self.data = {"name": "  Әлия  O'Neil  ", "specialty": "  General  medicine  ", "description": "  First line\nSecond line  ", "_save": "Save"}
        self.admin = get_user_model().objects.create_superuser(email="admin@example.test", password="test-only")

    def staff(self, *permissions):
        user = get_user_model().objects.create_user(email=f"staff{get_user_model().objects.count()}@example.test", is_staff=True)
        user.user_permissions.set(Permission.objects.filter(content_type__app_label="doctors", codename__in=permissions))
        self.client.force_login(user)
        return user

    def test_add_edit_and_invalid_submission_preserves_record(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(self.add, self.data), self.list)
        new = Doctor.objects.exclude(pk=self.doctor.pk).get()
        self.assertEqual(new.name, "Әлия  O'Neil")
        self.assertEqual(new.description, "First line\nSecond line")
        self.assertRedirects(self.client.post(self.change, self.data), self.list)
        for field, limit in (("name", 200), ("specialty", 200), ("description", 5000)):
            for invalid in ("  \n ", "x" * (limit + 1)):
                data = {**self.data, field: invalid}
                response = self.client.post(self.change, data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["adminform"].form.errors[field])
                self.doctor.refresh_from_db()
                self.assertEqual(self.doctor.name, "Әлия  O'Neil")
                response = self.client.post(self.add, data)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(Doctor.objects.count(), 2)

    def test_exact_boundaries_and_model_validation(self):
        self.client.force_login(self.admin)
        for length in (1, 200):
            data = {"name": " " + "x" * length + " ", "specialty": " " + "y" * length + " ", "description": " " + "z" * (1 if length == 1 else 5000) + " ", "_save": "Save"}
            self.assertEqual(self.client.post(self.add, data).status_code, 302)
        for field, limit in (("name", 200), ("specialty", 200), ("description", 5000)):
            for invalid in ("  ", "x" * (limit + 1)):
                instance = Doctor(name="A", specialty="B", description="C")
                setattr(instance, field, invalid)
                with self.assertRaises(ValidationError):
                    instance.full_clean()
        instance = Doctor(name=" A ", specialty=" B ", description=" C\nD ")
        instance.full_clean()
        self.assertEqual(instance.description, "C\nD")

    def test_nonstaff_and_inactive_cannot_administer(self):
        patient = get_user_model().objects.create_user(email="patient@example.test")
        inactive = get_user_model().objects.create_superuser(email="inactive@example.test", password="test-only", is_active=False)
        for user in (None, patient, inactive):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for url in (self.add, self.change, self.list):
                self.assertEqual(self.client.get(url).status_code, 302)
                self.assertEqual(self.client.post(url, self.data).status_code, 302)
            self.assertEqual(Doctor.objects.count(), 1)
            self.doctor.refresh_from_db()
            self.assertEqual(self.doctor.name, "Ada")

    def test_staff_permissions_and_direct_posts(self):
        self.staff()
        for url in (self.add, self.change, self.list):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, self.data).status_code, 403)
        self.staff("view_doctor")
        self.assertEqual(self.client.get(self.list).status_code, 200)
        self.assertEqual(self.client.get(self.change).status_code, 200)
        self.assertEqual(self.client.post(self.change, self.data).status_code, 403)
        self.assertEqual(self.client.get(self.add).status_code, 403)
        self.assertEqual(self.client.post(self.add, self.data).status_code, 403)
        self.staff("add_doctor")
        self.assertEqual(self.client.post(self.add, self.data).status_code, 302)
        self.assertEqual(self.client.get(self.change).status_code, 403)
        self.assertEqual(self.client.post(self.change, self.data).status_code, 403)
        self.staff("change_doctor")
        self.assertEqual(self.client.get(self.list).status_code, 200)
        self.assertEqual(self.client.get(self.change).status_code, 200)
        self.assertEqual(self.client.post(self.change, self.data).status_code, 302)
        self.assertEqual(self.client.post(self.add, self.data).status_code, 403)

    def test_admin_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for url in (self.add, self.change):
            self.assertEqual(client.post(url, self.data).status_code, 403)
            client.get(url)
            self.assertEqual(client.post(url, {**self.data, "csrfmiddlewaretoken": "bad"}).status_code, 403)
            token = client.cookies["csrftoken"].value
            self.assertEqual(client.post(url, {**self.data, "csrfmiddlewaretoken": token}).status_code, 302)

    def test_public_pages_order_empty_and_404(self):
        second = Doctor.objects.create(name="Ada", specialty="Second", description="Other")
        third = Doctor.objects.create(name="Zed", specialty="Third", description="Last")
        patient = get_user_model().objects.create_user(email="public@example.test")
        for user in (None, patient):
            if user:
                self.client.force_login(user)
            response = self.client.get("/doctors/")
            self.assertEqual(list(response.context["doctors"]), [self.doctor, second, third])
            self.assertContains(response, reverse("doctor_detail", args=[self.doctor.pk]))
            response = self.client.get(reverse("doctor_detail", args=[self.doctor.pk]))
            self.assertContains(response, "Profile")
            self.assertContains(response, "Back to doctors")
            self.assertEqual(self.client.get("/doctors/999999/").status_code, 404)
            self.assertEqual(self.client.get("/doctors/bad/").status_code, 404)
        Doctor.objects.all().delete()
        self.assertContains(self.client.get("/doctors/"), "No doctors are available yet")

    def test_text_escaped_and_navigation(self):
        text = '<script>alert("unsafe")</script>'
        self.doctor.name = self.doctor.specialty = self.doctor.description = text
        self.doctor.save()
        for url in ("/", "/doctors/", reverse("doctor_detail", args=[self.doctor.pk])):
            response = self.client.get(url)
            self.assertContains(response, 'href="/doctors/"')
            self.assertNotContains(response, text)
        response = self.client.get(reverse("doctor_detail", args=[self.doctor.pk]))
        self.assertContains(response, "&lt;script&gt;", count=4)
        self.client.force_login(self.admin)
        for url in (self.list, self.change):
            self.assertNotContains(self.client.get(url), text)
