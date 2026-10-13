from django.utils import timezone
from django.shortcuts import get_object_or_404, render

from .models import Doctor
from datetime import date
from django.db.models import Exists, OuterRef
from appointments.models import Appointment


def doctor_list(request):
    return render(request, "doctors/list.html", {"doctors": Doctor.objects.all()})


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    slots = doctor.slots.filter(start__gt=timezone.now()).annotate(reserved=Exists(Appointment.objects.filter(slot_id=OuterRef("pk")).exclude(status="Cancelled"))).filter(reserved=False)
    selected = request.GET.get("date", "")
    error = ""
    if selected:
        try:
            parsed = date.fromisoformat(selected)
            if parsed.isoformat() != selected:
                raise ValueError
            slots = slots.filter(start__date=parsed)
        except ValueError:
            error = "Enter a valid date in YYYY-MM-DD format."
            slots = slots.none()
    return render(request, "doctors/detail.html", {"doctor": doctor, "slots": slots, "selected_date": selected, "date_error": error})
