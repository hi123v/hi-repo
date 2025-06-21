from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'user_type']

class StudentLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    parent_email = forms.EmailField(label="Parent's Email")

from django import forms

class PlacementQuizForm(forms.Form):
    question_1 = forms.ChoiceField(
        choices=[('a', '2'), ('b', '4'), ('c', '6')],
        widget=forms.RadioSelect,
        label="What is 2 + 2?"
    )
    question_2 = forms.ChoiceField(
        choices=[('a', 'Dog'), ('b', 'Cat'), ('c', 'Fish')],
        widget=forms.RadioSelect,
        label="Which is a mammal?"
    )

class TeacherLoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)