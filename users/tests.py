from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from blog.models import Course, LessonPreset
from .models import Profile, TeacherCourse


class ClassAnalyticsViewTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='secret123')
        Profile.objects.create(user=self.teacher, user_type='teacher')
        self.course = Course.objects.create(name='Math 101', description='Intro math')
        TeacherCourse.objects.create(teacher=self.teacher, course=self.course)

    def test_class_analytics_renders_for_teacher(self):
        self.client.login(username='teacher', password='secret123')
        response = self.client.get(reverse('class-analytics', kwargs={'course_id': self.course.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analytics - Math 101')
        self.assertContains(response, 'Class overview')

    def test_add_class_succeeds_when_teacher_profile_is_missing(self):
        self.teacher.profile.delete()
        self.client.login(username='teacher', password='secret123')

        response = self.client.post(reverse('add-class'), {
            'name': 'New Class',
            'subject': 'Math',
            'grade': '1st Grade',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(name='New Class').exists())
        self.assertTrue(TeacherCourse.objects.filter(teacher=self.teacher, course__name='New Class').exists())

    def test_class_dashboard_shows_add_lessons_and_teacher_tools(self):
        self.client.login(username='teacher', password='secret123')

        response = self.client.get(reverse('class-dashboard', kwargs={'course_id': self.course.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add lessons')
        self.assertContains(response, 'Teacher Lessons')
        self.assertContains(response, 'Lesson Planner')
        self.assertContains(response, 'Calendar')
        self.assertContains(response, 'Parents List')

    def test_class_task_manager_can_auto_fill_lessons_from_preset(self):
        self.client.login(username='teacher', password='secret123')
        preset = LessonPreset.objects.create(name='Pre-K Life Skills', lesson_titles='Morning Circle\nStory Time')

        response = self.client.post(reverse('class-tasks', kwargs={'course_id': self.course.pk}), {
            'action': 'auto_fill',
            'preset_ids': [preset.pk],
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.course.lessons.filter(name='Morning Circle').exists())
        self.assertTrue(self.course.lessons.filter(name='Story Time').exists())
