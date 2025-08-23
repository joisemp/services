from django import forms
from core.models import UserProfile
from django.contrib.auth import get_user_model
from .models import WorkCategory, Spaces

User = get_user_model()

USER_TYPE_CHOICES = [
    (k, v) for k, v in UserProfile.USER_TYPE_CHOICES if k != 'general_user'
]

class AddGeneralUserForm(forms.Form):
    phone = forms.CharField(max_length=20, label='Phone Number')
    first_name = forms.CharField(max_length=255, required=False)
    last_name = forms.CharField(max_length=255, required=False)
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and User.objects.filter(phone=phone).exists():
            raise forms.ValidationError('A user with this phone number already exists.')
        return phone

class AddOtherUserForm(forms.Form):
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, label='User Type')
    skills = forms.ModelMultipleChoiceField(
        queryset=WorkCategory.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Work Categories (Skills)'
    )

    def __init__(self, *args, **kwargs):
        org = kwargs.pop('org', None)
        super().__init__(*args, **kwargs)
        if org:
            self.fields['skills'].queryset = WorkCategory.objects.filter(org=org)
        else:
            self.fields['skills'].queryset = WorkCategory.objects.all()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and User.objects.filter(phone=phone).exists():
            raise forms.ValidationError('A user with this phone number already exists.')
        return phone

class WorkCategoryForm(forms.ModelForm):
    class Meta:
        model = WorkCategory
        fields = ['name', 'description']


class SpaceForm(forms.ModelForm):
    """Form for creating and editing spaces"""
    class Meta:
        model = Spaces
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter space name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter space description (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Remove org from kwargs if passed, as it will be set automatically
        self.user_org = kwargs.pop('user_org', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user_org:
            instance.org = self.user_org
        if commit:
            instance.save()
        return instance
