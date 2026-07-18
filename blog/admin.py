from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.db import models
from .models import Post, Course, Lesson, LessonPreset, Task, Grade, SiteSectionItem, Game, Mission, Team, Career, Contact, FAQ
from .models import GameAsset


class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'overlay_preview')
    fields = ('name', 'image', 'description', 'overlay_items', 'overlay_color', 'overlay_3d')
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 6, 'cols': 60})},
    }

    def overlay_preview(self, obj):
        # Render a tiny preview using the course image (if any) and the first overlay item
        if not obj:
            return '(no preview)'
        bg = ''
        if getattr(obj, 'image', None):
            try:
                bg = obj.image.url
            except Exception:
                bg = ''
        items = obj.overlay_items_list() if hasattr(obj, 'overlay_items_list') else []
        sample = items[0] if items else ''
        color = obj.overlay_color if getattr(obj, 'overlay_color', None) else 'blue'
        style = f"background: url('{bg}') center/cover no-repeat; width:160px; height:88px; display:inline-block; border-radius:6px; border:1px solid #ddd; position:relative;"
        overlay_style = f"position:absolute; left:8px; bottom:6px; font-weight:700; color:{'white' if bg else color}; text-shadow:0 2px 6px rgba(0,0,0,0.4);"
        return format_html('<div style="{}"><span style="{}">{}</span></div>', style, overlay_style, sample)

    overlay_preview.short_description = 'Preview'


admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson)
admin.site.register(LessonPreset)
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
    list_display = ('name', 'template_name', 'out_of_order', 'created_at', 'launch_link')
    list_editable = ('out_of_order',)
    fields = ('name', 'description', 'template_name', 'out_of_order', 'preview')
    readonly_fields = ('launch_link', 'preview')
    inlines = []

    def launch_link(self, obj):
        if not obj or not obj.template_name or obj.template_name == 'none':
            return '(no template)'
        href = obj.get_launch_url()
        if not href:
            return '(no frontend mapping)'
        return format_html('<a href="{}" target="_blank">Open template</a>', href)

    launch_link.short_description = 'Preview'

    def preview(self, obj):
        """Render a small iframe preview of the selected game template (when available)."""
        if not obj or not obj.template_name or obj.template_name == 'none':
            return '(no template configured)'
        href = obj.get_launch_url()
        if not href:
            return '(unable to resolve preview)'
        # Use a fixed small iframe so admin stays usable
        return format_html('<div style="max-width:420px;"><iframe src="{}" style="width:400px;height:260px;border:1px solid #ddd;border-radius:6px"></iframe></div>', href)

    preview.short_description = 'Template Preview'


admin.site.register(Game, GameAdmin)


# Admin for game assets (items and grounds)
class GameAssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_type', 'game', 'created_at', 'thumb')
    list_filter = ('asset_type', 'game')
    fields = ('game', 'name', 'asset_type', 'image')

    def thumb(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="width:80px;height:48px;object-fit:cover;border-radius:4px"/>', obj.image.url)
        return '(no image)'

    thumb.short_description = 'Preview'


admin.site.register(GameAsset, GameAssetAdmin)


class GameAssetInline(admin.TabularInline):
    model = GameAsset
    fields = ('name', 'asset_type', 'image', 'thumb')
    readonly_fields = ('thumb',)
    extra = 1
    def thumb(self, obj):
        if obj and getattr(obj, 'image', None):
            return format_html('<img src="{}" style="width:120px;height:72px;object-fit:cover;border-radius:4px"/>', obj.image.url)
        return '(no image)'

    thumb.short_description = 'Preview'


# attach inline to GameAdmin so assets can be managed directly when editing a Game
GameAdmin.inlines = [GameAssetInline]


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