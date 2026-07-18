from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, StudentLoginForm, PlacementQuizForm, TeacherLoginForm
from .models import StudentLoginCode, Profile, LoginRole
from .models import FriendRequest, Friendship, StreakRequest, TeacherInvite, TeacherStudent, TeacherAction, TeacherCourse
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import models
from collections import defaultdict
from blog.models import Course, Grade as GradeModel, Lesson, LessonPreset, Task, CompletedTask
from blog.forms import LessonForm
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from django.utils.dateformat import format as df_format
from datetime import datetime

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
                        return redirect('teachers')
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
        if user_type and hasattr(user, 'profile') and not user.is_superuser and user.profile.user_type != user_type:
            messages.error(self.request, f"Account is registered as {user.profile.user_type}. Did you forget your account or would you like to register a {user_type} account?")
            return redirect('register-role', role=user_type)

        response = super().form_valid(form)

        # Preserve explicit next redirects.
        if self.request.GET.get('next') or self.request.POST.get('next'):
            return response

        try:
            if hasattr(user, 'profile') and not user.is_superuser:
                if user.profile.user_type == 'teacher':
                    return redirect('teachers')
                if user.profile.user_type == 'student':
                    return redirect('students')
                if user.profile.user_type == 'parent':
                    return redirect('parents')
        except Exception:
            pass
        return response

def choose_login(request):
    roles = LoginRole.objects.all()
    return render(request, 'users/login.html', {'roles': roles})


def re_register(request, role):
    """Allow a user to 're-register' into a different role by proving
    ownership of an existing account (same username, email, and password).
    This does not remove superuser privileges; superusers keep their access.
    """
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        # Authenticate credentials
        user_obj = authenticate(request, username=username, password=password)
        if user_obj is None:
            error = 'Invalid username or password.'
        else:
            # Verify email matches
            if (user_obj.email or '').strip().lower() != (email or '').strip().lower():
                error = 'Email does not match our records for that account.'
            else:
                # If superuser, do not change role/profile; just log them in and redirect
                if user_obj.is_superuser:
                    login(request, user_obj)
                    return redirect('teachers' if role == 'teacher' else 'home')
                # Update profile role
                try:
                    if not hasattr(user_obj, 'profile'):
                        Profile.objects.create(user=user_obj, user_type=role)
                    else:
                        user_obj.profile.user_type = role
                        # If switching away from student, clear grade/courses
                        if role != 'student':
                            user_obj.profile.grade = ''
                            try:
                                user_obj.profile.courses.clear()
                            except Exception:
                                pass
                        user_obj.profile.save()
                except Exception:
                    error = 'Unable to update account role; please contact an administrator.'
                if not error:
                    # Log the user in and redirect to appropriate page
                    login(request, user_obj)
                    if role == 'teacher':
                        return redirect('teachers')
                    return redirect('home')
    return render(request, 'users/re_register.html', {'role': role, 'error': error})


@login_required
def teachers(request):
    # Only allow teachers to view this page. Show role-swap suggestion to others.
    try:
        # Allow superusers to access teacher page as well
        if not (getattr(request.user, 'is_superuser', False) or (hasattr(request.user, 'profile') and request.user.profile.user_type == 'teacher')):
            return render(request, 'users/role_forbidden.html', {
                'target_role': 'teacher',
                'suggest_register_url': '/register/teacher/'
            })
    except Exception:
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'teacher',
            'suggest_register_url': '/register/teacher/'
        })
    # Provide teacher-specific context: accepted students and pending invites
    students = []
    pending_invites = []
    all_courses = []
    teacher_courses = []
    try:
        students = [rel.student for rel in TeacherStudent.objects.filter(teacher=request.user, accepted=True).select_related('student')]
        pending_invites = TeacherInvite.objects.filter(teacher=request.user, accepted=False)
        all_courses = Course.objects.all()
        teacher_courses = [tc.course for tc in TeacherCourse.objects.filter(teacher=request.user).select_related('course')]
    except Exception:
        students = []
        pending_invites = []
        all_courses = []
        teacher_courses = []
    pending_token = request.GET.get('pending_invite')
    return render(request, 'users/teachers.html', {
        'students': students,
        'pending_invites': pending_invites,
        'all_courses': all_courses,
        'teacher_courses': teacher_courses,
        'pending_invite': pending_token
    })


@login_required
def add_student(request):
    if request.method != 'POST':
        return redirect('teachers')
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    email = request.POST.get('email', '').strip()
    # optional course id to redirect back to class students page
    course_id = request.POST.get('course_id') or request.GET.get('course_id')
    if not username or not password or not email:
        messages.error(request, 'Username, password and email are required.')
        if course_id:
            return redirect('class-students', course_id=course_id)
        return redirect('teachers')
    # Find or create the student user
    user_obj, created = User.objects.get_or_create(username=username, defaults={'email': email})
    if created:
        user_obj.set_password(password)
        user_obj.email = email
        user_obj.save()
        # ensure profile exists and is student
        try:
            if not hasattr(user_obj, 'profile'):
                Profile.objects.create(user=user_obj, user_type='student')
            else:
                user_obj.profile.user_type = 'student'
                user_obj.profile.save()
        except Exception:
            pass
    # Create invite
    try:
        # Avoid duplicate pending invites
        existing = TeacherInvite.objects.filter(teacher=request.user, student=user_obj, accepted=False).first()
        if existing and not existing.is_expired():
            messages.info(request, 'An invite is already pending for that student.')
            if course_id:
                return redirect('class-students', course_id=course_id)
            return redirect('teachers')
        invite = TeacherInvite.objects.create(teacher=request.user, student=user_obj)
        messages.success(request, f'Invite sent to {user_obj.username}. They have 1 minute to accept.')
        # Redirect to teachers view with pending token so teacher sees loading state
        target = f"{reverse('teachers')}?pending_invite={invite.token}"
        if course_id:
            # send teacher back to class students page instead
            return redirect('class-students', course_id=course_id)
        return redirect(target)
    except Exception:
        messages.error(request, 'Unable to create invite; contact admin.')
    return redirect('teachers')


def ensure_user_profile(user, user_type=None):
    try:
        profile, _ = Profile.objects.get_or_create(user=user)
        if user_type and profile.user_type != user_type:
            profile.user_type = user_type
            profile.save(update_fields=['user_type'])
        return profile
    except Exception:
        return None


def is_teacher(user):
    # Treat superusers as teachers as well
    if getattr(user, 'is_superuser', False):
        return True
    try:
        profile = ensure_user_profile(user, user_type='teacher')
        return bool(profile and profile.user_type == 'teacher')
    except Exception:
        return False


@login_required
def add_class(request):
    if request.method != 'POST':
        return redirect('teachers')
    name = request.POST.get('name', '').strip()
    subject = request.POST.get('subject', '').strip()
    grade = request.POST.get('grade', '').strip()
    if not subject or not grade:
        messages.error(request, 'Subject and grade are required.')
        return redirect('teachers')
    ensure_user_profile(request.user)
    # create a Course entry to represent the class
    description = f'{grade} • {subject}'
    course_name = name or f'{grade} {subject}'
    course = Course.objects.create(name=course_name, description=description)
    # associate to teacher
    TeacherCourse.objects.get_or_create(teacher=request.user, course=course)
    messages.success(request, f'Class "{course.name}" created.')
    return redirect('class-dashboard', course_id=course.id)


@login_required
@user_passes_test(is_teacher)
def class_dashboard(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    students = [rel.student for rel in TeacherStudent.objects.filter(teacher=request.user, accepted=True, student__profile__courses=course).select_related('student')]
    lesson_count = course.lessons.count()
    task_count = Task.objects.filter(lesson__course=course).count()
    presets = LessonPreset.objects.all()
    return render(request, 'users/class_dashboard.html', {
        'course': course,
        'students': students,
        'lesson_count': lesson_count,
        'task_count': task_count,
        'presets': presets,
    })


@login_required
@user_passes_test(is_teacher)
def class_students(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    # ensure teacher has added this class
    if not TeacherCourse.objects.filter(teacher=request.user, course=course).exists():
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'teacher',
            'suggest_register_url': '/register/teacher/'
        })
    if request.method == 'POST':
        # delegate to add_student logic but stay on this page
        # extract fields and create invite
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        if not username or not password or not email:
            messages.error(request, 'Username, password and email are required.')
            return redirect('class-students', course_id=course_id)
        user_obj, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user_obj.set_password(password)
            user_obj.email = email
            user_obj.save()
            try:
                if not hasattr(user_obj, 'profile'):
                    Profile.objects.create(user=user_obj, user_type='student')
                else:
                    user_obj.profile.user_type = 'student'
                    user_obj.profile.save()
            except Exception:
                pass
        try:
            existing = TeacherInvite.objects.filter(teacher=request.user, student=user_obj, accepted=False).first()
            if existing and not existing.is_expired():
                messages.info(request, 'An invite is already pending for that student.')
                return redirect('class-students', course_id=course_id)
            invite = TeacherInvite.objects.create(teacher=request.user, student=user_obj)
            messages.success(request, f'Invite sent to {user_obj.username}. They have 1 minute to accept.')
            return redirect('class-students', course_id=course_id)
        except Exception:
            messages.error(request, 'Unable to create invite; contact admin.')
            return redirect('class-students', course_id=course_id)
    # GET: show students for this teacher who are enrolled in this course
    students_qs = TeacherStudent.objects.filter(teacher=request.user, accepted=True, student__profile__courses=course).select_related('student')
    students = [rel.student for rel in students_qs]
    pending_invites = TeacherInvite.objects.filter(teacher=request.user, accepted=False)
    return render(request, 'users/class_students.html', {'course': course, 'students': students, 'pending_invites': pending_invites})


@login_required
@user_passes_test(is_teacher)
def class_analytics(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    return render(request, 'users/class_analytics.html', {'course': course})


@login_required
@user_passes_test(is_teacher)
def class_profile_page(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    students = [rel.student for rel in TeacherStudent.objects.filter(teacher=request.user, accepted=True, student__profile__courses=course).select_related('student')]
    student_count = len(students)
    grade_values = []
    for student in students:
        grade_value = None
        try:
            grade_text = getattr(student.profile, 'grade', '') or ''
            digits = ''.join(ch for ch in grade_text if ch.isdigit())
            if digits:
                grade_value = int(digits)
            elif grade_text.lower().startswith('prek') or grade_text.lower().startswith('pre-k'):
                grade_value = 0
            elif grade_text.lower().startswith('k'):
                grade_value = 0
        except Exception:
            pass
        if grade_value is not None:
            grade_values.append(grade_value)
    average_grade_level = round(sum(grade_values) / len(grade_values), 1) if grade_values else 0
    lessons = course.lessons.count()
    weekly_goal = max(1, student_count) * 2
    monthly_goal = weekly_goal * 4
    return render(request, 'users/class_profile.html', {
        'course': course,
        'students': students,
        'student_count': student_count,
        'average_grade_level': average_grade_level,
        'lesson_count': lessons,
        'lessons_per_student_per_day': round(lessons / max(student_count, 1), 2) if student_count else 0,
        'lessons_per_student_per_week': round((lessons / max(student_count, 1)) * 7, 2) if student_count else 0,
        'lessons_per_student_per_month': round((lessons / max(student_count, 1)) * 30, 2) if student_count else 0,
        'weekly_goal': weekly_goal,
        'monthly_goal': monthly_goal,
    })


@login_required
@user_passes_test(is_teacher)
def class_points_page(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    return render(request, 'users/class_points.html', {'course': course})


@login_required
@user_passes_test(is_teacher)
def class_task_manager(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    # ensure teacher has added this class
    if not TeacherCourse.objects.filter(teacher=request.user, course=course).exists():
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'teacher',
            'suggest_register_url': '/register/teacher/'
        })
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action == 'auto_fill':
            preset_ids = request.POST.getlist('preset_ids')
            created_lessons = []
            for preset in LessonPreset.objects.filter(pk__in=preset_ids):
                for lesson_title in preset.lessons_list():
                    if not Lesson.objects.filter(course=course, name=lesson_title).exists():
                        Lesson.objects.create(course=course, name=lesson_title)
                        created_lessons.append(lesson_title)
            if created_lessons:
                messages.success(request, f'Added {len(created_lessons)} lesson{"s" if len(created_lessons) != 1 else ""} from the selected presets.')
            else:
                messages.info(request, 'Those lessons were already present in this class.')
            return redirect('class-tasks', course_id=course_id)

        lesson_name = request.POST.get('lesson_name', '').strip()
        finish_date_raw = request.POST.get('finish_date', '').strip()
        task_name = request.POST.get('task_name', '').strip()
        template_type = request.POST.get('template_type', 'none')
        template_data = request.POST.get('template_data', '').strip()
        finish_date = None
        if finish_date_raw:
            try:
                finish_date = datetime.fromisoformat(finish_date_raw)
                if timezone.is_naive(finish_date):
                    finish_date = timezone.make_aware(finish_date, timezone.get_current_timezone())
            except ValueError:
                finish_date = None
        if not lesson_name:
            messages.error(request, 'A lesson name is required.')
            return redirect('class-tasks', course_id=course_id)
        try:
            lesson, created = Lesson.objects.get_or_create(
                course=course,
                name=lesson_name,
                defaults={'finish_date': finish_date}
            )
            if finish_date is not None and lesson.finish_date != finish_date:
                lesson.finish_date = finish_date
                lesson.save()
            if task_name:
                Task.objects.create(lesson=lesson, name=task_name, template_type=template_type, template_data=template_data)
                messages.success(request, 'Lesson and task created.')
            else:
                messages.success(request, 'Lesson created.')
        except Exception:
            messages.error(request, 'Unable to create lesson.')
        return redirect('class-tasks', course_id=course_id)
    # GET: show tasks for course
    lessons = course.lessons.prefetch_related('tasks').filter(is_hidden=False).all()
    students = [rel.student for rel in TeacherStudent.objects.filter(teacher=request.user, accepted=True, student__profile__courses=course).select_related('student')]
    presets = LessonPreset.objects.all()
    return render(request, 'users/class_task_manager.html', {'course': course, 'lessons': lessons, 'students': students, 'presets': presets})


@login_required
@user_passes_test(is_teacher)
def class_lesson_planner(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    lessons = list(course.lessons.prefetch_related('tasks').filter(is_hidden=False).all())
    lessons.sort(key=lambda lesson: (lesson.finish_date is None, lesson.finish_date or datetime.max))
    return render(request, 'users/class_lesson_planner.html', {'course': course, 'lessons': lessons})


@login_required
@user_passes_test(is_teacher)
def class_lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, pk=course_id)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    from users.models import TeacherCourse
    if not request.user.is_superuser and not TeacherCourse.objects.filter(teacher=request.user, course=course).exists():
        messages.error(request, 'You do not have permission to view that lesson.')
        return redirect('class-lesson-planner', course_id=course_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_task':
            task_name = request.POST.get('task_name', '').strip()
            template_type = request.POST.get('template_type', 'none')
            template_data = request.POST.get('template_data', '').strip()
            if not task_name:
                messages.error(request, 'A task name is required.')
            else:
                Task.objects.create(lesson=lesson, name=task_name, template_type=template_type, template_data=template_data)
                messages.success(request, f'Task "{task_name}" added to lesson.')
            return redirect('class-lesson-detail', course_id=course_id, lesson_id=lesson_id)

        if action == 'save_lesson':
            form = LessonForm(request.POST, instance=lesson)
            if form.is_valid():
                form.save()
                messages.success(request, 'Lesson details updated.')
                return redirect('class-lesson-detail', course_id=course_id, lesson_id=lesson_id)
            messages.error(request, 'Please fix the errors below.')
    else:
        form = LessonForm(instance=lesson)

    tasks = lesson.tasks.all()
    completed_tasks_qs = CompletedTask.objects.filter(task__in=tasks).select_related('user')
    completions_by_task = defaultdict(list)
    for completed in completed_tasks_qs:
        completions_by_task[completed.task_id].append(completed.user)
    task_rows = [
        {
            'task': task,
            'completed_users': completions_by_task.get(task.id, []),
            'completed_count': len(completions_by_task.get(task.id, [])),
        }
        for task in tasks
    ]

    if request.method == 'POST' and request.POST.get('action') == 'hide_lesson':
        lesson.is_hidden = True
        lesson.save()
        messages.success(request, 'Lesson hidden from the planner.')
        return redirect('class-lesson-planner', course_id=course_id)

    return render(request, 'users/class_lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'form': form,
        'task_rows': task_rows,
    })


@login_required
@user_passes_test(is_teacher)
def class_calendar(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    lessons = course.lessons.all()
    # Provide a simple 7x6 grid days list for the basic calendar view
    days = list(range(1, 43))
    return render(request, 'users/class_calendar.html', {'course': course, 'lessons': lessons, 'days': days})


@login_required
@user_passes_test(is_teacher)
def class_parents(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    students = [rel.student for rel in TeacherStudent.objects.filter(teacher=request.user, accepted=True, student__profile__courses=course).select_related('student')]
    parent_contacts = []
    for student in students:
        try:
            parent_email = StudentLoginCode.objects.filter(user=student).order_by('-created_at').first()
            if parent_email and parent_email.parent_email:
                parent_contacts.append({'student': student, 'parent_email': parent_email.parent_email})
        except Exception:
            continue
    return render(request, 'users/class_parents.html', {'course': course, 'parent_contacts': parent_contacts})


@login_required
@user_passes_test(is_teacher)
def toggle_teacher_class(request, course_id):
    if request.method != 'POST':
        return redirect('teachers')
    course = get_object_or_404(Course, pk=course_id)
    try:
        tc = TeacherCourse.objects.filter(teacher=request.user, course=course).first()
        if tc:
            tc.delete()
            messages.info(request, f'Removed class {course.name} from your dashboard.')
        else:
            TeacherCourse.objects.create(teacher=request.user, course=course)
            messages.success(request, f'Added class {course.name} to your dashboard.')
    except Exception:
        messages.error(request, 'Unable to update classes.')
    return redirect(request.META.get('HTTP_REFERER') or 'teachers')


@login_required
def accept_invite(request, token):
    # Accept an invite from a teacher. Only allow POST to change state.
    if request.method != 'POST':
        return redirect('profile')
    try:
        invite = get_object_or_404(TeacherInvite, token=token)
    except Exception:
        messages.error(request, 'Invite not found.')
        return redirect('profile')
    # Only the invited student may accept
    if invite.student != request.user:
        messages.error(request, 'This invite is not for your account.')
        return redirect('profile')
    if invite.accepted:
        messages.info(request, 'Invite already accepted.')
        return redirect('profile')
    if invite.is_expired():
        messages.error(request, 'Invite has expired.')
        return redirect('profile')
    # mark accepted and create TeacherStudent relation
    invite.accepted = True
    invite.save()
    ts, created = TeacherStudent.objects.get_or_create(teacher=invite.teacher, student=invite.student)
    ts.accepted = True
    ts.accepted_at = timezone.now()
    ts.save()
    messages.success(request, f'You are now connected to teacher {invite.teacher.get_full_name() or invite.teacher.username}.')
    return redirect('profile')


@login_required
def teacher_student_detail(request, username):
    student = get_object_or_404(User, username=username)
    # Ensure caller is a teacher
    try:
        if not is_teacher(request.user):
            return render(request, 'users/role_forbidden.html', {
                'target_role': 'teacher',
                'suggest_register_url': '/register/teacher/'
            })
    except Exception:
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'teacher',
            'suggest_register_url': '/register/teacher/'
        })
    # require existing accepted relation
    rel = TeacherStudent.objects.filter(teacher=request.user, student=student, accepted=True).first()
    if not rel:
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'student',
            'suggest_register_url': '/register/student/'
        })
    # Gather profile info (exclude password)
    profile = student.profile
    friends = Friendship.objects.filter(models.Q(user1=student) | models.Q(user2=student))
    # Quests: try to fetch from quests app if available
    quests = []
    try:
        from quests.models import Quest
        quests = Quest.objects.filter(user=student)
    except Exception:
        quests = []
    actions = TeacherAction.objects.filter(teacher=request.user, student=student).order_by('-created_at')
    medals = actions.filter(action_type=TeacherAction.ActionType.MEDAL)
    emojis = actions.filter(action_type=TeacherAction.ActionType.EMOJI)
    all_courses = Course.objects.all()
    return render(request, 'users/teacher_student_detail.html', {
        'student': student,
        'profile': profile,
        'friends': friends,
        'quests': quests,
        'medals': medals,
        'emojis': emojis,
        'actions': actions,
        'all_courses': all_courses,
    })


@login_required
def teacher_action(request, username):
    # Ensure caller is a teacher
    try:
        if not is_teacher(request.user):
            return render(request, 'users/role_forbidden.html', {
                'target_role': 'teacher',
                'suggest_register_url': '/register/teacher/'
            })
    except Exception:
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'teacher',
            'suggest_register_url': '/register/teacher/'
        })
    if request.method != 'POST':
        return redirect('teacher-student-detail', username=username)
    student = get_object_or_404(User, username=username)
    rel = TeacherStudent.objects.filter(teacher=request.user, student=student, accepted=True).first()
    if not rel:
        messages.error(request, 'You are not connected to that student.')
        return redirect('teachers')
    action_type = request.POST.get('action_type')
    # Points adjustments
    if action_type == 'points':
        delta = int(request.POST.get('delta', '0'))
        TeacherAction.objects.create(teacher=request.user, student=student, action_type=TeacherAction.ActionType.POINTS, points_delta=delta)
        try:
            student.profile.points = max(0, student.profile.points + delta)
            student.profile.save()
        except Exception:
            pass
        messages.success(request, f'Adjusted points by {delta} for {student.username}.')
    elif action_type == 'medal':
        medal = request.POST.get('medal')
        TeacherAction.objects.create(teacher=request.user, student=student, action_type=TeacherAction.ActionType.MEDAL, medal=medal)
        messages.success(request, f'Gave {medal} medal to {student.username}.')
    elif action_type == 'emoji':
        emoji = request.POST.get('emoji')
        TeacherAction.objects.create(teacher=request.user, student=student, action_type=TeacherAction.ActionType.EMOJI, emoji=emoji)
        messages.success(request, f'Sent {emoji} to {student.username}.')
    elif action_type == 'assign_course':
        course_id = request.POST.get('course_id')
        try:
            course = Course.objects.get(pk=int(course_id))
            # toggle membership
            if course in student.profile.courses.all():
                student.profile.courses.remove(course)
                messages.success(request, f'Removed course {course.name} from {student.username}.')
            else:
                student.profile.courses.add(course)
                messages.success(request, f'Assigned course {course.name} to {student.username}.')
        except Exception:
            messages.error(request, 'Invalid course selection.')
    return redirect('teacher-student-detail', username=username)


@login_required
def poll_invites(request):
    # Return pending invites for current user as JSON
    invites = TeacherInvite.objects.filter(student=request.user, accepted=False)
    data = []
    for inv in invites:
        if inv.is_expired():
            continue
        data.append({
            'teacher': inv.teacher.get_full_name() or inv.teacher.username,
            'token': str(inv.token),
            'expires_at': inv.expires_at.isoformat(),
        })
    return JsonResponse({'invites': data})


@login_required
def invite_status(request, token):
    try:
        inv = get_object_or_404(TeacherInvite, token=token)
    except Exception:
        return JsonResponse({'status': 'not_found'})
    if inv.accepted:
        return JsonResponse({'status': 'accepted'})
    if inv.is_expired():
        return JsonResponse({'status': 'expired'})
    return JsonResponse({'status': 'pending'})


@login_required
def decline_invite(request, token):
    if request.method != 'POST':
        return redirect('profile')
    try:
        inv = get_object_or_404(TeacherInvite, token=token)
    except Exception:
        messages.error(request, 'Invite not found.')
        return redirect('profile')
    if inv.student != request.user:
        messages.error(request, 'This invite is not for your account.')
        return redirect('profile')
    # expire the invite
    inv.expires_at = timezone.now()
    inv.save()
    messages.info(request, 'Invite declined.')
    return redirect('profile')

def is_parent(user):
    # Treat superusers as parents as well
    try:
        return getattr(user, 'is_superuser', False) or (hasattr(user, 'profile') and user.profile.user_type == 'parent')
    except Exception:
        return False


def parent_required(view_func):
    """Decorator to restrict access to parent users (superusers allowed)."""
    return login_required(user_passes_test(is_parent)(view_func))


@parent_required
def parents(request):
    # Allow parents to view this page. Superusers can also access.
    try:
        if not (getattr(request.user, 'is_superuser', False) or (hasattr(request.user, 'profile') and request.user.profile.user_type == 'parent')):
            return render(request, 'users/role_forbidden.html', {
                'target_role': 'parent',
                'suggest_register_url': '/register/parent/'
            })
    except Exception:
        return render(request, 'users/role_forbidden.html', {
            'target_role': 'parent',
            'suggest_register_url': '/register/parent/'
        })
    # Provide the same course context as the home/teachers views so parents
    # can manage and view their selected courses.
    courses = []
    try:
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            user_courses = request.user.profile.courses.prefetch_related('lessons__tasks').all()
            if user_courses.exists():
                courses = user_courses
    except Exception:
        courses = []
    return render(request, 'users/parents.html', {'courses': courses})

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
    # Treat superusers as teachers as well
    return getattr(user, 'is_superuser', False) or (hasattr(user, 'profile') and user.profile.user_type == 'teacher')


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
    pending_teacher_invites = TeacherInvite.objects.filter(student=request.user, accepted=False)
    # Teachers the student has accepted
    accepted_teachers_qs = TeacherStudent.objects.filter(student=request.user, accepted=True).select_related('teacher')
    accepted_teachers = [ts.teacher for ts in accepted_teachers_qs]
    context['pending_friend_requests'] = pending_friend_requests
    context['pending_streak_requests'] = pending_streak_requests
    context['pending_teacher_invites'] = pending_teacher_invites
    context['accepted_teachers'] = accepted_teachers
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

    # Prevent cross-role viewing: teachers should not view student pages, and students shouldn't view teacher-only pages.
    try:
        if hasattr(user_obj, 'profile') and hasattr(request.user, 'profile'):
            if user_obj.profile.user_type == 'student' and request.user.profile.user_type == 'teacher':
                return render(request, 'users/role_forbidden.html', {
                    'target_role': 'student',
                    'suggest_register_url': '/register/student/'
                })
            if user_obj.profile.user_type == 'teacher' and request.user.profile.user_type == 'student':
                return render(request, 'users/role_forbidden.html', {
                    'target_role': 'teacher',
                    'suggest_register_url': '/register/teacher/'
                })
    except Exception:
        pass

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