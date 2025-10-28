# core/templatetags/size_extras.py
from django import template

register = template.Library()

@register.filter
def naturalsize(bytes_val):
    try:
        size = float(bytes_val)
    except (TypeError, ValueError):
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    # muestra con 0 o 1 decimal según corresponda
    return f"{size:.0f}{units[i]}" if size >= 10 or i == 0 else f"{size:.1f}{units[i]}"
