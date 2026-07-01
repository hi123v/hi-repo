from django.urls import reverse
from .models import Course


def all_courses(request):
    try:
        courses = Course.objects.all()
    except Exception:
        courses = []
    return {'all_courses': courses}


def home_url(request):
    try:
        if getattr(request.user, 'is_authenticated', False):
            profile = getattr(request.user, 'profile', None)
            user_type = getattr(profile, 'user_type', None)
            if getattr(request.user, 'is_superuser', False) or user_type == 'teacher':
                return {'home_url': reverse('teachers')}
            if user_type == 'student':
                return {'home_url': reverse('students')}
            if user_type == 'parent':
                return {'home_url': reverse('parents')}
    except Exception:
        pass
    return {'home_url': reverse('home')}
