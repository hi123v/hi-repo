from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.core.exceptions import ObjectDoesNotExist



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