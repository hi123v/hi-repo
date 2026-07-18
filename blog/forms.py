from django import forms
from .models import Course, Lesson, Post

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'image', 'description']


class LessonForm(forms.ModelForm):
    finish_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        }),
        help_text='Set when students should finish this lesson (optional)'
    )
    
    class Meta:
        model = Lesson
        fields = ['name', 'finish_date']


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content']