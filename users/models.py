from django.db import models
from django.contrib.auth.models import User
from PIL import Image

class Profile(models.Model):
    USER_TYPES = (
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('teacher', 'Teacher'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='student')
    grade = models.CharField(max_length=20, blank=True, null=True)  # <-- Add this line

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        img = Image.open(self.image.path)
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