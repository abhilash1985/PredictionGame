from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Deprecated: use seed_wc2026 instead'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('seed_wc2026_demo is deprecated; running seed_wc2026...'))
        call_command('seed_wc2026', clear_matches=True)
