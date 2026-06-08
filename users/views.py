from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, StudentLoginForm, PlacementQuizForm, TeacherLoginForm
from .models import StudentLoginCode, Profile, LoginRole
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from blog.models import Course, Grade as GradeModel
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import FriendRequest, Friendship, StreakRequest

def register(request, role=None):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # set profile fields created by post_save signal
            user.refresh_from_db()
            # user_type comes from the URL role (buttons lead to /register/<role>/)
            user.profile.user_type = role or 'student'
            grade = form.cleaned_data.get('grade') or ''
            # Normalize grade values (e.g. '2' -> '2nd') so they match Grade.name
            def _normalize_grade(g):
                if not g:
                    return ''
                g = str(g).strip()
                if not g.isdigit():
                    return g
                try:
                    n = int(g)
                except Exception:
                    return g
                if 10 <= (n % 100) <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
                return f"{n}{suffix}"

            grade_normalized = _normalize_grade(grade)
            # Only assign a grade for student accounts; clear for others
            if user.profile.user_type == 'student':
                user.profile.grade = grade_normalized
            else:
                user.profile.grade = ''
            user.profile.save()
            # Auto-enroll courses for explicit grade selections (not 'Unsure' or empty)
            if user.profile.user_type == 'student' and grade and grade.lower() != 'unsure':
                try:
                    # try both normalized and raw grade when matching Grade objects
                    grade_obj = GradeModel.objects.filter(Q(name__iexact=grade_normalized) | Q(name__iexact=grade)).first()
                    if grade_obj:
                        courses = grade_obj.courses.all()
                        if courses.exists():
                            user.profile.courses.set(courses)
                except Exception:
                    pass
            # Log the user in so placement quiz (if needed) can save grade
            try:
                raw_password = form.cleaned_data.get('password1')
                user_auth = authenticate(request, username=user.username, password=raw_password)
                if user_auth:
                    login(request, user_auth)
            except Exception:
                pass
            # if student, optionally store parent email in StudentLoginCode
            if user.profile.user_type == 'student':
                parent_email = form.cleaned_data.get('parent_email')
                if parent_email:
                    import secrets
                    code = ''.join(secrets.choice('0123456789') for _ in range(4))
                    StudentLoginCode.objects.create(user=user, parent_email=parent_email, code=code)
            messages.success(request, f'your account has been created!')
            # If user selected 'Unsure', send them to placement quiz to determine grade
            if grade and grade.lower() == 'unsure':
                return redirect('placement-quiz')
            # Otherwise redirect to home/profile (user is logged in)
            return redirect('home')
        # if POST but form invalid, render form page again (respect role if provided)
        if role:
            return render(request, 'users/register_form.html', {'form': form, 'role': role})
        else:
            roles = LoginRole.objects.all()
            return render(request, 'users/register.html', {'roles': roles, 'form': form})
    else:
        # If a role is provided in the URL, show the form-only page preselecting that role
        if role:
            form = UserRegisterForm()
            return render(request, 'users/register_form.html', {'form': form, 'role': role})
        # otherwise show the chooser with role image buttons
        form = UserRegisterForm()
        roles = LoginRole.objects.all()
        return render(request, 'users/register.html', {'roles': roles})

def student_login(request):
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            parent_email = form.cleaned_data.get('parent_email')

            # Check username exists
            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                form.add_error('username', 'Username not found.')
            else:
                # Check password
                user_auth = authenticate(request, username=username, password=password)
                if user_auth is None:
                    form.add_error('password', 'Incorrect password.')
                else:
                    # Ensure the account is a student (unless superuser)
                    if not user_auth.is_superuser and (not hasattr(user_auth, 'profile') or user_auth.profile.user_type != 'student'):
                        other_role = getattr(user_auth.profile, 'user_type', 'other') if hasattr(user_auth, 'profile') else 'other'
                        form.add_error(None, f"Account is registered as {other_role}. Did you forget your account, or would you like to register a student account? Register here: /register/student/")
                    else:
                        # If superuser, allow login without parent email validation
                        if user_auth.is_superuser:
                            login(request, user_auth)
                            return redirect('placement-quiz')
                        # Validate parent's email against StudentLoginCode records
                        if StudentLoginCode.objects.filter(user=user_auth, parent_email=parent_email).exists():
                            login(request, user_auth)
                            return redirect('placement-quiz')
                        else:
                            form.add_error('parent_email', "Parent's email doesn't match our records.")
    else:
        form = StudentLoginForm()
    return render(request, 'users/student_login.html', {'form': form})

def teacher_login(request):
    if request.method == 'POST':
        form = TeacherLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                form.add_error('username', 'Username not found.')
            else:
                user_auth = authenticate(request, username=username, password=password)
                if user_auth is None:
                    form.add_error('password', 'Incorrect password.')
                else:
                    # Allow superuser to login regardless of stored role
                    if not user_auth.is_superuser and (not hasattr(user_auth, 'profile') or user_auth.profile.user_type != 'teacher'):
                        other_role = getattr(user_auth.profile, 'user_type', 'other') if hasattr(user_auth, 'profile') else 'other'
                        form.add_error(None, f"Account is registered as {other_role}. Did you forget your account, or would you like to register a teacher account? Register here: /register/teacher/")
                    else:
                        login(request, user_auth)
                        return redirect('membership')
    else:
        form = TeacherLoginForm()
    return render(request, 'users/teacher_login.html', {'form': form})

class CustomLoginView(LoginView):
    def dispatch(self, request, *args, **kwargs):
        if not request.GET.get('user_type'):
            return redirect('choose-login')
        return super().dispatch(request, *args, **kwargs)
    def form_valid(self, form):
        # Ensure the authenticated user's stored role matches the requested login role.
        user = form.get_user()
        user_type = self.request.POST.get('user_type') or self.request.GET.get('user_type')
        # Allow superuser to login to any role view regardless of stored profile.user_type
        if user_type and hasattr(user, 'profile') and not user.is_superuser and user.profile.user_type != user_type:
            messages.error(self.request, f"Account is registered as {user.profile.user_type}. Did you forget your account or would you like to register a {user_type} account?")
            return redirect('register-role', role=user_type)
        # Proceed with normal login (do not overwrite stored profile.user_type on login)
        return super().form_valid(form)

def choose_login(request):
    roles = LoginRole.objects.all()
    return render(request, 'users/login.html', {'roles': roles})


def teachers(request):
    # Blank page for teachers section — placeholder template
    return render(request, 'users/teachers.html')

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
            # If profile was changed to non-student, ensure grade and courses are cleared
            if request.user.profile.user_type != 'student':
                request.user.profile.grade = ''
                try:
                    request.user.profile.courses.clear()
                except Exception:
                    pass
                request.user.profile.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    # Determine courses the user has activity in (fallback since there's no enrollment model)
    courses = Course.objects.filter(lessons__tasks__completedtask__user=request.user).distinct()
    # Social metrics (from Profile.following / Profile.followers)
    followers_count = request.user.profile.followers.count()
    following_count = request.user.profile.following.count()
    achievements = []
    friend_streak = 0
    joined = request.user.date_joined

    # Users list for add-friend UI with optional search
    q = request.GET.get('q', '').strip()
    if q:
        all_users = User.objects.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)).exclude(pk=request.user.pk)
    else:
        all_users = User.objects.exclude(pk=request.user.pk)[:50]

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'courses': courses,
        'followers_count': followers_count,
        'following_count': following_count,
        'achievements': achievements,
        'friend_streak': friend_streak,
        'joined': joined,
        'all_users': all_users,
        'search_query': q,
    }
    # Pending requests for current user
    pending_friend_requests = FriendRequest.objects.filter(to_user=request.user)
    pending_streak_requests = StreakRequest.objects.filter(to_user=request.user)
    context['pending_friend_requests'] = pending_friend_requests
    context['pending_streak_requests'] = pending_streak_requests
    return render(request, 'users/profile.html', context)


@login_required
def send_friend_request(request, username):
    if request.method != 'POST':
        return redirect('profile')
    to_user = get_object_or_404(User, username=username)
    if to_user == request.user:
        return redirect('profile')
    # don't duplicate requests or friendships
    exists = FriendRequest.objects.filter(from_user=request.user, to_user=to_user).exists()
    already_friends = Friendship.objects.filter(
        models.Q(user1=request.user, user2=to_user) | models.Q(user1=to_user, user2=request.user)
    ).exists()
    if not exists and not already_friends:
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        messages.success(request, f'Friend request sent to {to_user.username}')
    return redirect(request.META.get('HTTP_REFERER') or 'profile')


@login_required
def accept_friend_request(request, request_id):
    fr = get_object_or_404(FriendRequest, pk=request_id)
    if fr.to_user != request.user:
        return redirect('profile')
    # create friendship record; order users by id to keep unique constraint consistent
    u1, u2 = (fr.from_user, fr.to_user) if fr.from_user.id < fr.to_user.id else (fr.to_user, fr.from_user)
    Friendship.objects.get_or_create(user1=u1, user2=u2)
    fr.delete()
    messages.success(request, f'You are now friends with {u2.username}')
    return redirect('profile')


@login_required
def send_streak_request(request, username):
    if request.method != 'POST':
        return redirect('profile')
    to_user = get_object_or_404(User, username=username)
    if to_user == request.user:
        return redirect('profile')
    # must be friends first
    friendship = Friendship.objects.filter(
        models.Q(user1=request.user, user2=to_user) | models.Q(user1=to_user, user2=request.user)
    ).first()
    if not friendship:
        messages.error(request, 'You must be friends before starting a streak.')
        return redirect(request.META.get('HTTP_REFERER') or 'profile')
    # don't duplicate streak requests
    exists = StreakRequest.objects.filter(from_user=request.user, to_user=to_user).exists()
    if not exists:
        StreakRequest.objects.create(from_user=request.user, to_user=to_user)
        messages.success(request, f'Streak request sent to {to_user.username}')
    return redirect(request.META.get('HTTP_REFERER') or 'profile')


@login_required
def accept_streak_request(request, request_id):
    sr = get_object_or_404(StreakRequest, pk=request_id)
    if sr.to_user != request.user:
        return redirect('profile')
    # find friendship and activate streak
    friendship = Friendship.objects.filter(
        models.Q(user1=sr.from_user, user2=sr.to_user) | models.Q(user1=sr.to_user, user2=sr.from_user)
    ).first()
    if friendship:
        friendship.streak_active = True
        friendship.streak_started_at = timezone.now()
        friendship.save()
    sr.delete()
    messages.success(request, 'Friend streak started!')
    return redirect('profile')


@login_required
def user_profile(request, username):
    # Public (read-only) view of another user's profile. Only show limited actions.
    user_obj = get_object_or_404(User, username=username)
    if user_obj == request.user:
        # Redirect to own editable profile
        return redirect('profile')

    # Gather similar context but read-only
    courses = Course.objects.filter(lessons__tasks__completedtask__user=user_obj).distinct()
    followers_count = user_obj.profile.followers.count()
    following_count = user_obj.profile.following.count()
    achievements = []
    friend_streak = 0
    joined = user_obj.date_joined

    is_following = False
    is_friend = False
    sent_friend_request = False
    received_friend_request = None
    sent_streak_request = False
    received_streak_request = None
    if request.user.is_authenticated:
        is_following = request.user.profile.following.filter(pk=user_obj.profile.pk).exists()
        # friendship
        is_friend = Friendship.objects.filter(
            Q(user1=request.user, user2=user_obj) | Q(user1=user_obj, user2=request.user)
        ).exists()
        sent_friend_request = FriendRequest.objects.filter(from_user=request.user, to_user=user_obj).exists()
        received_friend_request = FriendRequest.objects.filter(from_user=user_obj, to_user=request.user).first()
        sent_streak_request = StreakRequest.objects.filter(from_user=request.user, to_user=user_obj).exists()
        received_streak_request = StreakRequest.objects.filter(from_user=user_obj, to_user=request.user).first()

    context = {
        'view_user': user_obj,
        'courses': courses,
        'followers_count': followers_count,
        'following_count': following_count,
        'achievements': achievements,
        'friend_streak': friend_streak,
        'joined': joined,
        'is_following': is_following,
        'is_friend': is_friend,
        'sent_friend_request': sent_friend_request,
        'received_friend_request': received_friend_request,
        'sent_streak_request': sent_streak_request,
        'received_streak_request': received_streak_request,
    }
    return render(request, 'users/user_profile.html', context)


@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        return redirect('profile')
    profile = request.user.profile
    target_profile = target_user.profile
    if target_profile in profile.following.all():
        profile.following.remove(target_profile)
    else:
        profile.following.add(target_profile)
    return redirect(request.META.get('HTTP_REFERER') or 'profile')


@login_required
def following_list(request):
    following_profiles = request.user.profile.following.all()
    context = {'following_profiles': following_profiles}
    return render(request, 'users/following_list.html', context)

def custom_logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect('/')
    return render(request, 'users/logout_confirm.html')