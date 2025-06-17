from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, StudentLoginForm, PlacementQuizForm
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
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user and hasattr(user, 'profile') and user.profile.user_type == 'student':
                login(request, user)
                if not user.profile.grade:
                    return redirect('placement-quiz')
                return redirect('home')
            else:
                ...
    else:
        form = StudentLoginForm()
    return render(request, 'users/student_login.html', {'form': form})

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

def student_login(request):
    if request.method == 'POST':
        if 'code' in request.POST:
            # Accept any 4-digit code for now
            code = request.POST.get('code')
            if code and len(code) == 4 and code.isdigit():
                username = request.session.get('student_username')
                user = User.objects.get(username=username)
                # Set user_type to "student" on the profile
                if hasattr(user, 'profile'):
                    user.profile.user_type = 'student'
                    user.profile.save()
                login(request, user)
                return redirect('home')
            else:
                return render(request, 'users/student_login_code.html', {'error': 'Invalid code'})
        else:
            form = StudentLoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user:
                    request.session['student_username'] = username
                    return render(request, 'users/student_login_code.html')
                else:
                    form.add_error(None, 'Invalid credentials.')
    else:
        form = StudentLoginForm()
    return render(request, 'users/student_login.html', {'form': form})

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