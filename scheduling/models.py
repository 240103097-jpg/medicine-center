from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class SlotQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Edit slots individually so their times can be validated.")

    def bulk_create(self, objs, **kwargs):
        with transaction.atomic(using=self.db):
            for obj in objs:
                obj.save(using=self.db)
        return objs

    def bulk_update(self, objs, fields, **kwargs):
        with transaction.atomic(using=self.db):
            for obj in objs:
                obj.save(using=self.db)
        return len(objs)


class Slot(models.Model):
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE, related_name="slots")
    start = models.DateTimeField(help_text="Date and time in Asia/Almaty.")
    objects = SlotQuerySet.as_manager()

    class Meta:
        ordering = ["start", "id"]

    @property
    def end(self):
        return self.start + timedelta(minutes=30) if self.start else None

    def clean(self):
        if not self.start:
            return
        if timezone.is_naive(self.start):
            raise ValidationError({"start": "Enter a timezone-aware date and time."})
        previous = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        changed = not previous or previous.start != self.start or previous.doctor_id != self.doctor_id
        if changed and self.start <= timezone.now():
            raise ValidationError({"start": "The slot must start in the future."})
        if self.doctor_id and type(self).objects.filter(doctor_id=self.doctor_id, start__lt=self.end, start__gt=self.start - timedelta(minutes=30)).exclude(pk=self.pk).exists():
            raise ValidationError({"start": "This slot overlaps another slot for this doctor."})

    def save(self, *args, **kwargs):
        using = kwargs.get("using") or self._state.db or "default"
        # SQLite IMMEDIATE transactions acquire the writer lock before validation
        # reads, including the surrounding Django admin transaction.
        with transaction.atomic(using=using):
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.doctor} — {timezone.localtime(self.start):%Y-%m-%d %H:%M} Asia/Almaty"
