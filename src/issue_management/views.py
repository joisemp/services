from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, IssueImage
from .forms import IssueForm

def issue_list(request):
    issues = Issue.objects.order_by('-created_at')
    return render(request, 'issue_management/issue_list.html', {'issues': issues})

def report_issue(request):
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES)
        images = request.FILES.getlist('image')
        if len(images) > 3:
            form.add_error('image', 'You can upload a maximum of 3 images.')
        if form.is_valid():
            issue = form.save(commit=False)
            # Assign organisation if user is authenticated and has a profile
            if request.user.is_authenticated and hasattr(request.user, 'profile'):
                issue.org = request.user.profile.org
                issue.created_by = request.user
            issue.save()
            # Handle multiple images (limit to 3)
            for img in images[:3]:
                IssueImage.objects.create(issue=issue, image=img)
            return redirect('issue_management:issue_list')
    else:
        form = IssueForm()
    return render(request, 'issue_management/report_issue.html', {'form': form})

def voice_record(request):
    return render(request, 'issue_management/voice_record.html')
