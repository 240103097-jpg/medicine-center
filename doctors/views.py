from django.shortcuts import get_object_or_404, render

from .models import Doctor


def doctor_list(request):
    return render(request, "doctors/list.html", {"doctors": Doctor.objects.all()})


def doctor_detail(request, pk):
    return render(request, "doctors/detail.html", {"doctor": get_object_or_404(Doctor, pk=pk)})
