from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from .models import Task, Course, CompletedTask, Grade
from .models import NewsletterSubscriber
from django.core.mail import send_mail
from django.conf import settings
from django.views.generic import (
    ListView, 
    DetailView, 
    CreateView, 
    UpdateView,
    DeleteView
)
from .models import Post, Course, SiteSectionItem, Game
from .forms import PostForm
import random
from django.contrib.auth import get_user_model
from users.models import Profile

def home(request):
    # If a logged-in user hasn't picked a grade yet, force grade selection first
    if request.user.is_authenticated and hasattr(request.user, 'profile') and not request.user.profile.grade:
        return redirect('choose-grade')

    all_courses = Course.objects.prefetch_related('lessons__tasks').all()
    user_type = None
    # Default to empty; show user's selected courses if any
    courses = []
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_type = request.user.profile.user_type
        user_courses = request.user.profile.courses.prefetch_related('lessons__tasks').all()
        if user_courses.exists():
            courses = user_courses
    return render(request, 'blog/home.html', {
        'title': 'Home',
        'courses': courses,
        'all_courses': all_courses,
        'user_type': user_type,
    })


@login_required
def manage_courses(request):
    if request.method == 'POST':
        selected = request.POST.getlist('courses')
        # Update user's profile courses
        request.user.profile.courses.set(Course.objects.filter(pk__in=selected))
        return redirect('home')
    # GET fallback: render page with all courses (modal is used from home)
    return render(request, 'blog/manage_courses.html', {'all_courses': Course.objects.all()})


@login_required
def choose_grade(request):
    grades = Grade.objects.all()
    if request.method == 'POST':
        grade_id = request.POST.get('grade')
        if grade_id:
            grade = get_object_or_404(Grade, pk=grade_id)
            # save grade name to profile and redirect to confirmation
            request.user.profile.grade = grade.name
            request.user.profile.save()
            return redirect('confirm-grade', grade_id=grade.pk)
    return render(request, 'blog/choose_grade.html', {'grades': grades})


@login_required
def confirm_grade(request, grade_id):
    grade = get_object_or_404(Grade, pk=grade_id)
    if request.method == 'POST':
        choice = request.POST.get('auto_enroll')
        if choice == 'yes':
            # enroll user in all courses for the grade
            request.user.profile.courses.set(grade.courses.all())
        return redirect('home')
    return render(request, 'blog/confirm_grade.html', {'grade': grade})

class PostListView(ListView):
    model = Post
    template_name = 'blog/blog.html'  
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Provide an empty post form for the modal (only for authenticated users)
        if self.request.user.is_authenticated:
            context['form'] = PostForm()
        return context

class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-date_posted')

class PostDetailView(DetailView):
    model = Post

class TaskDetailView(DetailView):
    model = Task
    template_name = 'blog/task_detail.html' 
    context_object_name = 'task'  

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False
    
def is_not_student(user):
    return not user.groups.filter(name='Student').exists()

@login_required
@user_passes_test(is_not_student)
def chat(request):
    return render(request, 'blog/chat.html', {'title': 'Chat'})

def about(request):
    # Provide current items for each about subsection (mission, team, career, contact, faq)
    current_mission = SiteSectionItem.objects.filter(section=SiteSectionItem.SECTION_MISSION, is_current=True).first()
    current_team = SiteSectionItem.objects.filter(section=SiteSectionItem.SECTION_TEAM, is_current=True).first()
    current_career = SiteSectionItem.objects.filter(section=SiteSectionItem.SECTION_CAREER, is_current=True).first()
    current_contact = SiteSectionItem.objects.filter(section=SiteSectionItem.SECTION_CONTACT, is_current=True).first()
    current_faq = SiteSectionItem.objects.filter(section=SiteSectionItem.SECTION_FAQ, is_current=True).first()
    return render(request, 'blog/about.html', {
        'title': 'About',
        'current_mission': current_mission,
        'current_team': current_team,
        'current_career': current_career,
        'current_contact': current_contact,
        'current_faq': current_faq,
    })

def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    # Try to parse template_data as JSON list, otherwise fall back to empty list
    import json
    data = []
    try:
        data = json.loads(task.template_data) if task.template_data else []
    except Exception:
        data = []

    return render(request, 'blog/task_detail.html', {'task': task, 'template_data': data})

def games(request):
    games_qs = Game.objects.all()
    return render(request, 'blog/games.html', {'title': 'Games', 'games': games_qs})

def number_pop_game(request):
    return render(request, 'blog/number_pop_game.html')

def newsletter_signup(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            if NewsletterSubscriber.objects.filter(email=email).exists():
                messages.info(request, "You're already subscribed!")
            else:
                NewsletterSubscriber.objects.create(email=email)
                # Send welcome email
                send_mail(
                    "Welcome to the Quest-ly's Newsletter!",
                    "Thanks for subscribing! You'll now get updates about all the cool stuff on the app.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True,
                )
                messages.success(request, "Thanks for subscribing! Check your email for a welcome message.")
    return redirect(request.META.get('HTTP_REFERER', '/'))

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all()
    random_pattern = [random.randint(1, 20) for _ in range(6)]
    completed_tasks = []
    if request.user.is_authenticated:
        completed_tasks = CompletedTask.objects.filter(user=request.user).values_list('task_id', flat=True)
    return render(request, 'blog/course_detail.html', {
        'course': course,
        'lessons': lessons,
        'random_pattern': random_pattern,
        'completed_tasks': completed_tasks,
    })

@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    completed, created = CompletedTask.objects.get_or_create(user=request.user, task=task)
    if created:
        profile = request.user.profile
        profile.points += 5
        profile.save()
    messages.success(request, f"You have completed the task: {task.name}")
    return redirect('course-detail', course_id=task.lesson.course.id)

@login_required
def uncomplete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    deleted, _ = CompletedTask.objects.filter(user=request.user, task=task).delete()
    if deleted:
        profile = request.user.profile
        profile.points = max(0, profile.points - 5)
        profile.save()
    messages.info(request, f"You have marked the task as not completed: {task.name}")
    return redirect('course-detail', course_id=task.lesson.course.id)

def leaderboard(request):
    user_league = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_league = request.user.profile.league
    # Only show users in the same league as the current user
    profiles = Profile.objects.filter(league=user_league).select_related('user').order_by('-points')[:20]
    return render(request, 'blog/leaderboard.html', {'profiles': profiles, 'user_league': user_league})