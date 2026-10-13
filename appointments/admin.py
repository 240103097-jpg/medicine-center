from datetime import timedelta

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["patient_name", "patient_email", "doctor", "appointment_time", "status"]
    readonly_fields = ["patient_name", "patient_email", "doctor", "appointment_time", "status"]
    fields = readonly_fields
    ordering = ["-slot__start", "-id"]
    actions = None
    change_form_template = "admin/appointments/appointment/change_form.html"
    change_list_template = "admin/appointments/appointment/change_list.html"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("patient", "slot__doctor")

    @admin.display(description="Patient name")
    def patient_name(self, obj):
        return obj.patient.get_full_name()

    @admin.display(description="Patient email")
    def patient_email(self, obj):
        return obj.patient.email

    @admin.display(description="Doctor")
    def doctor(self, obj):
        return obj.slot.doctor.name

    @admin.display(description="Appointment (Asia/Almaty, 30 minutes)")
    def appointment_time(self, obj):
        return f"{timezone.localtime(obj.slot.start):%Y-%m-%d %H:%M} – {timezone.localtime(obj.slot.end):%H:%M} Asia/Almaty"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Every field is immutable here; transitions have dedicated endpoints.
        pass

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if not object_id.isdecimal():
            raise Http404
        obj = get_object_or_404(Appointment, pk=object_id)
        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied
        return super().change_view(request, object_id, form_url, extra_context)

    def get_urls(self):
        return [
            path("<str:pk>/cancel/", self.admin_site.admin_view(self.cancel), name="appointments_appointment_cancel"),
            path("<str:pk>/complete/", self.admin_site.admin_view(self.complete), name="appointments_appointment_complete"),
        ] + super().get_urls()

    def transition(self, request, pk, target):
        if not self.has_change_permission(request):
            raise PermissionDenied
        if not str(pk).isdecimal():
            raise Http404
        return self.transition_post(request, pk, target)

    @method_decorator(require_POST)
    def transition_post(self, request, pk, target):
        with transaction.atomic():
            obj = get_object_or_404(Appointment, pk=pk)
            eligible = Appointment.objects.filter(pk=pk, status=Appointment.Status.BOOKED)
            if target == Appointment.Status.COMPLETED:
                eligible = eligible.filter(slot__start__lte=timezone.now() - timedelta(minutes=30))
            if not eligible.update(status=target):
                return render(request, "admin/appointments/appointment/conflict.html", {
                    **self.admin_site.each_context(request), "title": "Appointment cannot be changed", "appointment": obj,
                }, status=409)
        self.message_user(request, f"Appointment {pk} has been {target.lower()}.", messages.SUCCESS)
        return redirect("admin:appointments_appointment_change", pk)

    def cancel(self, request, pk):
        return self.transition(request, pk, Appointment.Status.CANCELLED)

    def complete(self, request, pk):
        return self.transition(request, pk, Appointment.Status.COMPLETED)
