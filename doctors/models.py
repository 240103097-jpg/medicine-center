from django.core.validators import MaxLengthValidator
from django.db import models


class Doctor(models.Model):
    name = models.CharField(max_length=200)
    specialty = models.CharField(max_length=200)
    description = models.TextField(validators=[MaxLengthValidator(5000)])

    class Meta:
        ordering = ["name", "id"]

    def clean_fields(self, exclude=None):
        for field in ("name", "specialty", "description"):
            if field not in (exclude or ()) and isinstance(getattr(self, field), str):
                setattr(self, field, getattr(self, field).strip())
        super().clean_fields(exclude=exclude)

    def __str__(self):
        return self.name
