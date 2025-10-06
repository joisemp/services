from django import template
from django.urls import resolve, reverse, NoReverseMatch

register = template.Library()


@register.filter
def get_item(queryset, index):
    """
    Get an item from a queryset by index.
    Usage: {{ queryset|get_item:index }}
    """
    try:
        # Convert queryset to list to access by index
        items = list(queryset)
        return items[index]
    except (IndexError, TypeError, ValueError):
        return None


@register.simple_tag(takes_context=True)
def is_active(context, url_name, return_value='active'):
    """
    Check if the current URL matches the given URL name pattern.
    
    Usage in templates:
        <a class="navlink {% is_active 'issue_management:central_admin:issue_list' %}" href="...">
    
    Or for multiple URL patterns:
        <a class="navlink {% is_active 'issue_management:central_admin:issue_list,issue_management:central_admin:issue_detail' %}" href="...">
    
    Or for wildcard matching (all URLs in a namespace):
        <a class="navlink {% is_active 'issue_management:central_admin:*' %}" href="...">
    """
    request = context.get('request')
    if not request:
        return ''
    
    try:
        current_url_name = resolve(request.path_info).url_name
        current_namespace = resolve(request.path_info).namespace
        
        # Build full current URL name with namespace
        if current_namespace:
            full_current_name = f"{current_namespace}:{current_url_name}"
        else:
            full_current_name = current_url_name
        
        # Handle multiple URL names separated by comma
        url_names = [name.strip() for name in url_name.split(',')]
        
        for name in url_names:
            # Check if it's a pattern match (ends with *)
            if name.endswith('*'):
                # Match namespace or beginning of URL name
                pattern = name[:-1]  # Remove the *
                if full_current_name.startswith(pattern):
                    return return_value
            else:
                # Exact match
                if full_current_name == name:
                    return return_value
    except Exception:
        # If any error occurs, just return empty string
        return ''
    
    return ''


@register.simple_tag(takes_context=True)
def is_active_path(context, path_pattern, return_value='active'):
    """
    Check if the current path matches the given path pattern.
    
    Usage in templates:
        <a class="navlink {% is_active_path '/issues/' %}" href="...">
    
    For exact match, use '=' prefix:
        <a class="navlink {% is_active_path '=/dashboard/' %}" href="...">
    """
    request = context.get('request')
    if not request:
        return ''
    
    current_path = request.path_info
    
    # Check for exact match
    if path_pattern.startswith('='):
        exact_path = path_pattern[1:]
        if current_path == exact_path:
            return return_value
    else:
        # Check if current path starts with the pattern
        if current_path.startswith(path_pattern):
            return return_value
    
    return ''