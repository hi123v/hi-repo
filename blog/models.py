from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

class Course(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='course_previews/', blank=True, null=True)
    description = models.TextField(blank=True, default='')
    # Overlay items: one per line (characters / places / words) to render on the course background
    overlay_items = models.TextField(blank=True, default='', help_text='Enter one item per line to display on the course background.')
    OVERLAY_COLOR_BLUE = 'blue'
    OVERLAY_COLOR_GREEN = 'green'
    OVERLAY_COLOR_ORANGE = 'orange'
    OVERLAY_COLOR_CHOICES = [
        (OVERLAY_COLOR_BLUE, 'Blue'),
        (OVERLAY_COLOR_GREEN, 'Green'),
        (OVERLAY_COLOR_ORANGE, 'Orange'),
    ]
    overlay_color = models.CharField(max_length=16, choices=OVERLAY_COLOR_CHOICES, default=OVERLAY_COLOR_BLUE)
    # If true, render overlay with a simple 3D/raised effect
    overlay_3d = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('course-detail', kwargs={'pk': self.pk})

    def overlay_items_list(self):
        """Return overlay items as a cleaned list (splits by lines and trims)."""
        if not self.overlay_items:
            return []
        return [line.strip() for line in self.overlay_items.splitlines() if line.strip()]


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
    out_of_order = models.BooleanField(default=False, help_text='Mark game as temporarily unavailable')

    # Allow attaching a template name so admins can choose which frontend template
    GAME_TEMPLATE_CHOICES = [
        ('none', 'None'),
        ('ball_drop', 'Ball Drop'),
        ('number_pop', 'Number Pop'),
    ]
    template_name = models.CharField(max_length=50, choices=GAME_TEMPLATE_CHOICES, default='none')

    def get_launch_url(self):
        """Return the resolved path for launching this game's frontend (if available).

        Returns a URL path string (e.g. '/games/ball-drop/') or None.
        """
        mapping = {
            'ball_drop': 'ball-drop-game',
            'number_pop': 'number-pop-game',
        }
        url_name = mapping.get(self.template_name)
        if not url_name:
            return None
        try:
            from django.urls import reverse
            base = reverse(url_name)
            # Attach this game's id so the frontend/view can detect which Game was launched
            return f"{base}?game={self.pk}"
        except Exception:
            return None


class GameAsset(models.Model):
    ASSET_ITEM = 'item'
    ASSET_GROUND = 'ground'
    ASSET_CHOICES = [
        (ASSET_ITEM, 'Item'),
        (ASSET_GROUND, 'Ground'),
    ]

    game = models.ForeignKey(Game, related_name='assets', on_delete=models.CASCADE, null=True, blank=True,
                             help_text='Optional: associate asset with a specific Game')
    name = models.CharField(max_length=150)
    asset_type = models.CharField(max_length=20, choices=ASSET_CHOICES, default=ASSET_ITEM)
    image = models.ImageField(upload_to='game_assets/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_asset_type_display()}: {self.name}"

    def image_url(self):
        if self.image:
            return self.image.url
        return ''

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


# Quests feature models (kept in blog because migrations created them there)
class QuestPage(models.Model):
    hero_title = models.CharField(max_length=200, default='Quests')
    hero_text = models.TextField(blank=True, default='')
    hero_image = models.ImageField(upload_to='quests/', blank=True, null=True)

    def __str__(self):
        return 'Quest Page Settings'


class QuestCategory(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Quest(models.Model):
    category = models.ForeignKey(QuestCategory, related_name='quests', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    points_reward = models.IntegerField(default=10, help_text='Points awarded when user completes this quest')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class CompletedQuest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'quest')

    def __str__(self):
        return f"{self.user.username} - {self.quest.title}"
