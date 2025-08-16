from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Profile
import random

LEAGUES = [
    'Stone', 'Bronze', 'Silver', 'Gold', 'Emerald',
    'Sapphire', 'Ruby', 'Diamond', 'Amethyst', 'Obsidian'
]

class Command(BaseCommand):
    help = 'Generate random users with random points and leagues for testing'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=50, help='Number of users to create')

    def handle(self, *args, **options):
        count = options['count']
        for i in range(count):
            username = f'testuser_{random.randint(10000, 99999)}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, password='testpass')
                league = random.choice(LEAGUES)
                points = random.randint(0, 500)
                profile = user.profile
                profile.league = league
                profile.points = points
                profile.save()
        self.stdout.write(self.style.SUCCESS(f'Created {count} random users!'))