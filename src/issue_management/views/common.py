"""
Common views shared across all user roles for issue management.
These views handle functionality that is role-agnostic.
"""
from django.views.generic import View
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import Issue
from ..forms import IssueCommentForm


class IssueCommentListView(LoginRequiredMixin, View):
    """
    HTMX endpoint to return the list of comments for an issue.
    This view is role-agnostic and can be used by all authenticated users.
    """
    
    def get(self, request, issue_slug):
        issue = get_object_or_404(Issue, slug=issue_slug)
        comments = issue.comments.select_related('user').all()
        
        return render(request, 'common/issue_management/partials/comment_list.html', {
            'comments': comments,
            'issue': issue
        })


class IssueCommentCreateView(LoginRequiredMixin, View):
    """
    HTMX endpoint to create a new comment.
    This view is role-agnostic and can be used by all authenticated users.
    """
    
    def post(self, request, issue_slug):
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = IssueCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.issue = issue
            comment.user = request.user
            comment.save()
            
            # Return the updated comment list
            comments = issue.comments.select_related('user').all()
            return render(request, 'common/issue_management/partials/comment_list.html', {
                'comments': comments,
                'issue': issue
            })
        else:
            # Return form errors
            return render(request, 'common/issue_management/partials/comment_form.html', {
                'form': form,
                'issue': issue
            }, status=400)
    
    def get(self, request, issue_slug):
        """Return empty form for HTMX to display"""
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = IssueCommentForm()
        
        return render(request, 'common/issue_management/partials/comment_form.html', {
            'form': form,
            'issue': issue
        })
