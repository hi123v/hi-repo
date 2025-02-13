from django.db import models

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.title

class Lesson(models.Model):
    title = models.CharField(max_length=200)
    course =  models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)

    def __str__(self):
        return self.title

class Task(models.Model):
    title = models.CharField(max_length=200)
    lesson = models.ForeignKey(Lesson, related_name='tasks', on_delete=models.CASCADE)

    def __str__(self):
        return self.title