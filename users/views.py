from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, StudentLoginForm, PlacementQuizForm, TeacherLoginForm
from .models import StudentLoginCode, Profile, LoginRole
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'your account has been created! You are now able to log in')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def student_login(request):
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            try:
                login_code = StudentLoginCode.objects.get(code=code)
                user = login_code.user
            except StudentLoginCode.DoesNotExist:
                user = None

            if user and hasattr(user, 'profile') and user.profile.user_type == 'student':
                login(request, user)
                return redirect('placement-quiz')
            else:
                form.add_error(None, 'Invalid credentials.')
    else:
        form = StudentLoginForm()
    return render(request, 'users/student_login.html', {'form': form})

def teacher_login(request):
    if request.method == 'POST':
        form = TeacherLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user and hasattr(user, 'profile') and user.profile.user_type == 'teacher':
                login(request, user)
                return redirect('membership')
            else:
                form.add_error(None, 'Invalid credentials.')
    else:
        form = TeacherLoginForm()
    return render(request, 'users/teacher_login.html', {'form': form})

class CustomLoginView(LoginView):
    def dispatch(self, request, *args, **kwargs):
        if not request.GET.get('user_type'):
            return redirect('choose-login')
        return super().dispatch(request, *args, **kwargs)

def form_valid(self, form):
    response = super().form_valid(form)
    user_type = self.request.POST.get('user_type') or self.request.GET.get('user_type')
    if user_type and hasattr(self.request.user, 'profile'):
        self.request.user.profile.user_type = user_type
        self.request.user.profile.save()
    return response

def choose_login(request):
    roles = LoginRole.objects.all()
    return render(request, 'users/login.html', {'roles': roles})

@login_required
def placement_quiz(request):
    if request.method == 'POST':
        form = PlacementQuizForm(request.POST)
        if form.is_valid():
            answers = form.cleaned_data
            # Simple logic: assign grade based on answers
            if answers['question_1'] == 'b' and answers['question_2'] == 'b':
                grade = '3rd'
            else:
                grade = '2nd'
            # Save to profile
            profile = request.user.profile
            profile.grade = grade
            profile.save()
            return redirect('home')
    else:
        form = PlacementQuizForm()
    return render(request, 'users/placement_quiz.html', {'form': form})

@login_required
def membership(request):
    return render(request, 'users/membership.html')

def is_teacher(user):
    return hasattr(user, 'profile') and user.profile.user_type == 'teacher'

@login_required
@user_passes_test(is_teacher)
def class_management(request):
    return render(request, 'users/class_management.html')

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile.html', context)