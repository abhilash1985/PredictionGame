from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.matches.forms import MatchPredictionForm
from apps.matches.models import GameSettings, Match, MatchQuestion, QuestionTemplate
from apps.tournaments.models import Round, Stadium, Team, Tournament

User = get_user_model()


class MatchPredictionFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='predictor@example.com', password='testpass123')
        tournament = Tournament.objects.create(
            name='Test WC',
            location='Test',
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
        )
        rnd = Round.objects.create(tournament=tournament, name='GROUP', sort_order=1)
        home = Team.objects.create(name='Home', short_name='HOM', fifa_code='HOM')
        away = Team.objects.create(name='Away', short_name='AWY', fifa_code='AWY')
        stadium = Stadium.objects.create(name='Test Stadium', city='Test City', country='Test')
        cls.match = Match.objects.create(
            tournament=tournament,
            round=rnd,
            match_number=1,
            team_home=home,
            team_away=away,
            stadium=stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=1),
        )
        template = QuestionTemplate.objects.create(
            code='MATCH_WINNER',
            question_text='Who wins?',
            default_points=8,
        )
        MatchQuestion.objects.create(
            match=cls.match,
            question_template=template,
            question_text='Who wins?',
            options=[home.name, away.name, 'Draw'],
            points=8,
        )
        settings = GameSettings.load()
        settings.tournament_active = tournament
        settings.save()

    def test_requires_match_and_user(self):
        with self.assertRaises(TypeError):
            MatchPredictionForm()

        with self.assertRaises(TypeError):
            MatchPredictionForm(match=self.match)

        form = MatchPredictionForm(match=self.match, user=self.user)
        self.assertIsNotNone(form)
