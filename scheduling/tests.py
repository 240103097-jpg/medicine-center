from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, datetime, timezone as dtz
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TestCase, TransactionTestCase, Client
from django.utils import timezone
from doctors.models import Doctor
from .models import Slot


class SlotTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name="Doctor", specialty="General", description="Care")
        self.start = timezone.now() + timedelta(days=2)

    def slot(self, **kwargs):
        return Slot.objects.create(doctor=self.doctor, start=kwargs.pop("start", self.start), **kwargs)

    def test_required_aware_future_boundaries(self):
        for obj in [Slot(), Slot(doctor=self.doctor, start=datetime(2030, 1, 1)), Slot(doctor_id=9999, start=self.start)]:
            with self.assertRaises(ValidationError): obj.save()
        now = timezone.now()
        with patch("scheduling.models.timezone.now", return_value=now):
            for start in [now, now - timedelta(microseconds=1)]:
                with self.assertRaises(ValidationError): self.slot(start=start)
            slot = self.slot(start=now + timedelta(microseconds=1))
            self.assertEqual(slot.end - slot.start, timedelta(minutes=30))
        with patch("scheduling.models.timezone.now", return_value=self.start + timedelta(days=3)):
            slot.save()
            slot.start += timedelta(minutes=1)
            with self.assertRaises(ValidationError): slot.save()

    def test_overlap_adjacency_different_doctor_and_update(self):
        original = self.slot()
        for offset in [-29, 0, 29]:
            with self.assertRaisesMessage(ValidationError, "overlaps"): self.slot(start=self.start + timedelta(minutes=offset))
        adjacent = self.slot(start=original.end)
        adjacent.start -= timedelta(minutes=1)
        with self.assertRaises(ValidationError): adjacent.save()
        other = Doctor.objects.create(name="Other", specialty="General", description="Care")
        Slot.objects.create(doctor=other, start=self.start)
        self.assertEqual(Slot.objects.count(), 3)
        with self.assertRaises(ValidationError): Slot.objects.update(start=self.start)
        with self.assertRaises(ValidationError): Slot.objects.bulk_create([Slot(doctor=self.doctor, start=self.start)])

    def test_public_boundary_order_empty_timezone_rollover(self):
        self.assertContains(self.client.get(f"/doctors/{self.doctor.pk}/"), "No future appointment")
        now = datetime(2030, 1, 1, tzinfo=dtz.utc)
        with patch("scheduling.models.timezone.now", return_value=now - timedelta(days=1)):
            self.slot(start=now - timedelta(minutes=30))
            self.slot(start=now)
            late = self.slot(start=now + timedelta(hours=19, minutes=45))
            early = self.slot(start=now + timedelta(hours=1))
        with patch("doctors.views.timezone.now", return_value=now):
            response = self.client.get(f"/doctors/{self.doctor.pk}/")
            self.assertEqual(list(response.context["slots"]), [early, late])
            self.assertContains(response, "2030-01-02 00:45")
            self.assertContains(response, "2030-01-02 01:15")
            self.assertContains(response, "Asia/Almaty")

    def test_admin_permissions_csrf_and_local_input(self):
        url = "/admin/scheduling/slot/add/"
        User = get_user_model()
        user = User.objects.create_user(email="staff@example.test", password="test-local", is_staff=True)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename="view_slot"))
        self.assertEqual(self.client.get("/admin/scheduling/slot/").status_code, 200)
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename="add_slot"), Permission.objects.get(codename="change_slot"))
        secure = Client(enforce_csrf_checks=True); secure.force_login(user)
        self.assertEqual(secure.post(url, {}).status_code, 403)
        self.assertEqual(self.client.post(url, {"doctor": self.doctor.pk, "start_0": "2030-01-02", "start_1": "09:15", "_save": "Save"}).status_code, 302)
        slot = Slot.objects.get()
        self.assertEqual(slot.start.hour, 4)
        conflict = self.client.post(url, {"doctor": self.doctor.pk, "start_0": "2030-01-02", "start_1": "09:20", "_save": "Save"})
        self.assertContains(conflict, "overlaps")
        patient = User.objects.create_user(email="patient@example.test", password="test-local")
        self.client.force_login(patient)
        self.assertEqual(self.client.get(url).status_code, 302)


class ConcurrentSlotTests(TransactionTestCase):
    def test_concurrent_creates_and_updates(self):
        doctor = Doctor.objects.create(name="Doctor", specialty="General", description="Care")
        start = timezone.now() + timedelta(days=2)
        def create(_):
            connections.close_all()
            try:
                Slot.objects.create(doctor_id=doctor.pk, start=start)
                return "saved"
            except ValidationError:
                return "conflict"
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(create, range(2))), ["saved", "conflict"])
        first = Slot.objects.get()
        second = Slot.objects.create(doctor=doctor, start=start + timedelta(hours=2))
        def update(pk):
            connections.close_all()
            try:
                obj = Slot.objects.get(pk=pk); obj.start = start + timedelta(hours=4); obj.save()
                return "saved"
            except ValidationError: return "conflict"
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(update, [first.pk, second.pk])), ["saved", "conflict"])
