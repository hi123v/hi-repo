from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from blog.models import QuestPage, QuestCategory, Quest, CompletedQuest


def quests(request):
    page = QuestPage.objects.first()
    categories = QuestCategory.objects.prefetch_related('quests').all()

    completed_ids = set()
    if request.user.is_authenticated:
        completed_ids = set(CompletedQuest.objects.filter(user=request.user).values_list('quest_id', flat=True))

    return render(request, 'quests/quests.html', {
        'title': 'Quests',
        'page': page,
        'categories': categories,
        'completed_ids': completed_ids,
    })


@login_required
def complete_quest(request, quest_id):
    quest = get_object_or_404(Quest, pk=quest_id, is_active=True)
    if CompletedQuest.objects.filter(user=request.user, quest=quest).exists():
        messages.info(request, 'You have already completed this quest.')
        return redirect('quests')

    CompletedQuest.objects.create(user=request.user, quest=quest)
    try:
        profile = request.user.profile
        profile.points += quest.points_reward
        profile.save()
    except Exception:
        pass
    messages.success(request, f"You earned {quest.points_reward} points!")
    return redirect('quests')
