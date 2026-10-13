from urllib.parse import urlencode

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from scheduling.models import Slot
from .models import Appointment


def login_redirect(request, target):
    return redirect(reverse("login") + "?" + urlencode({"next": target}))


def book(request, pk):
    slot = get_object_or_404(Slot, pk=pk)
    if not request.user.is_authenticated or not request.user.is_active:
        target = reverse("doctor_detail", args=[slot.doctor_id])
        selected = request.GET.get("date", "")
        if selected:
            target += "?" + urlencode({"date": selected})
        return login_redirect(request, target)
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponseForbidden("Only patient accounts can book appointments.")
    return book_post(request, pk)


@require_POST
def book_post(request, pk):
    try:
        with transaction.atomic():
            slot = get_object_or_404(Slot, pk=pk)
            if slot.start <= timezone.now() or slot.appointments.exclude(status="Cancelled").exists():
                return render(request, "appointments/unavailable.html", {"slot": slot}, status=409)
            appointment = Appointment.objects.create(patient=request.user, slot=slot)
    except IntegrityError:
        return render(request, "appointments/unavailable.html", {"slot": slot}, status=409)
    messages.success(request, "Your appointment has been booked.")
    target = reverse("booking_confirmation", args=[appointment.pk])
    if request.GET.get("date"):
        target += "?" + urlencode({"date": request.GET["date"]})
    return redirect(target)


def confirmation(request, pk):
    if not request.user.is_authenticated:
        return login_redirect(request, request.path)
    appointment = get_object_or_404(Appointment.objects.select_related("slot__doctor"), pk=pk, patient=request.user)
    return render(request, "appointments/confirmation.html", {"appointment": appointment, "selected_date": request.GET.get("date", "")})


def patient_access(request):
    if not request.user.is_authenticated or not request.user.is_active:
        return login_redirect(request, reverse("my_appointments"))
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponseForbidden("Only patient accounts can manage their own appointments.")


def my_appointments(request):
    denied = patient_access(request)
    if denied is not None:
        return denied
    records = Appointment.objects.filter(patient=request.user).select_related("slot__doctor").order_by("-slot__start", "-pk")
    return render(request, "appointments/history.html", {"appointments": records, "now": timezone.now()})


def cancel(request, pk):
    denied = patient_access(request)
    if denied is not None:
        return denied
    return cancel_post(request, pk)


@require_POST
def cancel_post(request, pk):
    with transaction.atomic():
        appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
        changed = Appointment.objects.filter(pk=appointment.pk, patient=request.user, status="Booked", slot__start__gt=timezone.now()).update(status="Cancelled")
        if not changed:
            return render(request, "appointments/cancel_conflict.html", status=409)
    messages.success(request, "Your appointment has been cancelled. The slot is available again.")
    return redirect("my_appointments")
