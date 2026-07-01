from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from datetime import timedelta
import uuid



LEAGUE_CHOICES = [
    ('Stone', 'Stone'),
    ('Bronze', 'Bronze'),
    ('Silver', 'Silver'),
    ('Gold', 'Gold'),
    ('Emerald', 'Emerald'),
    ('Sapphire', 'Sapphire'),
    ('Ruby', 'Ruby'),
    ('Diamond', 'Diamond'),
    ('Amethyst', 'Amethyst'),
    ('Obsidian', 'Obsidian'),
]

class Profile(models.Model):
    USER_TYPES = (
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics', blank=True, null=True)
    sprite = models.ImageField(upload_to='sprites/', blank=True, null=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='student')
    grade = models.CharField(max_length=20, blank=True, null=True)
    points = models.IntegerField(default=0) 
    league = models.CharField(max_length=20, choices=LEAGUE_CHOICES, default='Stone')
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    courses = models.ManyToManyField('blog.Course', related_name='subscribed_profiles', blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        if not self.image:
            try:
                settings = SiteSettings.objects.first()
                if settings and settings.default_profile_image:
                    self.image = settings.default_profile_image
            except ObjectDoesNotExist:
                pass
        super().save(*args, **kwargs)
        if self.image and hasattr(self.image, 'path'):
            try:
                img = Image.open(self.image.path)
            except (FileNotFoundError, OSError):
                return
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.image.path)

class StudentLoginCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent_email = models.EmailField()
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

class LoginRole(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
        ('student', 'Student'),
    ]
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    image = models.ImageField(upload_to='login_roles/')
    # Optionally add a description or other fields

    def __str__(self):
        return self.get_name_display()

class SiteSettings(models.Model):
    default_profile_image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return "Site Settings"


class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"FriendRequest from {self.from_user} to {self.to_user}"


class Friendship(models.Model):
    user1 = models.ForeignKey(User, related_name='friendships_initiated', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friendships_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    streak_active = models.BooleanField(default=False)
    streak_started_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = (('user1', 'user2'),)

    def __str__(self):
        return f"Friendship: {self.user1} <-> {self.user2}"


class StreakRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_streak_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_streak_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"StreakRequest from {self.from_user} to {self.to_user}"


class TeacherStudent(models.Model):
    teacher = models.ForeignKey(User, related_name='teacher_students', on_delete=models.CASCADE)
    student = models.ForeignKey(User, related_name='student_teachers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = (('teacher', 'student'),)

    def __str__(self):
        return f"{self.teacher.username} -> {self.student.username}"


class TeacherInvite(models.Model):
    teacher = models.ForeignKey(User, related_name='sent_teacher_invites', on_delete=models.CASCADE)
    student = models.ForeignKey(User, related_name='received_teacher_invites', on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=1)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite {self.teacher.username} -> {self.student.username} (accepted={self.accepted})"


class TeacherAction(models.Model):
    class ActionType(models.TextChoices):
        POINTS = 'points', 'Points'
        MEDAL = 'medal', 'Medal'
        EMOJI = 'emoji', 'Emoji'

    class MedalChoices(models.TextChoices):
        BRONZE = 'bronze', 'Bronze'
        SILVER = 'silver', 'Silver'
        GOLD = 'gold', 'Gold'

    class EmojiChoices(models.TextChoices):
        HAPPY = 'happy', 'Happy Face'
        THUMBS = 'thumbs', 'Thumbs Up'
        CONFETTI = 'confetti', 'Confetti'

    teacher = models.ForeignKey(User, related_name='teacher_actions', on_delete=models.CASCADE)
    student = models.ForeignKey(User, related_name='student_actions', on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    points_delta = models.IntegerField(default=0)
    medal = models.CharField(max_length=20, choices=MedalChoices.choices, blank=True, null=True)
    emoji = models.CharField(max_length=20, choices=EmojiChoices.choices, blank=True, null=True)
    message = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} by {self.teacher.username} -> {self.student.username}"


class TeacherCourse(models.Model):
    """Associate a Course with a teacher (teachers 'add' classes to their dashboard)."""
    teacher = models.ForeignKey(User, related_name='teacher_courses', on_delete=models.CASCADE)
    course = models.ForeignKey('blog.Course', related_name='teacher_owners', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('teacher', 'course'),)

    def __str__(self):
        return f"{self.teacher.username} -> {self.course.name}"