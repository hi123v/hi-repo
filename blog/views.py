from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from .models import Task, Course
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
from .models import Post, Course
import random

def home(request):
    courses = Course.objects.prefetch_related('lessons__tasks').all()
    user_type = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_type = request.user.profile.user_type
    return render(request, 'blog/home.html', {
        'title': 'Home',
        'courses': courses,
        'user_type': user_type
    })

class PostListView(ListView):
    model = Post
    template_name = 'blog/blog.html'  # Use the blog.html template for blog home
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 5

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
    return render(request, 'blog/about.html', {'title': 'About'})

def task_detail(request, task_id):
    # Determine the range of numbers based on the task ID
    if task_id == 1:  # Task 1: Numbers 1-10
        numbers = range(1, 11)
    elif task_id == 2:  # Task 2: Numbers 11-20
        numbers = range(11, 21)
    else:
        numbers = []  # Default to an empty list if the task ID is invalid

    return render(request, 'blog/task_detail.html', {'numbers': numbers, 'task_id': task_id})

def games(request):
    return render(request, 'blog/games.html', {'title': 'Games'})

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
    return render(request, 'blog/course_detail.html', {'course': course, 'lessons': lessons})

def home(request):
    courses = Course.objects.prefetch_related('lessons__tasks').all()
    user_type = None
    random_score = random.randint(60, 100)  # or any range you want
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_type = request.user.profile.user_type
    return render(request, 'blog/home.html', {
        'title': 'Home',
        'courses': courses,
        'user_type': user_type,
        'random_score': random_score
    })