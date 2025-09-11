from config.mixins.form_mixin import BootstrapFormMixin
from django import forms
from .models import Issue

class IssueForm(BootstrapFormMixin, forms.ModelForm):
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