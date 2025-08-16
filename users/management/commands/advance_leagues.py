from django.core.management.base import BaseCommand
from users.models import Profile

LEAGUES = [
    'Stone', 'Bronze', 'Silver', 'Gold', 'Emerald',
    'Sapphire', 'Ruby', 'Diamond', 'Amethyst', 'Obsidian'
]

class Command(BaseCommand):
    help = 'Advance top 5 users in each league to the next league'

    def handle(self, *args, **kwargs):
        # Promote top 5
        for i in range(len(LEAGUES) - 1):
            league = LEAGUES[i]
            next_league = LEAGUES[i + 1]
            top_profiles = Profile.objects.filter(league=league).order_by('-points')[:5]
            for profile in top_profiles:
                profile.league = next_league
                profile.save()
        # Demote bottom 5 (skip Stone league)
        for i in range(1, len(LEAGUES)):
            league = LEAGUES[i]
            prev_league = LEAGUES[i - 1]
            bottom_profiles = Profile.objects.filter(league=league).order_by('points')[:5]
            for profile in bottom_profiles:
                profile.league = prev_league
                profile.save()
        self.stdout.write(self.style.SUCCESS('Leagues advanced and demoted!'))