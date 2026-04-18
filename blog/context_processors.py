from .models import Course


def all_courses(request):
    try:
        courses = Course.objects.all()
    except Exception:
        courses = []
    return {'all_courses': courses}
