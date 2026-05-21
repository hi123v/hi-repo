from django.contrib import admin
from .models import QuestPage, QuestCategory, Quest, CompletedQuest


class QuestPageAdmin(admin.ModelAdmin):
    list_display = ('hero_title',)
    fields = ('hero_title', 'hero_text', 'hero_image')


class QuestCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    fields = ('name', 'description', 'order')


class QuestAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'points_reward', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    fields = ('category', 'title', 'description', 'points_reward', 'is_active')


class CompletedQuestAdmin(admin.ModelAdmin):
    list_display = ('user', 'quest', 'completed_at')
    readonly_fields = ('completed_at',)


admin.site.register(QuestPage, QuestPageAdmin)
admin.site.register(QuestCategory, QuestCategoryAdmin)
admin.site.register(Quest, QuestAdmin)
admin.site.register(CompletedQuest, CompletedQuestAdmin)
