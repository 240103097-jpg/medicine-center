from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        # The unique database field arbitrates conflicting normalized submissions.
        try:
            with transaction.atomic():
                return super().save(commit=commit)
        except IntegrityError:
            self.add_error('email', 'An account with this email already exists.')
            return None


class EmailAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Please enter a correct email and password.',
        'inactive': 'Please enter a correct email and password.',
    }
    username = forms.EmailField(label='Email', max_length=254)

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()
