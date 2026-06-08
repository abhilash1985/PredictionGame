from django.core.management.base import BaseCommand
from django.db import transaction

from apps.matches.models import GameSettings, Match, MatchQuestion, QuestionTemplate
from apps.tournaments.data.loader import load_wc2026_data, load_wc2026_squads, parse_kickoff
from apps.tournaments.models import PastWorldCupWinner, Player, Round, Stadium, Team, Tournament


class Command(BaseCommand):
    help = 'Seed FIFA World Cup 2026 group stage data (fifa.com fixture times are UTC)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-matches',
            action='store_true',
            help='Delete existing matches and predictions before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Loading FIFA World Cup 2026 data...')
        data = load_wc2026_data()
        squads = load_wc2026_squads()

        tournament, _ = Tournament.objects.update_or_create(
            name='FIFA World Cup 2026',
            defaults={
                'location': 'Canada, Mexico, USA',
                'start_date': '2026-06-11',
                'end_date': '2026-07-19',
                'is_active': True,
            },
        )
        Tournament.objects.exclude(pk=tournament.pk).update(is_active=False)

        stadiums = {}
        for key, (name, city, country, _tz) in data['stadiums'].items():
            stadium, _ = Stadium.objects.update_or_create(
                name=name,
                defaults={'city': city, 'country': country},
            )
            stadiums[key] = stadium

        teams = {}
        for team_data in data['teams']:
            team, _ = Team.objects.update_or_create(
                short_name=team_data['code'],
                defaults={
                    'name': team_data['name'],
                    'fifa_code': team_data['code'],
                    'group_letter': team_data['group'],
                    'fifa_ranking': team_data['ranking'],
                },
            )
            teams[team_data['code']] = team

        rounds = {}
        for letter in 'ABCDEFGHIJKL':
            rnd, _ = Round.objects.update_or_create(
                tournament=tournament,
                name=f'Group {letter}',
                defaults={'sort_order': ord(letter) - ord('A') + 1},
            )
            rounds[f'Group {letter}'] = rnd

        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()

        self._seed_question_templates()
        self._seed_squads(teams, squads)

        if options['clear_matches']:
            Match.objects.filter(tournament=tournament).delete()

        official_codes = {team_data['code'] for team_data in data['teams']}
        Team.objects.exclude(short_name__in=official_codes).delete()
        Round.objects.filter(tournament=tournament).exclude(name__startswith='Group ').delete()

        match_no = 1
        for fixture in data['group_matches']:
            match_no = self._seed_match(
                tournament=tournament,
                match_no=match_no,
                fixture=fixture,
                round_obj=rounds[f"Group {fixture['group']}"],
                teams=teams,
                stadiums=stadiums,
                stadiums_meta=data['stadiums'],
            )

        for year, country in data['past_winners']:
            PastWorldCupWinner.objects.update_or_create(year=year, defaults={'country': country})

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {match_no - 1} group stage matches, {len(data["teams"])} teams, '
            f'{sum(len(v) for v in squads.values())} players.'
        ))

    def _seed_question_templates(self):
        templates = [
            ('MATCH_WINNER', 'Who will win the match?', 'winner', 8),
            ('HOME_GOALS', 'Goals scored by {home_team}?', 'goals', 5),
            ('AWAY_GOALS', 'Goals scored by {away_team}?', 'goals', 5),
            ('PLAYER_OF_MATCH', 'Player of the match', 'player', 6),
            ('TOTAL_YELLOW_CARDS', 'Total yellow cards in the match', 'stats', 3),
        ]
        for code, text, category, points in templates:
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

    def _seed_squads(self, teams, squads):
        for code, players in squads.items():
            team = teams.get(code)
            if not team:
                continue
            for first, last, number, position in players:
                Player.objects.update_or_create(
                    team=team,
                    jersey_number=number,
                    defaults={
                        'first_name': first,
                        'last_name': last,
                        'position': position,
                        'is_active': True,
                    },
                )

    def _seed_match(self, tournament, match_no, fixture, round_obj, teams, stadiums, stadiums_meta):
        home = teams[fixture['home']]
        away = teams[fixture['away']]
        stadium = stadiums[fixture['stadium']]
        kickoff = parse_kickoff(fixture['date'], fixture['time'], fixture['stadium'], stadiums_meta)

        match, created = Match.objects.update_or_create(
            tournament=tournament,
            match_number=match_no,
            defaults={
                'round': round_obj,
                'team_home': home,
                'team_away': away,
                'stadium': stadium,
                'kickoff_at': kickoff,
                'status': Match.Status.SCHEDULED,
            },
        )

        if created or not match.questions.exists():
            if not created and match.questions.exists():
                match.questions.all().delete()
            self._create_match_questions(match)

        return match_no + 1

    def _create_match_questions(self, match):
        for template in QuestionTemplate.objects.filter(is_active=True):
            options = []
            if template.code == 'MATCH_WINNER':
                options = [match.team_home.name, match.team_away.name, 'Draw']
            elif template.code in ('HOME_GOALS', 'AWAY_GOALS'):
                options = [str(n) for n in range(0, 6)]
            elif template.code == 'TOTAL_YELLOW_CARDS':
                options = [str(n) for n in range(0, 8)]
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
