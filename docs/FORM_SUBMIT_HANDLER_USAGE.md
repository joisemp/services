# Form Submit Handler - Usage Guide

## Overview
The Form Submit Handler automatically adds loading animations to submit buttons and prevents multiple form submissions.

## Features
- ✅ Automatic loading spinner on submit buttons
- ✅ Prevents multiple form submissions
- ✅ Works with standard forms and HTMX
- ✅ Customizable loading text and styles
- ✅ Accessibility support (ARIA attributes)
- ✅ Auto re-enables after timeout (for AJAX forms)

## Installation

### 1. Include the CSS file in your base template:

```html
<!-- In your base.html or sidebar_base.html -->
<link rel="stylesheet" href="{% static 'styles/components/form-submit-handler.css' %}">
```

### 2. Include the JavaScript file before closing `</body>` tag:

```html
<!-- Before closing </body> -->
<script src="{% static 'js/form-submit-handler.js' %}"></script>
```

## Basic Usage

### Automatic Mode (No Code Required!)

Once included, the script **automatically** handles ALL forms on the page:

```html
<form method="post">
    {% csrf_token %}
    <input type="text" name="title" required>
    <button type="submit" class="btn btn-primary">Submit</button>
</form>
```

When user clicks "Submit":
1. Button shows spinner and "Processing..."
2. Button becomes disabled
3. Form submits normally
4. If page doesn't navigate away (AJAX), button re-enables after 5 seconds

### Custom Loading Text

Add `data-loading-text` attribute to button:

```html
<button type="submit" class="btn btn-primary" data-loading-text="Saving...">
    Save Issue
</button>
```

Result: Shows "Saving..." instead of "Processing..."

### Manual Control (Advanced)

For AJAX forms or custom scenarios:

```javascript
// Start loading manually
FormSubmitHandler.setLoading('#mySubmitButton');

// Reset button after AJAX completes
fetch('/api/endpoint', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        FormSubmitHandler.reset('#mySubmitButton');
    })
    .catch(error => {
        FormSubmitHandler.reset('#mySubmitButton');
    });
```

### Global Configuration

Customize default settings:

```javascript
// Add this after including form-submit-handler.js
FormSubmitHandler.config({
    loadingText: 'Please wait...',     // Default loading text
    reEnableDelay: 8000,               // 8 seconds instead of 5
    spinnerHTML: '<i class="fas fa-spinner fa-spin"></i>' // Use FontAwesome spinner
});
```

## Examples

### Example 1: Issue Create Form

```html
<form method="post" action="{% url 'issue_management:central_admin:issue_create' %}">
    {% csrf_token %}
    {{ form.as_p }}
    
    <button type="submit" class="btn btn-success" data-loading-text="Creating Issue...">
        Create Issue
    </button>
</form>
```

### Example 2: Work Task Complete Form

```html
<form method="post" action="{% url 'issue_management:supervisor:work_task_complete' work_task_slug=work_task.slug %}">
    {% csrf_token %}
    {{ form.as_p }}
    
    <button type="submit" class="btn btn-primary" data-loading-text="Completing Task...">
        Mark as Completed
    </button>
</form>
```

### Example 3: Delete Confirmation

```html
<form method="post" action="{% url 'issue_management:central_admin:issue_delete' issue_slug=issue.slug %}">
    {% csrf_token %}
    
    <button type="submit" class="btn btn-danger" data-loading-text="Deleting...">
        Delete Issue
    </button>
</form>
```

### Example 4: HTMX Form

```html
<form hx-post="/api/update" hx-target="#result">
    {% csrf_token %}
    <input type="text" name="title">
    
    <button type="submit" class="btn btn-primary" data-loading-text="Updating...">
        Update
    </button>
</form>

<script>
// Reset button after HTMX request completes
document.body.addEventListener('htmx:afterRequest', function(event) {
    const form = event.detail.elt;
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        FormSubmitHandler.reset(submitBtn);
    }
});
</script>
```

## CSS Classes

The script automatically adds these classes:

| Class | Description |
|-------|-------------|
| `btn-loading` | Applied when button is in loading state |
| `btn-disabled` | Applied when button is disabled |
| `spinner-border` | Bootstrap-style spinner element |
| `spinner-border-sm` | Small spinner size |

## Customizing Styles

Override the default styles in your custom CSS:

```css
/* Custom spinner color */
.btn-primary .spinner-border {
    border-color: #fff;
    border-right-color: transparent;
}

/* Custom loading opacity */
.btn-loading {
    opacity: 0.7;
}

/* Add pulse animation */
.btn-loading {
    animation: btn-loading-pulse 1.5s ease-in-out infinite;
}
```

## Browser Support

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ IE11 (with polyfills)

## Troubleshooting

### Button doesn't show loading state

**Check:**
1. CSS file is included in `<head>`
2. JS file is included before `</body>`
3. Button has `type="submit"` attribute

### Button stays disabled after submission

**Cause:** Form navigates away before timeout completes (this is normal)

**Solution:** Button will reset on page load or use manual reset for AJAX

### Multiple spinners appear

**Cause:** Script included multiple times

**Solution:** Include script only once in base template

## API Reference

### FormSubmitHandler.setLoading(selector)
Manually trigger loading state on a button.

**Parameters:**
- `selector` (String|Element) - CSS selector or button element

**Example:**
```javascript
FormSubmitHandler.setLoading('#submitBtn');
```

### FormSubmitHandler.reset(selector)
Manually reset button to original state.

**Parameters:**
- `selector` (String|Element) - CSS selector or button element

**Example:**
```javascript
FormSubmitHandler.reset('#submitBtn');
```

### FormSubmitHandler.config(options)
Configure global settings.

**Parameters:**
- `options` (Object) - Configuration options

**Example:**
```javascript
FormSubmitHandler.config({
    loadingText: 'Loading...',
    reEnableDelay: 10000
});
```

## Integration with Existing Project

Add to `templates/base.html` or `templates/sidebar_base.html`:

```html
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <!-- Existing head content -->
    <link rel="stylesheet" href="{% static 'styles/components/form-submit-handler.css' %}">
</head>
<body>
    <!-- Your content -->
    
    <!-- Existing scripts -->
    <script src="{% static 'js/form-submit-handler.js' %}"></script>
</body>
</html>
```

That's it! All forms in your application will now have loading animations and double-submit prevention! 🎉
