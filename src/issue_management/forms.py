from django import forms
from .models import Issue
from core.models import User

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['title', 'description', 'voice']  # Remove 'image' from form fields

class IssueAssignmentForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['maintainer']

    def __init__(self, *args, **kwargs):
        org = None
        if 'instance' in kwargs and kwargs['instance']:
            org = kwargs['instance'].org
        super().__init__(*args, **kwargs)
        if org:
            self.fields['maintainer'].queryset = User.objects.filter(profile__user_type='maintainer', profile__org=org)
        else:
            self.fields['maintainer'].queryset = User.objects.none()
