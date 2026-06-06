from django.core.management.base import BaseCommand

from apps.tournaments.squad_parser import fetch_fifa_teams, sync_wc2026_team_names, write_squads_json


class Command(BaseCommand):
    help = 'Update wc2026 squads and sync FIFA team names from fifa.com'

    def handle(self, *args, **options):
        fifa_teams = fetch_fifa_teams()
        sync_wc2026_team_names(fifa_teams=fifa_teams)
        squads = write_squads_json()
        total_players = sum(len(players) for players in squads.values())
        empty = sorted(code for code, players in squads.items() if not players)

        self.stdout.write(f'FIFA teams: {len(fifa_teams)}')
        if empty:
            self.stdout.write(self.style.WARNING(f'Empty squads for: {", ".join(empty)}'))

        self.stdout.write(self.style.SUCCESS(
            f'Updated squads for {len(squads)} teams ({total_players} players). '
            'Run seed_wc2026 to load into the database.'
        ))
