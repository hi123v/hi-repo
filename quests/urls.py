from django.urls import path
from . import views

urlpatterns = [
    path('', views.quests, name='quests'),
    path('<int:quest_id>/complete/', views.complete_quest, name='quest-complete'),
]
