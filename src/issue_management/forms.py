from django import forms
from .models import Issue, IssueCategory, IssueComment
from core.models import User
from service_management.models import Spaces

class IssueForm(forms.ModelForm):
    space = forms.ModelChoiceField(
        queryset=Spaces.objects.none(),
        required=False,
        empty_label="Select a space...",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=IssueCategory.objects.none(),
        required=False,
        empty_label="Select a category...",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Issue
        fields = ['title', 'description', 'voice', 'space', 'category', 'priority', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'voice': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile'):
            # Set up category choices
            self.fields['category'].queryset = IssueCategory.objects.filter(
                org=user.profile.org, 
                is_active=True
            )
            
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
            # Anonymous users don't see space/category selection
            self.fields['space'].widget = forms.HiddenInput()
            self.fields['category'].widget = forms.HiddenInput()

class IssueUpdateForm(forms.ModelForm):
    """Form for updating issue status and details by maintainers/admins"""
    class Meta:
        model = Issue
        fields = ['status', 'priority', 'category', 'due_date', 'resolution_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add resolution details...'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile') and self.instance:
            self.fields['category'].queryset = IssueCategory.objects.filter(
                org=self.instance.org, 
                is_active=True
            )
            
            # Limit status choices based on user type and current status
            if user.profile.user_type == 'maintainer':
                current_status = self.instance.status
                if current_status == 'open':
                    # Maintainers can only set to 'in_progress' from 'open'
                    status_choices = [('open', 'Open'), ('in_progress', 'In Progress')]
                elif current_status == 'in_progress':
                    # Maintainers can resolve or escalate from 'in_progress'
                    status_choices = [('in_progress', 'In Progress'), ('resolved', 'Resolved'), ('escalated', 'Escalated')]
                else:
                    # Once resolved or escalated, maintainers cannot change status
                    status_choices = [(current_status, dict(Issue.STATUS_CHOICES)[current_status])]
                
                self.fields['status'].choices = status_choices
            
            # Central admins have full control over escalated issues
            elif user.profile.user_type == 'central_admin':
                # Central admins can manage all statuses
                pass

class IssueEscalationForm(forms.ModelForm):
    """Form for escalating issues by maintainers"""
    class Meta:
        model = Issue
        fields = ['escalation_reason']
        widgets = {
            'escalation_reason': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Please explain why this issue needs to be escalated...',
                'required': True
            }),
        }
        labels = {
            'escalation_reason': 'Escalation Reason'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['escalation_reason'].required = True

class EscalatedIssueReassignmentForm(forms.ModelForm):
    """Form for central admins to reassign escalated issues to maintainers"""
    reassignment_message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Add a message for the assigned maintainer about handling this escalated issue...'
        }),
        label='Message to Maintainer',
        help_text='Provide context and instructions for the maintainer',
        required=True
    )
    
    class Meta:
        model = Issue
        fields = ['maintainer']
        widgets = {
            'maintainer': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'maintainer': 'Assign to Maintainer'
        }

    def __init__(self, *args, **kwargs):
        org = kwargs.pop('org', None)
        super().__init__(*args, **kwargs)
        
        if org:
            self.fields['maintainer'].queryset = User.objects.filter(
                profile__user_type='maintainer', 
                profile__org=org
            )
            self.fields['maintainer'].empty_label = "Select a maintainer..."
        else:
            self.fields['maintainer'].queryset = User.objects.none()
        
        self.fields['maintainer'].required = True

class IssueCommentForm(forms.ModelForm):
    """Form for adding comments to issues"""
    class Meta:
        model = IssueComment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Add a comment...'
            }),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show internal comment option to maintainers and admins
        if not (user and hasattr(user, 'profile') and 
                user.profile.user_type in ['maintainer', 'central_admin']):
            self.fields['is_internal'].widget = forms.HiddenInput()
            self.fields['is_internal'].initial = False

class IssueCategoryForm(forms.ModelForm):
    """Form for creating and editing issue categories"""
    class Meta:
        model = IssueCategory
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }

class IssueAssignmentForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['maintainer']
        widgets = {
            'maintainer': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        org = None
        if 'instance' in kwargs and kwargs['instance']:
            org = kwargs['instance'].org
        super().__init__(*args, **kwargs)
        if org:
            self.fields['maintainer'].queryset = User.objects.filter(
                profile__user_type='maintainer', 
                profile__org=org
            )
            self.fields['maintainer'].empty_label = "Select a maintainer..."
        else:
            self.fields['maintainer'].queryset = User.objects.none()
