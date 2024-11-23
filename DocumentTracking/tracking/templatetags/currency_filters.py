# myapp/templatetags/currency_filters.py
from django import template

register = template.Library()

@register.filter
def to_php(value):
    """Format the number as Philippine Peso (₱)."""
    try:
        return f"₱{value:,.2f}"  # Format with commas and 2 decimal places
    except (ValueError, TypeError):
        return value
