from datetime import datetime
from zoneinfo import ZoneInfo

from django.db.models import Count
from django.test import TestCase
from django.utils import timezone

from apps.matches.models import Match
from apps.tournaments.data.loader import load_wc2026_data, parse_kickoff
from apps.tournaments.models import Round, Stadium, Team, Tournament
from apps.tournaments.views import default_verdict_match


class ParseKickoffTest(TestCase):
    def test_opening_match_ist(self):
        data = load_wc2026_data()
        fixture = data['group_matches'][0]
        kickoff = parse_kickoff(fixture['date'], fixture['time'], fixture['stadium'], data['stadiums'])
        ist = kickoff.astimezone(ZoneInfo('Asia/Kolkata'))

        self.assertEqual(kickoff, datetime(2026, 6, 11, 19, 0, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(ist, datetime(2026, 6, 12, 0, 30, tzinfo=ZoneInfo('Asia/Kolkata')))

    def test_korea_czechia_ist(self):
        data = load_wc2026_data()
        fixture = data['group_matches'][1]
        kickoff = parse_kickoff(fixture['date'], fixture['time'], fixture['stadium'], data['stadiums'])
        ist = kickoff.astimezone(ZoneInfo('Asia/Kolkata'))

        self.assertEqual(kickoff, datetime(2026, 6, 12, 2, 0, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(ist, datetime(2026, 6, 12, 7, 30, tzinfo=ZoneInfo('Asia/Kolkata')))


class DefaultVerdictMatchTests(TestCase):
    def setUp(self):
        today = timezone.now().date()
        self.tournament = Tournament.objects.create(
            name='Test Cup',
            location='Test',
            start_date=today,
            end_date=today,
            is_active=True,
        )
        self.round = Round.objects.create(tournament=self.tournament, name='Group A', sort_order=1)
        self.stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        self.home = Team.objects.create(name='Home FC', short_name='HOM', fifa_code='HOM', group_letter='A')
        self.away = Team.objects.create(name='Away FC', short_name='AWY', fifa_code='AWY', group_letter='A')
        self.past_match = Match.objects.create(
            tournament=self.tournament,
            round=self.round,
            match_number=1,
            team_home=self.home,
            team_away=self.away,
            stadium=self.stadium,
            kickoff_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.future_match = Match.objects.create(
            tournament=self.tournament,
            round=self.round,
            match_number=2,
            team_home=self.away,
            team_away=self.home,
            stadium=self.stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=1),
        )

    def test_default_verdict_match_prefers_most_recent_past_match(self):
        verdict_matches = (
            Match.objects.filter(tournament=self.tournament, round__name__startswith='Group ')
            .annotate(prediction_count=Count('predictions'))
            .order_by('kickoff_at')
        )
        default_match = default_verdict_match(verdict_matches)
        self.assertEqual(default_match.pk, self.past_match.pk)
