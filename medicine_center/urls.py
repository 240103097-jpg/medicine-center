from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from accounts.views import register, EmailLoginView, PatientLogoutView

from doctors.views import doctor_list, doctor_detail
from appointments.views import book, confirmation, my_appointments, cancel

urlpatterns = [
    path("appointments/", my_appointments, name="my_appointments"),
    path("appointments/<int:pk>/cancel/", cancel, name="cancel_appointment"),
    path("slots/<int:pk>/book/", book, name="book_slot"),
    path("appointments/<int:pk>/confirmation/", confirmation, name="booking_confirmation"),
    path("doctors/", doctor_list, name="doctor_list"),
    path("doctors/<int:pk>/", doctor_detail, name="doctor_detail"),
    path("register/", register, name="register"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", PatientLogoutView.as_view(), name="logout"),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("admin/", admin.site.urls),
]
