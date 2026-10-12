from django import forms

from .models import Doctor


class DoctorAdminForm(forms.ModelForm):
    # Trim before length validation, including the text area's 5,000 limit.
    name = forms.CharField(max_length=200, strip=True)
    specialty = forms.CharField(max_length=200, strip=True)
    description = forms.CharField(max_length=5000, strip=True, widget=forms.Textarea)

    class Meta:
        model = Doctor
        fields = ["name", "specialty", "description"]
