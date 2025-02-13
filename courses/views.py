from django.shortcuts import render, get_object_or_404
from .models import Course, Lesson

def course_list(request):
    courses = Course.objects.prefetch_related('lessons__tasks').all()
    return render(request, 'courses/courses.html', {'courses': courses})

def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    return render(request, 'courses/lesson.html', {'lesson': lesson})

def contact(request):
    return render(request, 'courses/contact.html')

def about(request):
    return render(request, 'courses/about.html')

def blog(request):
    return render(request, 'courses/blog.html')