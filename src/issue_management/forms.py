from config.mixins.form_mixin import BootstrapFormMixin
from django import forms
from .models import Issue, WorkTask, IssueComment

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