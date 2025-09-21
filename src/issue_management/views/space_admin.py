from django.views.generic import ListView, CreateView, DetailView, View
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from ..models import Issue, IssueImage
from ..forms import IssueForm, AdditionalImageUploadForm, VoiceUploadForm
from django.urls import reverse_lazy
from django.http import JsonResponse

class IssueListView(ListView):
    template_name = "space_admin/issue_management/issue_list.html"
    context_object_name = "issues"
    model = Issue
    
    def get_queryset(self):
        queryset = Issue.objects.prefetch_related('images').select_related('org', 'space', 'reporter').all()
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in ['open', 'assigned', 'in_progress', 'critical']:
            if status_filter == 'critical':
                queryset = queryset.filter(priority='critical')
            else:
                queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    

class IssueCreateView(CreateView):
    template_name = "space_admin/issue_management/issue_create.html"
    form_class = IssueForm
    success_url = reverse_lazy('issue_management:space_admin:issue_list')
    
    def form_valid(self, form):
        # Set the reporter to the current user before saving
        form.instance.reporter = self.request.user
        
        # Save the issue first
        response = super().form_valid(form)
        
        # Handle image uploads
        image_fields = ['image1', 'image2', 'image3']
        for field_name in image_fields:
            image_file = form.cleaned_data.get(field_name)
            if image_file:
                IssueImage.objects.create(
                    issue=self.object,
                    image=image_file
                )
        
        return response    


class IssueDetailView(DetailView):
    template_name = "space_admin/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images').select_related('org', 'space')


class IssueImageDeleteView(View):
    """Delete a specific image attached to an issue"""
    
    def post(self, request, issue_slug, image_slug):
        # Get the issue and image
        issue = get_object_or_404(Issue, slug=issue_slug)
        image = get_object_or_404(IssueImage, slug=image_slug, issue=issue)
        
        # Store the image filename for the success message
        image_name = image.image.name
        
        # Delete the image file from storage
        if image.image:
            image.image.delete(save=False)
        
        # Delete the image record
        image.delete()
        
        messages.success(request, f'Image successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)


class IssueImageUploadView(View):
    """Upload additional images to an existing issue"""
    
    def get(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = AdditionalImageUploadForm()
        
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/image_upload.html', context)
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = AdditionalImageUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the list of uploaded images from cleaned_data
            images = form.cleaned_data.get('images')
            uploaded_count = 0
            
            # Ensure images is a list
            if not isinstance(images, list):
                images = [images] if images else []
            
            # Create IssueImage instances for each uploaded image
            for image_file in images:
                try:
                    IssueImage.objects.create(
                        issue=issue,
                        image=image_file
                    )
                    uploaded_count += 1
                except Exception as e:
                    messages.error(request, f'Failed to upload image "{image_file.name}": {str(e)}')
            
            if uploaded_count > 0:
                if uploaded_count == 1:
                    messages.success(request, f'Successfully uploaded {uploaded_count} image.')
                else:
                    messages.success(request, f'Successfully uploaded {uploaded_count} images.')
                
                # Redirect back to the issue detail page
                return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # If form is not valid, show errors
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/image_upload.html', context)


class IssueVoiceDeleteView(View):
    """Delete the voice recording attached to an issue"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue has a voice recording
        if not issue.voice:
            messages.error(request, 'No voice recording found for this issue.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # Delete the voice file from storage
        if issue.voice:
            issue.voice.delete(save=False)
        
        # Clear the voice field and save the issue
        issue.voice = None
        issue.save()
        
        messages.success(request, 'Voice recording successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)


class IssueVoiceUploadView(View):
    """Upload a voice recording to an existing issue"""
    
    def get(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue already has a voice recording
        if issue.voice:
            messages.error(request, 'This issue already has a voice recording. Delete it first to upload a new one.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        form = VoiceUploadForm()
        
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/voice_upload.html', context)
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue already has a voice recording
        if issue.voice:
            messages.error(request, 'This issue already has a voice recording. Delete it first to upload a new one.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        form = VoiceUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the voice file from cleaned_data
            voice_file = form.cleaned_data.get('voice')
            
            if voice_file:
                try:
                    # Save the voice file to the issue
                    issue.voice = voice_file
                    issue.save()
                    
                    messages.success(request, 'Voice recording successfully uploaded.')
                    return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
                    
                except Exception as e:
                    messages.error(request, f'Failed to upload voice recording: {str(e)}')
        
        # If form is not valid, show errors
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/voice_upload.html', context)


class IssueResolveView(View):
    """Mark an issue as resolved with resolution notes"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue is already resolved, closed, or cancelled
        if issue.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This issue is already {issue.get_status_display().lower()} and cannot be resolved again.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # Get resolution notes from the form
        resolution_notes = request.POST.get('resolution_notes', '').strip()
        
        if not resolution_notes:
            messages.error(request, 'Resolution notes are required to mark an issue as resolved.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        try:
            # Update the issue status and resolution notes
            issue.status = 'resolved'
            issue.resolution_notes = resolution_notes
            issue.save()
            
            messages.success(request, f'Issue "{issue.title}" has been successfully marked as resolved.')
            
        except Exception as e:
            messages.error(request, f'Failed to resolve issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)