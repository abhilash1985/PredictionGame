from datetime import datetime
from zoneinfo import ZoneInfo

from django.db.models import Count
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.matches.models import Match
from apps.tournaments.data.loader import load_wc2026_data, parse_kickoff
from apps.tournaments.models import Round, Stadium, Team, Tournament
from apps.tournaments.views import default_verdict_match


class AdsTxtTests(TestCase):
    def setUp(self):
        self.client = Client()

    @override_settings(GOOGLE_ADSENSE_CLIENT='')
    def test_ads_txt_not_configured_returns_404(self):
        response = self.client.get('/ads.txt')
        self.assertEqual(response.status_code, 404)

    @override_settings(GOOGLE_ADSENSE_CLIENT='ca-pub-1234567890123456')
    def test_ads_txt_returns_publisher_line(self):
        response = self.client.get('/ads.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')
        self.assertIn('google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0', response.content.decode())


class LegalPagesTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_privacy_page_returns_200(self):
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Privacy Policy')
        self.assertContains(response, 'cookies')

    def test_about_page_returns_200(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'fantasy prediction')

    def test_contact_page_returns_200(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Get in touch')


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
            .order_by('match_number')
        )
        default_match = default_verdict_match(verdict_matches)
        self.assertEqual(default_match.pk, self.past_match.pk)
