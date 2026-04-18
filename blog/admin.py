from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.db import models
from .models import Post, Course, Lesson, Task, Grade, SiteSectionItem, Game, Mission, Team, Career, Contact, FAQ


class CourseAdmin(admin.ModelAdmin):
    list_display = ('name',)
    fields = ('name', 'image', 'description')


admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson)
admin.site.register(Grade)


class TaskAdmin(admin.ModelAdmin):
    readonly_fields = ('task_template',)
    fields = ('lesson', 'name', 'template_type', 'template_data', 'task_template')
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 6, 'cols': 60})},
    }

    def task_template(self, obj):
        return format_html(
            '<div style="border:2px dashed #ccc; padding:12px; background:#fafafa;">'
            '<strong>Task Template</strong><br>'
            'Placeholder area for lesson backbone structure. Add template components here later.'
            '</div>'
        )

    task_template.short_description = 'Task Template (placeholder)'


admin.site.register(Task, TaskAdmin)


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date_posted')
    list_filter = ('author', 'date_posted')
    search_fields = ('title', 'content')


admin.site.register(Post, PostAdmin)


# Admin for simple Game entries
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    fields = ('name', 'description')


admin.site.register(Game, GameAdmin)


# Generic admin for proxy section models (Mission, Team, Career, Contact, FAQ)
class ProxySectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_current', 'created_at')
    fields = ('title', 'description', 'is_current')

    # subclasses must set this to the section constant from SiteSectionItem
    section_value = None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(section=self.section_value)

    def save_model(self, request, obj, form, change):
        obj.section = self.section_value
        super().save_model(request, obj, form, change)


class MissionAdmin(ProxySectionAdmin):
    section_value = SiteSectionItem.SECTION_MISSION


class TeamAdmin(ProxySectionAdmin):
    section_value = SiteSectionItem.SECTION_TEAM


class CareerAdmin(ProxySectionAdmin):
    section_value = SiteSectionItem.SECTION_CAREER


class ContactAdmin(ProxySectionAdmin):
    section_value = SiteSectionItem.SECTION_CONTACT


class FAQAdmin(ProxySectionAdmin):
    section_value = SiteSectionItem.SECTION_FAQ


admin.site.register(Mission, MissionAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Career, CareerAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(FAQ, FAQAdmin)

# Customize Django admin site headers to match site name
from django.contrib import admin as _admin
_admin.site.site_header = 'Quest-ly Administration'
_admin.site.site_title = 'Quest-ly Admin'
_admin.site.index_title = 'Quest-ly Site Admin'