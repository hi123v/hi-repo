from django.shortcuts import render
from .models import Post

posts = [
    {
        'author': 'George patterson',
        'title': 'how to stop you kids from whatching to much T.V.',
        'content': 'If you have not let your kids whatch T.V. before you will have it easier because they do not know what it is so just do not show it to them',
        'date_posted': 'October 13, 2024'
    },
    {
        'author': 'George patterson',
        'title': 'how to stop you kids from whatching to much T.V.',
        'content': 'If they do know what T.v. is than it will be trickier, but not impossible. (1) one trick that helps is to after a nap or sleeping you should not give them T.V, this is mainly for toddlers. (2) for older kids one trick is to teach them the value of playing out side or doing the chores in a way that makes them happy to do it.',
        'date_posted': 'October 13, 2024'
    } 
]


def home(request):
    context = {
        'posts': Post.objects.all
    }
    return render(request, 'blog/home.html', context)



def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})
