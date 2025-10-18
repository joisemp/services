/**
 * Form Submit Handler with Loading Animation
 * Prevents multiple form submissions and shows loading state on submit buttons
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        loadingClass: 'btn-loading',
        disabledClass: 'btn-disabled',
        spinnerHTML: '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>',
        loadingText: 'Processing...',
        // Time to wait before re-enabling button if form doesn't navigate away (in ms)
        reEnableDelay: 5000
    };

    /**
     * Initialize form submit handlers when DOM is ready
     */
    function init() {
        // Handle all forms with submit buttons
        document.addEventListener('submit', handleFormSubmit, true);
        
        // Handle forms that might be dynamically added (HTMX, etc.)
        observeFormChanges();
    }

    /**
     * Handle form submission
     */
    function handleFormSubmit(event) {
        const form = event.target;
        
        // Skip if form is already submitting
        if (form.dataset.submitting === 'true') {
            event.preventDefault();
            return false;
        }

        // Find the submit button that was clicked
        const submitButton = form.querySelector('button[type="submit"]:focus, input[type="submit"]:focus') 
            || form.querySelector('button[type="submit"], input[type="submit"]');

        if (!submitButton) {
            return; // No submit button found, let form submit normally
        }

        // Check if button is already disabled
        if (submitButton.disabled) {
            event.preventDefault();
            return false;
        }

        // Mark form as submitting
        form.dataset.submitting = 'true';

        // Store original button content
        if (!submitButton.dataset.originalText) {
            submitButton.dataset.originalText = submitButton.innerHTML;
        }

        // Disable the button and show loading state
        setLoadingState(submitButton);

        // Set a timeout to re-enable if form doesn't navigate away
        // (useful for AJAX forms or if submission fails)
        setTimeout(() => {
            if (form.dataset.submitting === 'true') {
                resetButtonState(submitButton, form);
            }
        }, CONFIG.reEnableDelay);
    }

    /**
     * Set loading state on submit button
     */
    function setLoadingState(button) {
        // Disable the button
        button.disabled = true;
        button.classList.add(CONFIG.loadingClass, CONFIG.disabledClass);
        
        // Add spinner and change text
        if (button.tagName === 'BUTTON') {
            button.innerHTML = CONFIG.spinnerHTML + 
                (button.dataset.loadingText || CONFIG.loadingText);
        } else if (button.tagName === 'INPUT') {
            button.value = CONFIG.loadingText;
        }

        // Add aria-label for accessibility
        button.setAttribute('aria-busy', 'true');
    }

    /**
     * Reset button to original state
     */
    function resetButtonState(button, form) {
        // Re-enable the button
        button.disabled = false;
        button.classList.remove(CONFIG.loadingClass, CONFIG.disabledClass);
        
        // Restore original content
        if (button.dataset.originalText) {
            if (button.tagName === 'BUTTON') {
                button.innerHTML = button.dataset.originalText;
            } else if (button.tagName === 'INPUT') {
                button.value = button.dataset.originalText;
            }
        }

        // Remove aria-label
        button.removeAttribute('aria-busy');

        // Mark form as not submitting
        if (form) {
            form.dataset.submitting = 'false';
        }
    }

    /**
     * Observe DOM for dynamically added forms (HTMX, etc.)
     */
    function observeFormChanges() {
        // Only if MutationObserver is supported
        if (typeof MutationObserver === 'undefined') {
            return;
        }

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    // Check if added node is a form or contains forms
                    if (node.nodeType === 1) { // Element node
                        if (node.tagName === 'FORM') {
                            // Already handled by the submit event listener
                        } else if (node.querySelectorAll) {
                            // Check for forms within the added node
                            const forms = node.querySelectorAll('form');
                            // Forms will be handled by the submit event listener
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Public API for manual control
     */
    window.FormSubmitHandler = {
        /**
         * Manually trigger loading state on a button
         */
        setLoading: function(buttonSelector) {
            const button = typeof buttonSelector === 'string' 
                ? document.querySelector(buttonSelector) 
                : buttonSelector;
            
            if (button) {
                const form = button.closest('form');
                if (form) {
                    form.dataset.submitting = 'true';
                }
                if (!button.dataset.originalText) {
                    button.dataset.originalText = button.innerHTML;
                }
                setLoadingState(button);
            }
        },

        /**
         * Manually reset button state
         */
        reset: function(buttonSelector) {
            const button = typeof buttonSelector === 'string' 
                ? document.querySelector(buttonSelector) 
                : buttonSelector;
            
            if (button) {
                const form = button.closest('form');
                resetButtonState(button, form);
            }
        },

        /**
         * Configure global settings
         */
        config: function(options) {
            Object.assign(CONFIG, options);
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
