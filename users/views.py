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
from blog.models import Course
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import FriendRequest, Friendship, StreakRequest

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