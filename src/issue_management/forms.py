from config.mixins.form_mixin import BootstrapFormMixin
from django import forms
from .models import Issue, WorkTask

class IssueForm(BootstrapFormMixin, forms.ModelForm):
    # Add image fields for up to 3 images
    image1 = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control',
        'accept': 'image/*'
    }))
    image2 = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control',
        'accept': 'image/*'
    }))
    image3 = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control',
        'accept': 'image/*'
    }))
    
    class Meta:
        model = Issue
        fields = ['title', 'description', 'status', 'priority', 'org', 'space', 'voice']
        widgets = {
            'voice': forms.FileInput(attrs={
                'class': 'voice-file-input',
                'accept': 'audio/*',
                'style': 'display: none;'
            }),
            'space': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make space field optional
        self.fields['space'].required = False
        self.fields['space'].empty_label = "Select a space (optional)"


class WorkTaskForm(BootstrapFormMixin, forms.ModelForm):
    """Form for creating work tasks - no resolution notes field"""
    class Meta:
        model = WorkTask
        fields = ['title', 'description', 'assigned_to', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe the work task...'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract the issue from kwargs to filter users
        self.issue = kwargs.pop('issue', None)
        super().__init__(*args, **kwargs)
        
        # Make due_date optional
        self.fields['due_date'].required = False
        
        # Filter assigned_to to only show users from the same organization
        if self.issue and self.issue.org:
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(is_active=True)
        
        # Add help text
        self.fields['due_date'].help_text = "When should this task be completed?"


class WorkTaskUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Form for updating work tasks - no resolution notes field"""
    class Meta:
        model = WorkTask
        fields = ['title', 'description', 'assigned_to', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe the work task...'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract the issue from kwargs to filter users
        self.issue = kwargs.pop('issue', None)
        super().__init__(*args, **kwargs)
        
        # Make due_date optional
        self.fields['due_date'].required = False
        
        # Filter assigned_to to only show users from the same organization
        if self.issue and self.issue.org:
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(is_active=True)
        
        # Add help text
        self.fields['due_date'].help_text = "When should this task be completed?"


class WorkTaskCompleteForm(BootstrapFormMixin, forms.ModelForm):
    """Form for completing work tasks - only resolution notes field"""
    class Meta:
        model = WorkTask
        fields = ['resolution_notes']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe how this task was completed...',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make resolution_notes required for completion
        self.fields['resolution_notes'].required = True
        self.fields['resolution_notes'].help_text = "Please provide details about how the task was completed"