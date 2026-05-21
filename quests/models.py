from blog import models as blog_models


class QuestPage(blog_models.QuestPage):
    class Meta:
        proxy = True
        app_label = 'quests'
        verbose_name = 'Quest Page'
        verbose_name_plural = 'Quest Pages'


class QuestCategory(blog_models.QuestCategory):
    class Meta:
        proxy = True
        app_label = 'quests'
        verbose_name = 'Quest Category'
        verbose_name_plural = 'Quest Categories'


class Quest(blog_models.Quest):
    class Meta:
        proxy = True
        app_label = 'quests'
        verbose_name = 'Quest'
        verbose_name_plural = 'Quests'


class CompletedQuest(blog_models.CompletedQuest):
    class Meta:
        proxy = True
        app_label = 'quests'
        verbose_name = 'Completed Quest'
        verbose_name_plural = 'Completed Quests'
