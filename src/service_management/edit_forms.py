from django import forms
from core.models import UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()

class EditUserForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['phone'].initial = self.instance.user.phone
            # Only show email field if not a general user
            if self.instance.user_type == 'general_user':
                self.fields.pop('email', None)
            else:
                self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.phone = self.cleaned_data.get('phone', user.phone)
        if 'email' in self.cleaned_data:
            user.email = self.cleaned_data.get('email', user.email)
        if commit:
            user.save()
            profile.save()
        return profile
