"""
Common views shared across all user roles for ticket management.
These views handle functionality that is role-agnostic.
"""
from django.views.generic import View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from ..models import Ticket, TicketReviewComment, TicketReviewCommentImage
from ..forms import TicketCommentForm, TicketReviewCommentForm


class TicketCommentListView(LoginRequiredMixin, View):
    """
    HTMX endpoint to return the list of comments for a ticket.
    This view is role-agnostic and can be used by all authenticated users.
    """
    
    def get(self, request, ticket_slug):
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        comments = ticket.comments.select_related('user').all()
        
        return render(request, 'common/ticket_management/partials/comment_list.html', {
            'comments': comments,
            'ticket': ticket
        })


class TicketCommentCreateView(LoginRequiredMixin, View):
    """
    HTMX endpoint to create a new comment.
    This view is role-agnostic and can be used by all authenticated users.
    """
    
    def post(self, request, ticket_slug):
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        form = TicketCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.user = request.user
            comment.save()
            
            # Return the updated comment list
            comments = ticket.comments.select_related('user').all()
            return render(request, 'common/ticket_management/partials/comment_list.html', {
                'comments': comments,
                'ticket': ticket
            })
        else:
            # Return form errors
            return render(request, 'common/ticket_management/partials/comment_form.html', {
                'form': form,
                'ticket': ticket
            }, status=400)
    
    def get(self, request, ticket_slug):
        """Return empty form for HTMX to display"""
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        form = TicketCommentForm()
        
        return render(request, 'common/ticket_management/partials/comment_form.html', {
            'form': form,
            'ticket': ticket
        })


class TicketReviewCommentCreateView(LoginRequiredMixin, View):
    """
    View to create a new review comment with optional images.
    This view is role-agnostic and can be used by all authenticated users.
    """
    
    def post(self, request, ticket_slug):
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        form = TicketReviewCommentForm(request.POST, request.FILES)
        
        if form.is_valid():
            review_comment = form.save(commit=False)
            review_comment.ticket = ticket
            review_comment.user = request.user
            review_comment.save()
            
            # Handle image uploads (up to 3 images)
            for i in range(1, 4):
                image_field_name = f'image{i}'
                image = request.FILES.get(image_field_name)
                
                if image:
                    TicketReviewCommentImage.objects.create(
                        review_comment=review_comment,
                        image=image
                    )
            
            messages.success(request, 'Review comment added successfully!')
            return redirect(request.META.get('HTTP_REFERER', 'ticket_management:reviewer:ticket_detail'), ticket_slug=ticket_slug)
        else:
            messages.error(request, 'Error adding review comment. Please check the form.')
            return redirect(request.META.get('HTTP_REFERER', 'ticket_management:reviewer:ticket_detail'), ticket_slug=ticket_slug)
