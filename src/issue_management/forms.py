from config.mixins.form_mixin import BootstrapFormMixin
from django import forms
from .models import Issue

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
            })
        }