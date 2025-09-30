from django import template

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