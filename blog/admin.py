from django.contrib import admin
from .models import Post, Course, Lesson, Task

admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Task)

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date_posted')
    list_filter = ('author', 'date_posted')
    search_fields = ('title', 'content')

admin.site.register(Post, PostAdmin)