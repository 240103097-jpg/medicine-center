from django.conf import settings
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "Booked"
        CANCELLED = "Cancelled"
        COMPLETED = "Completed"

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    slot = models.ForeignKey("scheduling.Slot", on_delete=models.PROTECT, related_name="appointments")
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.BOOKED)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=["Booked", "Cancelled", "Completed"]), name="appointment_valid_status"),
            models.UniqueConstraint(fields=["slot"], condition=models.Q(status__in=["Booked", "Completed"]), name="one_reserved_appointment_per_slot"),
        ]
