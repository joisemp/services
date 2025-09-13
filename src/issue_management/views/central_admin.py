from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from ..models import Issue, IssueImage
from ..forms import IssueForm


class IssueListView(ListView):
    template_name = "central_admin/issue_management/issue_list.html"
    context_object_name = "issues"
    model = Issue
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images').select_related('org', 'space').all()

    
class IssueCreateView(CreateView):
    template_name = "central_admin/issue_management/issue_create.html"
    form_class = IssueForm
    success_url = reverse_lazy('issue_management:central_admin:issue_list')
    
    def form_valid(self, form):
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
    template_name = "central_admin/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images', 'comments').select_related('org', 'space')
    