from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm 


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('Your account has been created! You are now able tolog in')
            messages.success(request, f'your ')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'user/register.html', {'form': form})

 