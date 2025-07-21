from django import forms
from .models import Issue
from core.models import User
from service_management.models import Spaces

class IssueForm(forms.ModelForm):
    space = forms.ModelChoiceField(
        queryset=Spaces.objects.none(),
        required=False,
        empty_label="Select a space...",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Issue
        fields = ['title', 'description', 'voice', 'space']  # Include space field
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'voice': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile'):
            if user.profile.user_type == 'central_admin':
                # Central admin can select from all spaces in their organization (optional)
                self.fields['space'].queryset = Spaces.objects.filter(org=user.profile.org)
                self.fields['space'].required = False
            elif user.profile.user_type == 'space_admin':
                # Space admin has space pre-populated and locked to their active space
                if user.profile.current_active_space:
                    self.fields['space'].queryset = Spaces.objects.filter(id=user.profile.current_active_space.id)
                    self.fields['space'].initial = user.profile.current_active_space
                    self.fields['space'].widget.attrs.update({
                        'readonly': True,
                        'disabled': True,
                        'class': 'form-control bg-light'
                    })
                else:
                    # No active space, hide field
                    self.fields['space'].widget = forms.HiddenInput()
            else:
                # Other user types don't see space selection
                self.fields['space'].widget = forms.HiddenInput()
        else:
            # Anonymous users don't see space selection
            self.fields['space'].widget = forms.HiddenInput()

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
