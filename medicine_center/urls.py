from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from accounts.views import register, EmailLoginView, PatientLogoutView

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", PatientLogoutView.as_view(), name="logout"),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("admin/", admin.site.urls),
]
