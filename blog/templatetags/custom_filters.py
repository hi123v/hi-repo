# filepath: /c:/Users/georg/source/webpage_project/blog/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='is_not_student')
def is_not_student(user):
    return not user.groups.filter(name='Students').exists()