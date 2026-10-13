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

class PatientManagementTests(TestCase):
    def setUp(self):
        BookingTests.setUp(self)
        self.record = Appointment.objects.create(patient=self.patient, slot=self.slot)
        self.cancel_url = f"/appointments/{self.record.pk}/cancel/"

    def test_list_isolation_order_history_empty_and_escaping(self):
        self.assertContains(self.client.get('/appointments/'), '&lt;script&gt;Doctor&lt;/script&gt;')
        for status in ('Cancelled', 'Completed'):
            Appointment.objects.create(patient=self.patient, slot=self.slot, status='Cancelled')
        Appointment.objects.filter(pk=self.record.pk).update(status='Completed')
        page = self.client.get('/appointments/')
        self.assertEqual([a.pk for a in page.context['appointments']], list(Appointment.objects.order_by('-pk').values_list('pk', flat=True)))
        self.assertContains(page, 'Completed')
        self.assertContains(page, 'Cancelled')
        self.client.force_login(self.other)
        self.assertContains(self.client.get('/appointments/'), 'no appointments yet')
        self.assertEqual(self.client.post(self.cancel_url).status_code, 404)
        self.assertEqual(self.client.get(f'/appointments/{self.record.pk}/confirmation/').status_code, 404)

    def test_cancel_preserves_history_rebooking_and_ignores_tampering(self):
        response = self.client.post(self.cancel_url, {'patient': self.other.pk, 'status': 'Completed', 'slot': 999})
        self.assertEqual(response.status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual((self.record.patient_id,self.record.slot_id,self.record.status),(self.patient.pk,self.slot.pk,'Cancelled'))
        self.assertContains(self.client.get(f'/doctors/{self.doctor.pk}/'), '>Book</button>')
        self.assertEqual(self.client.post(self.cancel_url).status_code, 409)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertEqual(Appointment.objects.exclude(status='Cancelled').count(), 1)
        self.assertEqual(len(self.client.get('/appointments/').context['appointments']), 1)

    def test_cancel_boundaries_status_auth_methods_csrf(self):
        for now in (self.slot.start, self.slot.start+timedelta(seconds=1)):
            with patch('appointments.views.timezone.now',return_value=now):
                self.assertEqual(self.client.post(self.cancel_url).status_code,409)
                self.assertNotContains(self.client.get('/appointments/'),'Cancel appointment')
        for status in ('Cancelled','Completed'):
            Appointment.objects.filter(pk=self.record.pk).update(status=status)
            self.assertEqual(self.client.post(self.cancel_url).status_code,409)
            self.record.refresh_from_db(); self.assertEqual(self.record.status,status)
        self.assertEqual(self.client.get(self.cancel_url).status_code,405)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.patient)
        for data in ({},{'csrfmiddlewaretoken':'invalid'}):
            self.assertEqual(csrf.post(self.cancel_url,data).status_code,403)
        for url in ('/appointments/bad/cancel/','/appointments/999999/cancel/'):
            self.assertEqual(self.client.post(url).status_code,404)
        for flag in ('is_staff','is_superuser'):
            setattr(self.other,flag,True);self.other.save();self.client.force_login(self.other)
            self.assertEqual(self.client.get('/appointments/').status_code,403)
            self.assertEqual(self.client.post(self.cancel_url).status_code,403)
            setattr(self.other,flag,False);self.other.save()
        self.client.logout();self.assertIn('next=',self.client.get('/appointments/').url)


class CancellationConcurrencyTests(TransactionTestCase):
    def test_two_independent_cancellations_and_rebooking(self):
        patient=get_user_model().objects.create_user(email='race@example.com')
        doctor=Doctor.objects.create(name='Race',specialty='Care',description='Plain')
        slot=Slot.objects.create(doctor=doctor,start=timezone.now()+timedelta(days=2))
        record=Appointment.objects.create(patient=patient,slot=slot)
        clients=[Client(),Client()]
        for client in clients: client.force_login(patient)
        barrier=Barrier(2)
        def cancel_request(client):
            connections.close_all()
            try:
                barrier.wait();return client.post(f'/appointments/{record.pk}/cancel/').status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(cancel_request,clients)),[302,409])
        record.refresh_from_db();self.assertEqual(record.status,'Cancelled')
        self.assertEqual(clients[0].post(f'/slots/{slot.pk}/book/').status_code,302)
        self.assertEqual(Appointment.objects.filter(slot=slot).count(),2)
        self.assertEqual(Appointment.objects.filter(slot=slot).exclude(status='Cancelled').count(),1)
