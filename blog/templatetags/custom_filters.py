# filepath: /c:/Users/georg/source/webpage_project/blog/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='is_not_student')
def is_not_student(user):
    try:
        if not getattr(user, 'is_authenticated', False):
            return True
        # Check group membership (name used elsewhere is 'Student')
        if user.groups.filter(name='Student').exists():
            return False
        # Fallback to profile.user_type if present
        if hasattr(user, 'profile') and getattr(user.profile, 'user_type', None) == 'student':
            return False
        return True
    except Exception:
        return True