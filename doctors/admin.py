from django.contrib import admin

from .forms import DoctorAdminForm
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    form = DoctorAdminForm
    list_display = ["name", "specialty"]
