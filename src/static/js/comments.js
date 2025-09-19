// Comment functionality JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Auto-resize textarea on mobile
    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }

    // Handle textarea auto-resize
    document.addEventListener('input', function(e) {
        if (e.target && e.target.matches('#comment-form-sticky textarea')) {
            autoResize(e.target);
        }
    });

    // Handle Enter key submission (Ctrl+Enter or Cmd+Enter)
    document.addEventListener('keydown', function(e) {
        if (e.target && e.target.matches('#comment-form-sticky textarea')) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                const form = e.target.closest('form');
                if (form) {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn && !submitBtn.disabled) {
                        submitBtn.click();
                    }
                }
            }
        }
    });

    // Disable submit button during form submission
    document.addEventListener('htmx:beforeRequest', function(e) {
        if (e.target && e.target.matches('#comment-form-sticky .comment-form')) {
            const submitBtn = e.target.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Posting...';
            }
        }
    });

    // Re-enable submit button after response
    document.addEventListener('htmx:afterRequest', function(e) {
        if (e.target && e.target.matches('#comment-form-sticky .comment-form')) {
            const submitBtn = e.target.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i><span class="d-none d-sm-inline">Post Comment</span><span class="d-inline d-sm-none">Post</span>';
            }
        }
    });

    // Clear form after successful submission
    document.addEventListener('htmx:afterSwap', function(e) {
        if (e.target && e.target.id === 'comments-list-area') {
            // Find the comment form and clear it
            const commentForm = document.querySelector('#comment-form-sticky .comment-form');
            if (commentForm) {
                const textarea = commentForm.querySelector('textarea');
                if (textarea) {
                    textarea.value = '';
                    textarea.style.height = 'auto';
                }
            }
            
            // Scroll to bottom of comments list on mobile
            const commentsArea = document.getElementById('comments-list-area');
            if (commentsArea && window.innerWidth <= 768) {
                commentsArea.scrollTop = commentsArea.scrollHeight;
            }
        }
    });

    // Handle focus on comment textarea for mobile
    document.addEventListener('focus', function(e) {
        if (e.target && e.target.matches('#comment-form-sticky textarea')) {
            // On mobile, ensure the sticky form is visible
            if (window.innerWidth <= 768) {
                setTimeout(() => {
                    e.target.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'nearest' 
                    });
                }, 300); // Delay to wait for virtual keyboard
            }
        }
    }, true);
});