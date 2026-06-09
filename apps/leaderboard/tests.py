from django.test import TestCase
from django.utils import timezone

from apps.leaderboard.services import LeaderboardService
from apps.matches.models import Match, MatchQuestion, QuestionTemplate
from apps.tournaments.models import Round, Stadium, Team, Tournament


class PredictionGraphServiceTests(TestCase):
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
        self.future_match = Match.objects.create(
            tournament=self.tournament,
            round=self.round,
            match_number=1,
            team_home=self.home,
            team_away=self.away,
            stadium=self.stadium,
            kickoff_at=timezone.now() + timezone.timedelta(days=2),
        )
        self.past_match = Match.objects.create(
            tournament=self.tournament,
            round=self.round,
            match_number=2,
            team_home=self.away,
            team_away=self.home,
            stadium=self.stadium,
            kickoff_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.winner_template = QuestionTemplate.objects.create(
            code='MATCH_WINNER',
            question_text='Who wins?',
            question_type=QuestionTemplate.QuestionType.CHOICE,
            category=QuestionTemplate.Category.WINNER,
        )
        MatchQuestion.objects.create(
            match=self.future_match,
            question_template=self.winner_template,
            question_text='Who wins?',
            options=[self.home.name, 'Draw', self.away.name],
            points=5,
        )

    def test_default_graph_match_prefers_upcoming(self):
        default_match = LeaderboardService.default_graph_match(self.tournament)
        self.assertEqual(default_match.pk, self.future_match.pk)

    def test_prediction_graph_data_for_match_includes_chart_metadata(self):
        graph_data = LeaderboardService.prediction_graph_data_for_match(self.future_match)
        self.assertEqual(len(graph_data), 1)
        self.assertEqual(graph_data[0]['chart_type'], 'doughnut')
        self.assertEqual(graph_data[0]['points'], 5)
        self.assertEqual(graph_data[0]['total'], 0)
        self.assertEqual(graph_data[0]['labels'], ['Home FC', 'Draw', 'Away FC'])
        self.assertEqual(graph_data[0]['counts'], [0, 0, 0])

    def test_graph_match_choices_orders_by_kickoff(self):
        matches = list(LeaderboardService.graph_match_choices(self.tournament))
        self.assertEqual([match.pk for match in matches], [self.past_match.pk, self.future_match.pk])
