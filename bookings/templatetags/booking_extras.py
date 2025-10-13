from django import template

register = template.Library()

@register.filter
def booking_item_name(item):
    if getattr(item, "lab_test", None):
        return item.lab_test.name
    elif getattr(item, "profile", None):
        return item.profile.name
    elif getattr(item, "package", None):
        return item.package.name
    return "—"

@register.filter
def booking_item_type(item):
    if getattr(item, "lab_test", None):
        return "Lab Test"
    elif getattr(item, "profile", None):
        return "Lab Profile"
    elif getattr(item, "package", None):
        return "Lab Package"
    return "—"

@register.filter
def abs_val(value):
    """Return absolute value in templates."""
    try:
        return abs(float(value))
    except Exception:
        return value
