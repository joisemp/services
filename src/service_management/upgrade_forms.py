from django import forms
from core.models import UserProfile

class UserTypeSelectForm(forms.Form):
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPE_CHOICES,
        label='Select User Type',
    )

class UserEmailUpdateForm(forms.Form):
    email = forms.EmailField(label='User Email', required=True)
