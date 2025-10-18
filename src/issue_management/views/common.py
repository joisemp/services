"""
Common views shared across all user roles for issue management.
These views handle functionality that is role-agnostic.
"""
from django.views.generic import View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from ..models import Issue, IssueReviewComment, IssueReviewCommentImage
from ..forms import IssueCommentForm, IssueReviewCommentForm


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


class IssueReviewCommentCreateView(LoginRequiredMixin, View):
    """
    View to create a new review comment with optional images.
    This view is role-agnostic and can be used by all authenticated users.
    """
    
    def post(self, request, issue_slug):
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = IssueReviewCommentForm(request.POST, request.FILES)
        
        if form.is_valid():
            review_comment = form.save(commit=False)
            review_comment.issue = issue
            review_comment.user = request.user
            review_comment.save()
            
            # Handle image uploads (up to 3 images)
            for i in range(1, 4):
                image_field_name = f'image{i}'
                image = request.FILES.get(image_field_name)
                
                if image:
                    IssueReviewCommentImage.objects.create(
                        review_comment=review_comment,
                        image=image
                    )
            
            messages.success(request, 'Review comment added successfully!')
            return redirect(request.META.get('HTTP_REFERER', 'issue_management:reviewer:issue_detail'), issue_slug=issue_slug)
        else:
            messages.error(request, 'Error adding review comment. Please check the form.')
            return redirect(request.META.get('HTTP_REFERER', 'issue_management:reviewer:issue_detail'), issue_slug=issue_slug)
