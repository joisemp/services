from config.mixins.form_mixin import BootstrapFormMixin
from django import forms
from .models import Issue, WorkTask, IssueComment, SiteVisit

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
        fields = ['title', 'description', 'priority', 'space', 'voice']
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
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        # Make space field optional
        self.fields['space'].required = False
        self.fields['space'].empty_label = "Select a space (optional)"

    def clean(self):
        cleaned_data = super().clean()
        # Set organization on instance before validation
        if hasattr(self, 'instance') and self.current_user and self.current_user.organization:
            self.instance.org = self.current_user.organization
        return cleaned_data


class SpaceAdminIssueForm(BootstrapFormMixin, forms.ModelForm):
    """
    Form for space admins to create issues.
    Excludes the space field since it's auto-assigned from active_space.
    """
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
        fields = ['title', 'description', 'priority', 'voice']
        widgets = {
            'voice': forms.FileInput(attrs={
                'class': 'voice-file-input',
                'accept': 'audio/*',
                'style': 'display: none;'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        self.active_space = kwargs.pop('active_space', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # Set organization and space on instance before validation
        if hasattr(self, 'instance'):
            if self.current_user and self.current_user.organization:
                self.instance.org = self.current_user.organization
            if self.active_space:
                self.instance.space = self.active_space
        return cleaned_data


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
        
        # Filter assigned_to to only show supervisors or maintainers from the same organization
        if self.issue and self.issue.org:
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(
                is_active=True,
                user_type__in=['supervisor', 'maintainer']
            ).order_by('first_name', 'last_name')
            self.fields['assigned_to'].empty_label = "Select a supervisor or maintainer"
        
        # Update label and help text
        self.fields['assigned_to'].label = "Assign to"
        self.fields['assigned_to'].help_text = "Tasks can only be assigned to supervisors or maintainers"
        self.fields['due_date'].help_text = "When should this task be completed?"
    
    def clean_assigned_to(self):
        """Validate that the assigned user is a supervisor or maintainer from the same organization"""
        assigned_to = self.cleaned_data.get('assigned_to')
        
        if assigned_to and self.issue:
            # Check if user is from the same organization
            if assigned_to.organization != self.issue.org:
                raise forms.ValidationError(
                    'Selected user must be from the same organization as the issue.'
                )
            
            # Check if user is a supervisor or maintainer
            if assigned_to.user_type not in ['supervisor', 'maintainer']:
                raise forms.ValidationError(
                    'Tasks can only be assigned to supervisors or maintainers.'
                )
        
        return assigned_to


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
        
        # Filter assigned_to to only show supervisors or maintainers from the same organization
        if self.issue and self.issue.org:
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(
                is_active=True,
                user_type__in=['supervisor', 'maintainer']
            ).order_by('first_name', 'last_name')
            self.fields['assigned_to'].empty_label = "Select a supervisor or maintainer"
        
        # Update label and help text
        self.fields['assigned_to'].label = "Assign to"
        self.fields['assigned_to'].help_text = "Tasks can only be assigned to supervisors or maintainers"
        self.fields['due_date'].help_text = "When should this task be completed?"
    
    def clean_assigned_to(self):
        """Validate that the assigned user is a supervisor or maintainer from the same organization"""
        assigned_to = self.cleaned_data.get('assigned_to')
        
        if assigned_to and self.issue:
            # Check if user is from the same organization
            if assigned_to.organization != self.issue.org:
                raise forms.ValidationError(
                    'Selected user must be from the same organization as the issue.'
                )
            
            # Check if user is a supervisor or maintainer
            if assigned_to.user_type not in ['supervisor', 'maintainer']:
                raise forms.ValidationError(
                    'Tasks can only be assigned to supervisors or maintainers.'
                )
        
        return assigned_to


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads"""
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        """Return a list of uploaded files"""
        upload = files.getlist(name)
        if not upload:
            return None
        return upload


class MultipleFileField(forms.FileField):
    """Custom field for handling multiple file uploads"""
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_python(self, data):
        """Handle multiple file data"""
        if data in self.empty_values:
            return None
        elif isinstance(data, list):
            return [super(MultipleFileField, self).to_python(item) for item in data]
        else:
            return super().to_python(data)

    def validate(self, value):
        """Validate multiple files"""
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'], code='required')
        if isinstance(value, list):
            for file_item in value:
                super(MultipleFileField, self).validate(file_item)
        else:
            super().validate(value)


class WorkTaskCompleteForm(BootstrapFormMixin, forms.ModelForm):
    """Form for completing work tasks - resolution notes and images"""
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


class IssueResolveForm(BootstrapFormMixin, forms.ModelForm):
    """Form for resolving issues with resolution notes and images"""
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
        fields = ['resolution_notes']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe how this issue was resolved...',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make resolution_notes required for resolution
        self.fields['resolution_notes'].required = True
        self.fields['resolution_notes'].help_text = "Please provide details about how the issue was resolved"


class IssueCommentForm(BootstrapFormMixin, forms.ModelForm):
    """Form for adding comments to issues"""
    class Meta:
        model = IssueComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add your comment...',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make comment required
        self.fields['comment'].required = True
        self.fields['comment'].label = ""  # Remove label for cleaner UI


class AdditionalImageUploadForm(BootstrapFormMixin, forms.Form):
    """Form for uploading additional images to existing issues"""
    images = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True
        }),
        help_text='Select one or more images to upload (JPEG, PNG, GIF formats supported)',
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['images'].label = "Additional Images"
        
    def clean_images(self):
        """Validate uploaded images"""
        images = self.cleaned_data.get('images')
        
        if not images:
            raise forms.ValidationError("Please select at least one image to upload.")
        
        # Ensure images is a list
        if not isinstance(images, list):
            images = [images]
        
        # Limit number of images that can be uploaded at once
        max_images = 5
        if len(images) > max_images:
            raise forms.ValidationError(f"You can upload a maximum of {max_images} images at once.")
        
        # Validate each image
        max_size = 10 * 1024 * 1024  # 10MB per image
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        
        for image in images:
            # Check file size
            if hasattr(image, 'size') and image.size > max_size:
                raise forms.ValidationError(f"Image '{image.name}' is too large. Maximum size is 10MB.")
            
            # Check content type
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise forms.ValidationError(f"Image '{image.name}' has an unsupported format. Please use JPEG, PNG, GIF, or WebP.")
        
        return images


class VoiceUploadForm(BootstrapFormMixin, forms.Form):
    """Form for adding voice recording to existing issues"""
    voice = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'voice-file-input',
            'accept': 'audio/*',
            'style': 'display: none;'
        }),
        help_text='Record or upload a voice message for this issue',
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['voice'].label = "Voice Recording"
        
    def clean_voice(self):
        """Validate uploaded voice file"""
        voice = self.cleaned_data.get('voice')
        
        if not voice:
            raise forms.ValidationError("Please record or select a voice file.")
        
        # Check file size (max 50MB for audio files)
        max_size = 50 * 1024 * 1024  # 50MB
        if hasattr(voice, 'size') and voice.size > max_size:
            raise forms.ValidationError(f"Voice file is too large. Maximum size is 50MB.")
        
        # Check content type
        allowed_types = [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 
            'audio/m4a', 'audio/mp4', 'audio/aac', 'audio/ogg', 'audio/webm'
        ]
        if hasattr(voice, 'content_type') and voice.content_type not in allowed_types:
            raise forms.ValidationError(f"Audio format not supported. Please use MP3, WAV, M4A, AAC, or WebM.")
        
        return voice
    

class IssueUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Form for updating existing issues - excludes image and voice fields"""
    class Meta:
        model = Issue
        fields = ['title', 'description', 'status', 'priority']


class IssueAssignmentForm(BootstrapFormMixin, forms.ModelForm):
    """Form for assigning issues to supervisors with review requirement option"""
    
    class Meta:
        model = Issue
        fields = ['assigned_to', 'requires_review']
        widgets = {
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            }),
            'requires_review': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract the issue from kwargs to filter supervisors from same organization
        self.issue = kwargs.pop('issue', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to to only show supervisors from the same organization
        if self.issue and self.issue.org:
            from core.models import User
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(
                user_type='supervisor',
                is_active=True
            )
            self.fields['assigned_to'].empty_label = "Select a supervisor to assign"
        
        # Add labels and help text
        self.fields['assigned_to'].label = "Assign to Supervisor"
        self.fields['assigned_to'].help_text = "Select a supervisor to handle this issue"
        self.fields['assigned_to'].required = True
        self.fields['requires_review'].label = "Requires Review"
        self.fields['requires_review'].help_text = "Check this if the issue requires review before being marked as resolved"
    
    def clean_assigned_to(self):
        """Validate that assigned user is a supervisor"""
        assigned_to = self.cleaned_data.get('assigned_to')
        
        if assigned_to and assigned_to.user_type != 'supervisor':
            raise forms.ValidationError("Issues can only be assigned to supervisors.")
        
        return assigned_to


class IssueReviewerSelectionForm(BootstrapFormMixin, forms.Form):
    """Form for selecting reviewers for an issue (Step 2 after assignment)"""
    
    reviewers = forms.ModelMultipleChoiceField(
        queryset=None,
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Select Reviewers",
        help_text="Choose one or more reviewers for this issue"
    )
    
    def __init__(self, *args, **kwargs):
        # Extract the issue from kwargs to filter reviewers from same organization
        self.issue = kwargs.pop('issue', None)
        super().__init__(*args, **kwargs)
        
        # Filter reviewers to only show reviewers from the same organization
        if self.issue and self.issue.org:
            from core.models import User
            self.fields['reviewers'].queryset = self.issue.org.users.filter(
                user_type='reviewer',
                is_active=True
            ).order_by('first_name', 'last_name')
            
            # Set initial values if issue already has reviewers
            if self.issue.reviewers.exists():
                self.initial['reviewers'] = self.issue.reviewers.all()
    
    def clean_reviewers(self):
        """Validate that at least one reviewer is selected"""
        reviewers = self.cleaned_data.get('reviewers')
        
        if not reviewers:
            raise forms.ValidationError("Please select at least one reviewer.")
        
        return reviewers


class SiteVisitForm(BootstrapFormMixin, forms.ModelForm):
    """Form for creating site visits - simplified with only essential fields"""
    
    class Meta:
        model = SiteVisit
        fields = ['title', 'description', 'location', 'assigned_to', 'scheduled_date']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe what needs to be done during this visit...'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Enter the address or location for the site visit...',
                'class': 'form-control'
            }),
            'scheduled_date': forms.DateTimeInput(attrs={
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
        
        # Filter assigned_to to only show supervisors or maintainers from the same organization
        if self.issue and self.issue.org:
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(
                is_active=True,
                user_type__in=['supervisor', 'maintainer']
            ).order_by('first_name', 'last_name')
            self.fields['assigned_to'].empty_label = "Select a supervisor or maintainer"
        
        # Update labels and help text
        self.fields['title'].help_text = "Brief description of the site visit purpose"
        self.fields['location'].help_text = "Physical address or location where the visit will take place"
        self.fields['assigned_to'].label = "Assign to"
        self.fields['assigned_to'].help_text = "Site visits can be assigned to supervisors or maintainers"
        self.fields['scheduled_date'].help_text = "When should this site visit occur?"
    
    def clean_assigned_to(self):
        """Validate that the assigned user is a supervisor or maintainer from the same organization"""
        assigned_to = self.cleaned_data.get('assigned_to')
        
        if assigned_to and self.issue:
            # Check if user is from the same organization
            if assigned_to.organization != self.issue.org:
                raise forms.ValidationError(
                    'Selected user must be from the same organization as the issue.'
                )
            
            # Check if user is a supervisor or maintainer
            if assigned_to.user_type not in ['supervisor', 'maintainer']:
                raise forms.ValidationError(
                    'Site visits can only be assigned to supervisors or maintainers.'
                )
        
        return assigned_to


class SiteVisitUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Form for updating site visits (basic info and scheduling)"""
    # Add image fields for adding more images during update
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
        model = SiteVisit
        fields = ['title', 'description', 'assigned_to', 'scheduled_date', 'estimated_duration', 'status']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe what needs to be done during this visit...'
            }),
            'scheduled_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'estimated_duration': forms.TextInput(attrs={
                'placeholder': 'e.g., 2:00:00 for 2 hours',
                'class': 'form-control'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extract the issue from kwargs to filter users
        self.issue = kwargs.pop('issue', None)
        super().__init__(*args, **kwargs)
        
        # Make estimated_duration optional
        self.fields['estimated_duration'].required = False
        
        # Filter assigned_to to only show supervisors or maintainers from the same organization
        if self.issue and self.issue.org:
            self.fields['assigned_to'].queryset = self.issue.org.users.filter(
                is_active=True,
                user_type__in=['supervisor', 'maintainer']
            ).order_by('first_name', 'last_name')
            self.fields['assigned_to'].empty_label = "Select a supervisor or maintainer"
        
        # Update labels and help text
        self.fields['title'].help_text = "Brief description of the site visit purpose"
        self.fields['assigned_to'].label = "Assign to"
        self.fields['assigned_to'].help_text = "Site visits can be assigned to supervisors or maintainers"
        self.fields['scheduled_date'].help_text = "When should this site visit occur?"
        self.fields['estimated_duration'].help_text = "Expected duration in HH:MM:SS format (e.g., 2:00:00)"
    
    def clean_assigned_to(self):
        """Validate that the assigned user is a supervisor or maintainer from the same organization"""
        assigned_to = self.cleaned_data.get('assigned_to')
        
        if assigned_to and self.issue:
            # Check if user is from the same organization
            if assigned_to.organization != self.issue.org:
                raise forms.ValidationError(
                    'Selected user must be from the same organization as the issue.'
                )
            
            # Check if user is a supervisor or maintainer
            if assigned_to.user_type not in ['supervisor', 'maintainer']:
                raise forms.ValidationError(
                    'Site visits can only be assigned to supervisors or maintainers.'
                )
        
        return assigned_to


class SiteVisitCompleteForm(BootstrapFormMixin, forms.ModelForm):
    """Form for completing site visits with findings, actions, and recommendations"""
    # Add image fields for completion images
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
        model = SiteVisit
        fields = ['findings', 'actions_taken', 'recommendations']
        widgets = {
            'findings': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your findings and observations...',
                'class': 'form-control'
            }),
            'actions_taken': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe actions taken during the visit...',
                'class': 'form-control'
            }),
            'recommendations': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Provide recommendations for follow-up...',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make findings and actions_taken required for completion
        self.fields['findings'].required = True
        self.fields['actions_taken'].required = True
        self.fields['recommendations'].required = False
        
        # Update help text
        self.fields['findings'].help_text = "Required: What did you observe during the site visit?"
        self.fields['actions_taken'].help_text = "Required: What actions did you take?"
        self.fields['recommendations'].help_text = "Optional: Any recommendations for future actions?"