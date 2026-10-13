from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from doctors.models import Doctor
from scheduling.models import Slot
from .models import Appointment


class BookingTests(TestCase):
    def setUp(self):
        self.patient = get_user_model().objects.create_user(email="patient@example.com", password="Testing-only-843!")
        self.other = get_user_model().objects.create_user(email="other@example.com", password="Testing-only-843!")
        self.doctor = Doctor.objects.create(name="<script>Doctor</script>", specialty="Care", description="Plain")
        self.slot = Slot.objects.create(doctor=self.doctor, start=timezone.now()+timedelta(days=2))
        self.url = f"/slots/{self.slot.pk}/book/"
        self.client.force_login(self.patient)

    def test_booking_binding_confirmation_and_occupancy(self):
        response = self.client.post(self.url, {"patient": self.other.pk, "status": "Completed", "doctor": 999, "start": "2000-01-01"})
        self.assertEqual(response.status_code, 302)
        booking = Appointment.objects.get()
        self.assertEqual((booking.patient_id, booking.status, booking.slot_id), (self.patient.pk, "Booked", self.slot.pk))
        page = self.client.get(response.url)
        self.assertContains(page, "30 minutes")
        self.assertContains(page, "Asia/Almaty")
        self.assertContains(page, "&lt;script&gt;Doctor&lt;/script&gt;")
        self.assertEqual(self.client.post(self.url).status_code, 409)
        self.assertNotContains(self.client.get(f"/doctors/{self.doctor.pk}/"), "<button type=\"submit\">Book</button>")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(response.url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(response.url).status_code, 302)

    def test_auth_methods_csrf_and_unknown_ids(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.patient)
        self.assertEqual(csrf.post(self.url).status_code, 403)
        self.assertEqual(csrf.post(self.url, {"csrfmiddlewaretoken": "invalid"}).status_code, 403)
        self.client.logout()
        self.assertIn("next=", self.client.get(self.url+"?date=2030-01-01").url)
        for flag in ("is_staff", "is_superuser"):
            setattr(self.other, flag, True); self.other.save()
            self.client.force_login(self.other)
            self.assertEqual(self.client.post(self.url).status_code, 403)
            setattr(self.other, flag, False); self.other.save()
        for url in ("/slots/999999/book/", "/slots/bad/book/", "/appointments/bad/confirmation/", "/appointments/999999/confirmation/"):
            self.assertEqual(self.client.post(url).status_code, 404)

    def test_time_boundary_history_completed_and_constraints(self):
        for now in (self.slot.start, self.slot.start+timedelta(seconds=1)):
            with patch("appointments.views.timezone.now", return_value=now):
                self.assertEqual(self.client.post(self.url).status_code, 409)
        cancelled = Appointment.objects.create(patient=self.patient, slot=self.slot, status="Cancelled")
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(Appointment.objects.filter(pk=cancelled.pk, status="Cancelled").exists())
        for status in ("Booked", "Completed", "Bad"):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Appointment.objects.create(patient=self.other, slot=self.slot, status=status)
        Appointment.objects.filter(status="Booked").update(status="Completed")
        self.assertEqual(self.client.post(self.url).status_code, 409)

    def test_history_freezes_slot_and_protects_deletion(self):
        Appointment.objects.create(patient=self.patient, slot=self.slot, status="Cancelled")
        self.slot.start += timedelta(hours=1)
        with self.assertRaisesMessage(ValidationError, "appointment history"):
            self.slot.save()
        self.slot.refresh_from_db()
        other_doctor = Doctor.objects.create(name="Other", specialty="Care", description="Plain")
        self.slot.doctor = other_doctor
        with self.assertRaises(ValidationError): self.slot.save()
        with self.assertRaises(ProtectedError): self.slot.delete()
        with self.assertRaises(ProtectedError): Slot.objects.filter(pk=self.slot.pk).delete()

    def test_date_filter_order_rollover_empty_and_invalid(self):
        local = timezone.localtime(self.slot.start).replace(hour=23, minute=45, second=0, microsecond=0)
        self.slot.start = local; self.slot.save()
        second = Slot.objects.create(doctor=self.doctor, start=local+timedelta(hours=1))
        page = self.client.get(f"/doctors/{self.doctor.pk}/?date={local.date().isoformat()}")
        self.assertEqual(list(page.context["slots"]), [self.slot])
        self.assertContains(page, timezone.localtime(self.slot.end).strftime("%Y-%m-%d %H:%M"))
        self.assertEqual(list(self.client.get(f"/doctors/{self.doctor.pk}/").context["slots"]), [self.slot, second])
        self.assertContains(self.client.get(f"/doctors/{self.doctor.pk}/?date=bad"), "Enter a valid date")
        self.assertContains(self.client.get(f"/doctors/{self.doctor.pk}/?date=2000-01-01"), "No future appointment slots")

    def test_selected_date_survives_booking_confirmation(self):
        selected = timezone.localtime(self.slot.start).date().isoformat()
        response = self.client.post(self.url + "?date=" + selected)
        self.assertIn("date=" + selected, response.url)
        self.assertContains(self.client.get(response.url), "?date=" + selected)


class ConcurrentBookingTests(TransactionTestCase):
    def test_independent_patient_requests_and_same_patient_and_different_slots(self):
        doctor = Doctor.objects.create(name="Concurrent", specialty="Care", description="Plain")
        patients = [get_user_model().objects.create_user(email=f"race{i}@example.com") for i in range(2)]
        for same_patient, same_slot in ((False, True), (True, True), (False, False)):
            slots = [Slot.objects.create(doctor=doctor, start=timezone.now()+timedelta(days=10+Slot.objects.count())) for _ in range(2)]
            clients = [Client(), Client()]
            for i, client in enumerate(clients): client.force_login(patients[0 if same_patient else i])
            barrier = Barrier(2)
            def submit(i):
                connections.close_all()
                try:
                    barrier.wait()
                    return clients[i].post(f"/slots/{slots[0 if same_slot else i].pk}/book/").status_code
                finally: connections.close_all()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, range(2)))
            self.assertEqual(sorted(results), [302, 409] if same_slot else [302, 302])
            self.assertEqual(Appointment.objects.filter(slot__in=slots).count(), 1 if same_slot else 2)
