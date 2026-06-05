from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.matches.models import GameSettings, Match, MatchQuestion, QuestionTemplate
from apps.tournaments.models import PastWorldCupWinner, Player, Round, Stadium, Team, Tournament


class Command(BaseCommand):
    help = 'Seed demo FIFA 2026 tournament data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding WC 2026 demo data...')

        tournament, _ = Tournament.objects.update_or_create(
            name='FIFA World Cup 2026',
            defaults={
                'location': 'Canada, Mexico, USA',
                'start_date': timezone.now().date(),
                'end_date': timezone.now().date() + timedelta(days=30),
                'is_active': True,
            },
        )
        Tournament.objects.exclude(pk=tournament.pk).update(is_active=False)

        group, _ = Round.objects.get_or_create(tournament=tournament, name='GROUP-STAGE', defaults={'sort_order': 1})

        teams_data = [
            ('Argentina', 'ARG', 'ARG', 1),
            ('France', 'FRA', 'FRA', 2),
            ('Brazil', 'BRA', 'BRA', 3),
            ('England', 'ENG', 'ENG', 4),
            ('USA', 'USA', 'USA', 15),
            ('Mexico', 'MEX', 'MEX', 14),
        ]
        teams = {}
        for name, short, code, rank in teams_data:
            team, _ = Team.objects.update_or_create(
                short_name=short,
                defaults={'name': name, 'fifa_code': code, 'fifa_ranking': rank},
            )
            teams[short] = team

        stadium, _ = Stadium.objects.get_or_create(
            name='MetLife Stadium',
            defaults={'city': 'East Rutherford', 'country': 'USA'},
        )

        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()

        templates = [
            ('MATCH_WINNER', 'Who will win the match?', 'winner', 8, ['{home_team}', '{away_team}', 'Draw']),
            ('HOME_GOALS', 'Goals scored by {home_team}?', 'goals', 5, [str(i) for i in range(0, 6)]),
            ('AWAY_GOALS', 'Goals scored by {away_team}?', 'goals', 5, [str(i) for i in range(0, 6)]),
            ('PLAYER_OF_MATCH', 'Player of the match', 'player', 6, []),
            ('TOTAL_YELLOW_CARDS', 'Total yellow cards in the match', 'stats', 3, [str(i) for i in range(0, 8)]),
        ]
        for code, text, category, points, _opts in templates:
            QuestionTemplate.objects.update_or_create(
                code=code,
                defaults={
                    'question_text': text,
                    'category': category,
                    'default_points': points,
                    'question_type': 'choice',
                    'is_active': True,
                },
            )

        sample_players = [
            ('ARG', [('Lionel', 'Messi', 10, 'RW'), ('Emiliano', 'Martinez', 23, 'GK')]),
            ('FRA', [('Kylian', 'Mbappe', 10, 'ST'), ('Hugo', 'Lloris', 1, 'GK')]),
            ('BRA', [('Neymar', 'Jr', 10, 'LW'), ('Alisson', 'Becker', 1, 'GK')]),
            ('ENG', [('Harry', 'Kane', 9, 'ST'), ('Jordan', 'Pickford', 1, 'GK')]),
            ('USA', [('Christian', 'Pulisic', 10, 'LW'), ('Matt', 'Turner', 1, 'GK')]),
            ('MEX', [('Alexis', 'Vega', 10, 'LW'), ('Guillermo', 'Ochoa', 13, 'GK')]),
        ]
        for short, players in sample_players:
            team = teams[short]
            for first, last, number, pos in players:
                Player.objects.update_or_create(
                    team=team,
                    jersey_number=number,
                    defaults={'first_name': first, 'last_name': last, 'position': pos, 'is_active': True},
                )

        pairings = [
            ('ARG', 'FRA', 1),
            ('BRA', 'ENG', 2),
            ('USA', 'MEX', 3),
        ]
        now = timezone.now()
        for i, (home, away, num) in enumerate(pairings):
            kickoff = now + timedelta(days=i + 1, hours=18)
            match, _ = Match.objects.update_or_create(
                tournament=tournament,
                match_number=num,
                defaults={
                    'round': group,
                    'team_home': teams[home],
                    'team_away': teams[away],
                    'stadium': stadium,
                    'kickoff_at': kickoff,
                    'status': Match.Status.SCHEDULED,
                },
            )
            if not match.questions.exists():
                for template in QuestionTemplate.objects.filter(is_active=True):
                    options = []
                    if template.code == 'MATCH_WINNER':
                        options = [match.team_home.name, match.team_away.name, 'Draw']
                    elif template.code in ('HOME_GOALS', 'AWAY_GOALS', 'TOTAL_YELLOW_CARDS'):
                        options = [str(n) for n in range(0, 6 if 'GOALS' in template.code else 8)]
                    elif template.code == 'PLAYER_OF_MATCH':
                        options = [
                            p.full_name for p in
                            list(match.team_home.players.filter(is_active=True)) +
                            list(match.team_away.players.filter(is_active=True))
                        ]

                    MatchQuestion.objects.create(
                        match=match,
                        question_template=template,
                        question_text=template.render_text(match),
                        options=options,
                        points=template.default_points,
                        sort_order=template.id,
                    )

        winners = [
            (2022, 'Argentina'), (2018, 'France'), (2014, 'Germany'), (2010, 'Spain'),
            (2006, 'Italy'), (2002, 'Brazil'), (1998, 'France'), (1994, 'Brazil'),
        ]
        for year, country in winners:
            PastWorldCupWinner.objects.update_or_create(year=year, defaults={'country': country})

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
