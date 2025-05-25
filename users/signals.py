from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile

# --- Existing profile signals ---
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()

# --- Add this for welcome email on login ---
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.conf import settings

@receiver(user_logged_in)
def send_welcome_email(sender, user, request, **kwargs):
    subject = "Welcome back to CoolApp!"
    message = (
        f"Hi {user.username},\n\n"
        "Check out all the cool stuff on the app:\n"
        "- Number Pop Game\n"
        "- Drag and Drop Challenges\n"
        "- More fun features coming soon!\n\n"
        "Thanks for being part of our community!"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )