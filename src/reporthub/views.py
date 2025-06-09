from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, IssueImage
from .forms import IssueForm

def issue_list(request):
    issues = Issue.objects.order_by('-created_at')
    return render(request, 'reporthub/issue_list.html', {'issues': issues})

def report_issue(request):
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save()
            # Handle multiple images
            for img in request.FILES.getlist('image'):
                IssueImage.objects.create(issue=issue, image=img)
            return redirect('reporthub:issue_list')
    else:
        form = IssueForm()
    return render(request, 'reporthub/report_issue.html', {'form': form})

def voice_record(request):
    return render(request, 'reporthub/voice_record.html')
