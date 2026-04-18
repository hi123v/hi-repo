from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from users.models import Profile
from blog.models import Course, Task, CompletedTask, NewsletterSubscriber
from datetime import timedelta


def _superuser_required(user):
    # allow access to staff members or superusers
    return user and user.is_active and (user.is_superuser or user.is_staff)


@user_passes_test(_superuser_required)
def analytics_dashboard(request):
    now = timezone.now()
    last_30 = now - timedelta(days=30)

    total_users = User.objects.count()
    new_users_last_30 = User.objects.filter(date_joined__gte=last_30).count()
    active_last_30 = User.objects.filter(last_login__gte=last_30).count()
    total_profiles = Profile.objects.count()
    total_courses = Course.objects.count()
    total_tasks = Task.objects.count()
    completed_tasks = CompletedTask.objects.count()
    newsletter_last_30 = NewsletterSubscriber.objects.filter(date_joined__gte=last_30).count()

    # signups per day for last 30 days
    labels = []
    signups = []
    for i in range(30, 0, -1):
        day = (now - timedelta(days=i)).date()
        labels.append(day.strftime('%b %d'))
        signups.append(User.objects.filter(date_joined__date=day).count())

    # Placeholder revenue/memberships if not tracked in models
    memberships_last_30 = 0
    revenue_last_30 = 0.0

    context = {
        'total_users': total_users,
        'new_users_last_30': new_users_last_30,
        'active_last_30': active_last_30,
        'total_profiles': total_profiles,
        'total_courses': total_courses,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'newsletter_last_30': newsletter_last_30,
        'memberships_last_30': memberships_last_30,
        'revenue_last_30': revenue_last_30,
        'chart_labels': labels,
        'chart_signups': signups,
    }
    return render(request, 'admin/analytics.html', context)
