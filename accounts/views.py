from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .forms import EmailAuthenticationForm, RegistrationForm


@require_http_methods(['GET', 'POST'])
def register(request):
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        if form.save() is not None:
            messages.success(request, 'Account created. Please sign in.')
            return redirect('login')
    return render(request, 'accounts/register.html', {'form': form})


class EmailLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    next_page = '/'

    def get_redirect_url(self):
        target = self.request.POST.get('next', self.request.GET.get('next', ''))
        valid = target.startswith('/') or target.startswith(('http://', 'https://'))
        if valid and url_has_allowed_host_and_scheme(
            target, allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return target
        return ''


class PatientLogoutView(LogoutView):
    next_page = '/'

    def get_success_url(self):
        return '/'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, 'You have signed out.')
        return response
