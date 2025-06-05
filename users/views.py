from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, StudentLoginForm
from .models import StudentLoginCode, Profile
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login


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


@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, 
                                   request.FILES, 
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save
            p_form.save()
            messages.success(request, f'your account has been updated!')
            return redirect('profile') 

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'users/profile.html', context)

class CustomLoginView(LoginView):
    def form_valid(self, form):
        response = super().form_valid(form)
        user_type = self.request.POST.get('user_type')
        if user_type and hasattr(self.request.user, 'profile'):
            self.request.user.profile.user_type = user_type
            self.request.user.profile.save()
        return response

def student_login(request):
    if request.method == 'POST':
        if 'code' in request.POST:
            # Step 2: Verify code
            username = request.session.get('student_username')
            code = request.POST.get('code')
            try:
                user = User.objects.get(username=username)
                login_code = StudentLoginCode.objects.filter(user=user, code=code).latest('created_at')
                login(request, user)
                return redirect('home')
            except (User.DoesNotExist, StudentLoginCode.DoesNotExist):
                return render(request, 'users/student_login_code.html', {'error': 'Invalid code'})
        else:
            # Step 1: Authenticate and send code
            form = StudentLoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                parent_email = form.cleaned_data['parent_email']
                user = authenticate(request, username=username, password=password)
                if user and hasattr(user, 'profile') and user.profile.user_type == 'student':
                    code = f"{random.randint(1000, 9999)}"
                    StudentLoginCode.objects.create(user=user, parent_email=parent_email, code=code)
                    send_mail(
                        'Your Student Login Code',
                        f'Your code is: {code}',
                        'noreply@yourdomain.com',
                        [parent_email],
                        fail_silently=False,
                    )
                    request.session['student_username'] = username
                    return render(request, 'users/student_login_code.html')
                else:
                    form.add_error(None, 'Invalid credentials or not a student account.')
    else:
        form = StudentLoginForm()
    return render(request, 'users/student_login.html', {'form': form})

 