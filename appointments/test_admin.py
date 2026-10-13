from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from appointments.models import Appointment
from doctors.models import Doctor
from scheduling.models import Slot


class AdminAppointmentsTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(email="admin@example.com", password="Test-only-4981!")
        self.patient = get_user_model().objects.create_user(email="patient@example.com", first_name="<script>Patient</script>")
        self.staff = get_user_model().objects.create_user(email="staff@example.com", is_staff=True)
        self.doctor = Doctor.objects.create(name="<script>Doctor</script>", specialty="Care", description="Care")
        self.slot = Slot.objects.create(doctor=self.doctor, start=timezone.now()+timedelta(days=3))
        self.obj = Appointment.objects.create(patient=self.patient, slot=self.slot)
        self.root = "/admin/appointments/appointment/"
        self.detail = f"{self.root}{self.obj.pk}/change/"
        self.client.force_login(self.admin)

    def action(self, name):
        return f"{self.root}{self.obj.pk}/{name}/"

    def test_list_detail_empty_order_timezone_escape(self):
        page = self.client.get(self.root)
        for text in ("patient@example.com", "Asia/Almaty", "30 minutes", "Booked", "&lt;script&gt;Doctor&lt;/script&gt;", "&lt;script&gt;Patient&lt;/script&gt;"):
            self.assertContains(page, text)
        self.assertContains(self.client.get(self.detail), "Cancel appointment")
        other = Appointment.objects.create(patient=self.staff, slot=self.slot, status="Cancelled")
        self.assertEqual([o.pk for o in self.client.get(self.root).context["cl"].result_list], [other.pk, self.obj.pk])
        Appointment.objects.all().delete()
        self.assertContains(self.client.get(self.root), "No appointments exist.")

    def test_permissions_matrix(self):
        for user in (self.patient, self.staff):
            self.client.force_login(user)
            expected = 403 if user.is_staff else 302
            for url in (self.root, self.detail, self.action("cancel"), self.action("complete")):
                self.assertEqual(self.client.get(url).status_code, expected)
        self.staff.user_permissions.add(Permission.objects.get(codename="view_appointment"))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.detail).status_code, 200)
        self.assertNotContains(self.client.get(self.detail), "Cancel appointment")
        self.assertEqual(self.client.post(self.action("cancel")).status_code, 403)
        self.staff.user_permissions.add(Permission.objects.get(codename="change_appointment"))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(self.action("cancel")).status_code, 302)
        self.staff.is_active = False; self.staff.save()
        self.assertEqual(self.client.get(self.detail).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(self.detail).status_code, 302)

    def test_completion_exact_boundary_and_terminal_conflicts(self):
        with patch("appointments.admin.timezone.now", return_value=self.slot.end-timedelta(microseconds=1)):
            self.assertEqual(self.client.post(self.action("complete")).status_code, 409)
        with patch("appointments.admin.timezone.now", return_value=self.slot.end):
            self.assertEqual(self.client.post(self.action("complete")).status_code, 302)
        for action in ("cancel", "complete"):
            self.assertEqual(self.client.post(self.action(action)).status_code, 409)
        self.obj.refresh_from_db(); self.assertEqual(self.obj.status, "Completed")

    def test_cancel_history_rebook_past(self):
        self.assertEqual(self.client.post(self.action("cancel"), {"status": "Completed", "patient": self.staff.pk}).status_code, 302)
        self.obj.refresh_from_db(); self.assertEqual((self.obj.status, self.obj.patient_id), ("Cancelled", self.patient.pk))
        for action in ("cancel", "complete"):
            self.assertEqual(self.client.post(self.action(action)).status_code, 409)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.post(f"/slots/{self.slot.pk}/book/").status_code, 302)
        self.assertEqual(Appointment.objects.filter(slot=self.slot).count(), 2)
        self.client.force_login(self.admin)
        latest = Appointment.objects.get(status="Booked")
        with patch("appointments.admin.timezone.now", return_value=self.slot.end):
            self.assertEqual(self.client.post(f"{self.root}{latest.pk}/cancel/").status_code, 302)
        self.client.force_login(self.patient)
        with patch("appointments.views.timezone.now", return_value=self.slot.end):
            self.assertEqual(self.client.post(f"/slots/{self.slot.pk}/book/").status_code, 409)

    def test_bounded_forms_methods_csrf_add_delete_ids(self):
        self.assertEqual(self.client.post(self.detail, {"status": "Completed", "patient": self.staff.pk, "slot": 999}).status_code, 302)
        self.obj.refresh_from_db(); self.assertEqual(self.obj.status, "Booked")
        for name in ("cancel", "complete"):
            self.assertEqual(self.client.get(self.action(name)).status_code, 405)
            csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.admin)
            self.assertEqual(csrf.post(self.action(name)).status_code, 403)
        for url in (self.root+"add/", f"{self.root}{self.obj.pk}/delete/"):
            for method in (self.client.get, self.client.post):
                self.assertEqual(method(url).status_code, 403)
        for url in (self.root+"999999/change/", self.root+"bad/change/", self.root+"999999/cancel/", self.root+"bad/complete/"):
            self.assertEqual(self.client.post(url).status_code, 404)


class AdminTransitionRaceTests(TransactionTestCase):
    def test_atomic_cancel_complete_and_repeat_and_patient_conflict(self):
        admin = get_user_model().objects.create_superuser(email="admin@example.com", password="Test-only-4981!")
        patient = get_user_model().objects.create_user(email="patient@example.com")
        doctor = Doctor.objects.create(name="Doctor", specialty="Care", description="Care")
        slot = Slot.objects.create(doctor=doctor, start=timezone.now()+timedelta(days=2))
        for actions in (("cancel", "complete"), ("cancel", "cancel"), ("complete", "complete"), ("cancel", "patient")):
            Appointment.objects.all().delete()
            obj = Appointment.objects.create(patient=patient, slot=slot)
            clients = [Client(), Client()]
            for index, client in enumerate(clients):
                client.force_login(patient if actions[index] == "patient" else admin)
            barrier = Barrier(2)
            def request(index):
                try:
                    barrier.wait()
                    action = actions[index]
                    url = f"/appointments/{obj.pk}/cancel/" if action == "patient" else f"/admin/appointments/appointment/{obj.pk}/{action}/"
                    return clients[index].post(url).status_code
                finally:
                    connections.close_all()
            # Completion eligibility and patient future eligibility are tested in separate races.
            now = slot.start-timedelta(hours=1) if "patient" in actions else slot.end
            with patch("appointments.admin.timezone.now", return_value=now), patch("appointments.views.timezone.now", return_value=now):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(request, (0, 1)))
            self.assertEqual(sorted(results), [302, 409])
            obj.refresh_from_db(); self.assertIn(obj.status, ("Cancelled", "Completed"))
