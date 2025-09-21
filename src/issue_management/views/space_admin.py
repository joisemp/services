from django.views.generic import ListView, CreateView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from ..models import Issue, IssueImage
from ..forms import IssueForm
from django.urls import reverse_lazy

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
    
    