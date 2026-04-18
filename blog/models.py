from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

class Course(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='course_previews/', blank=True, null=True)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('course-detail', kwargs={'pk': self.pk})


class Grade(models.Model):
    name = models.CharField(max_length=100, unique=True)
    courses = models.ManyToManyField(Course, related_name='grades', blank=True)

    def __str__(self):
        return self.name

class Lesson(models.Model):
    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('lesson-detail', kwargs={'pk': self.pk})

class Task(models.Model):
    lesson = models.ForeignKey(Lesson, related_name='tasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    TEMPLATE_CHOICES = [
        ('none', 'None'),
        ('reorder', 'Reorder (drag to correct order)'),
        ('random_click', 'Random Click (pick randomized value)'),
        ('placeholder1', 'Placeholder 1'),
        ('placeholder2', 'Placeholder 2'),
    ]
    template_type = models.CharField(max_length=50, choices=TEMPLATE_CHOICES, default='none')
    # Store template-specific data as JSON text (e.g. list of values)
    template_data = models.TextField(blank=True, default='', help_text='Enter one value per line, or a JSON array like ["a","b","c"].')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('task-detail', kwargs={'task_id': self.pk})
    
class CompletedTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'task')

    def __str__(self):
        return f"{self.user.username} completed {self.task.name}"

class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})
    
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class SubTask(models.Model):
    task = models.ForeignKey(Task, related_name='subtasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

class CompletedSubTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subtask = models.ForeignKey(SubTask, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)


# Generic site section items (missions, teams, careers, contact entries, faq entries)
class SiteSectionItem(models.Model):
    SECTION_MISSION = 'mission'
    SECTION_TEAM = 'team'
    SECTION_CAREER = 'career'
    SECTION_CONTACT = 'contact'
    SECTION_FAQ = 'faq'

    SECTION_CHOICES = [
        (SECTION_MISSION, 'Mission'),
        (SECTION_TEAM, 'Team'),
        (SECTION_CAREER, 'Career'),
        (SECTION_CONTACT, 'Contact'),
        (SECTION_FAQ, 'FAQ'),
    ]

    section = models.CharField(max_length=32, choices=SECTION_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    is_current = models.BooleanField(default=False, help_text='Mark this item as the current/active one for this section')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_section_display()}: {self.title}"

    def save(self, *args, **kwargs):
        # If this item is marked current, unset other current items in the same section
        super_save = super(SiteSectionItem, self).save
        if self.is_current:
            # Temporarily save without enforcing uniqueness to have a PK for exclude
            if not self.pk:
                super_save(*args, **kwargs)
            SiteSectionItem.objects.filter(section=self.section).exclude(pk=self.pk).update(is_current=False)
            # Ensure instance is saved with current=True
            super_save(*args, **kwargs)
        else:
            super_save(*args, **kwargs)


# Games model: simple holder for game entries
class Game(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# Proxy models so admin can show separate entries per section (Mission appears as About)
class Mission(SiteSectionItem):
    class Meta:
        proxy = True
        app_label = 'about'
        verbose_name = 'Mission'
        verbose_name_plural = 'Missions'


class Team(SiteSectionItem):
    class Meta:
        proxy = True
        app_label = 'about'
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'


class Career(SiteSectionItem):
    class Meta:
        proxy = True
        app_label = 'about'
        verbose_name = 'Career'
        verbose_name_plural = 'Careers'


class Contact(SiteSectionItem):
    class Meta:
        proxy = True
        app_label = 'about'
        verbose_name = 'Contact'
        verbose_name_plural = 'Contact'


class FAQ(SiteSectionItem):
    class Meta:
        proxy = True
        app_label = 'about'
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'