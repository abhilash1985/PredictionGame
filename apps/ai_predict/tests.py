from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.accounts.profile_service import ensure_user_profile
from apps.ai_predict.services import AiPredictService
from apps.ai_predict.core_prediction import (
    generate_coherent_core_answers,
    goals_consistent_with_winner,
    normalize_core_answers,
)
from apps.ai_predict.validators import validate_answers
from apps.matches.models import GameSettings, Match, MatchPrediction, MatchQuestion, QuestionPrediction, QuestionTemplate
from apps.tournaments.models import Player, Round, Stadium, Team, Tournament
from django.contrib.auth import get_user_model

User = get_user_model()


class AiPredictValidatorTests(TestCase):
    def test_validate_answers_accepts_exact_option(self):
        template = QuestionTemplate.objects.create(code='TEST', question_text='Test?', default_points=2)
        match = _create_match()
        question = MatchQuestion.objects.create(
            match=match,
            question_template=template,
            question_text='Pick',
            options=['A', 'B'],
            points=2,
        )
        validated = validate_answers([question], {str(question.pk): 'A'})
        self.assertEqual(validated[question.pk], 'A')

    def test_validate_answers_rejects_invalid_option(self):
        template = QuestionTemplate.objects.create(code='TEST2', question_text='Test?', default_points=2)
        match = _create_match()
        question = MatchQuestion.objects.create(
            match=match,
            question_template=template,
            question_text='Pick',
            options=['A', 'B'],
            points=2,
        )
        validated = validate_answers([question], {str(question.pk): 'C'})
        self.assertEqual(validated, {})


class AiPredictServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='ai@example.com', password='testpass123')
        self.profile = ensure_user_profile(self.user)
        self.profile.ai_predict_enabled = True
        self.profile.save()
        self.match = _create_match(kickoff_at=timezone.now() + timedelta(hours=1))

    def test_predict_for_user_skips_existing_prediction(self):
        MatchPrediction.objects.create(user=self.user, match=self.match, is_ai_generated=False)
        self.assertIsNone(AiPredictService.predict_for_user(self.user, self.match))

    @override_settings(GOOGLE_API_KEY='')
    def test_predict_for_user_creates_heuristic_prediction_without_gemini(self):
        _add_basic_questions(self.match)
        prediction = AiPredictService.predict_for_user(self.user, self.match)
        self.assertIsNotNone(prediction)
        self.assertTrue(prediction.is_ai_generated)
        self.assertEqual(prediction.answers.count(), 3)

    @override_settings(GOOGLE_API_KEY='test-key')
    @patch('apps.ai_predict.gemini_client.GeminiPredictor._call_gemini')
    def test_predict_for_user_uses_gemini_answers(self, mock_call):
        import json

        questions = _add_basic_questions(self.match)
        winner, home_goals, away_goals = questions
        mock_call.return_value = json.dumps(
            {
                'answers': {
                    str(winner.pk): self.match.team_home.name,
                    str(home_goals.pk): '2',
                    str(away_goals.pk): '1',
                },
            },
        )
        prediction = AiPredictService.predict_for_user(self.user, self.match)
        answers = {answer.match_question_id: answer.user_answer for answer in prediction.answers.all()}
        self.assertEqual(answers[winner.pk], self.match.team_home.name)
        self.assertEqual(answers[home_goals.pk], '2')
        self.assertEqual(answers[away_goals.pk], '1')

    @override_settings(GOOGLE_API_KEY='test-key')
    @patch('apps.ai_predict.gemini_client.GeminiPredictor._call_gemini')
    def test_inconsistent_gemini_core_answers_are_normalized(self, mock_call):
        import json

        questions = _add_basic_questions(self.match)
        winner, home_goals, away_goals = questions
        mock_call.return_value = json.dumps(
            {
                'answers': {
                    str(winner.pk): self.match.team_home.name,
                    str(home_goals.pk): '0',
                    str(away_goals.pk): '4',
                },
            },
        )
        prediction = AiPredictService.predict_for_user(self.user, self.match)
        answers = {answer.match_question_id: answer.user_answer for answer in prediction.answers.all()}
        self.assertEqual(answers[winner.pk], self.match.team_home.name)
        self.assertNotEqual(answers[home_goals.pk], '0')
        self.assertNotEqual(answers[away_goals.pk], '4')
        self.assertGreater(
            int(answers[home_goals.pk]),
            int(answers[away_goals.pk]),
        )

    @override_settings(GOOGLE_API_KEY='')
    def test_heuristic_core_prediction_is_consistent(self):
        questions = _add_basic_questions(self.match)
        answers = AiPredictService.build_answers(self.user, self.match, questions)
        winner, home_goals, away_goals = questions
        self.assertNotEqual(answers[winner.pk], 'No Results')
        self.assertTrue(
            goals_consistent_with_winner(
                answers[winner.pk],
                int(answers[home_goals.pk]),
                int(answers[away_goals.pk]),
                self.match,
            ),
        )

    @override_settings(GOOGLE_API_KEY='')
    def test_run_scheduled_predictions_within_window(self):
        _add_basic_questions(self.match)
        created = AiPredictService.run_scheduled_predictions()
        self.assertEqual(created, 1)

    @override_settings(GOOGLE_API_KEY='')
    def test_run_upcoming_matches_limits_fixture_count(self):
        _add_basic_questions(self.match)
        match_two = _create_match(
            kickoff_at=timezone.now() + timedelta(hours=2),
            tournament=self.match.tournament,
            round_obj=self.match.round,
            stadium=self.match.stadium,
            team_home=self.match.team_home,
            team_away=self.match.team_away,
            match_number=2,
        )
        match_three = _create_match(
            kickoff_at=timezone.now() + timedelta(hours=3),
            tournament=self.match.tournament,
            round_obj=self.match.round,
            stadium=self.match.stadium,
            team_home=self.match.team_home,
            team_away=self.match.team_away,
            match_number=3,
        )
        _add_basic_questions(match_two)
        _add_basic_questions(match_three)

        created = AiPredictService.run_scheduled_predictions(upcoming_match_limit=2)
        self.assertEqual(created, 2)
        self.assertEqual(MatchPrediction.objects.filter(user=self.user).count(), 2)
        self.assertFalse(MatchPrediction.objects.filter(user=self.user, match=match_three).exists())


class CorePredictionTests(TestCase):
    def test_normalize_replaces_no_results_and_fixes_goals(self):
        match = _create_match()
        questions = _add_basic_questions(match)
        winner, home_goals, away_goals = questions
        answers = {
            winner.pk: 'No Results',
            home_goals.pk: '0',
            away_goals.pk: '3',
        }
        normalized = normalize_core_answers(questions, answers, match)
        self.assertNotEqual(normalized[winner.pk], 'No Results')
        self.assertTrue(
            goals_consistent_with_winner(
                normalized[winner.pk],
                int(normalized[home_goals.pk]),
                int(normalized[away_goals.pk]),
                match,
            ),
        )

    def test_generate_coherent_core_answers_for_draw(self):
        match = _create_match(
            team_home=Team.objects.create(name='Even A', short_name='EVA', group_letter='B', fifa_ranking=10),
            team_away=Team.objects.create(name='Even B', short_name='EVB', group_letter='B', fifa_ranking=11),
        )
        questions = _add_basic_questions(match)
        answers = generate_coherent_core_answers(match, questions)
        winner, home_goals, away_goals = questions
        if answers[winner.pk] == 'Draw':
            self.assertEqual(answers[home_goals.pk], answers[away_goals.pk])


def _create_match(
    kickoff_at=None,
    match_number=1,
    tournament=None,
    round_obj=None,
    stadium=None,
    team_home=None,
    team_away=None,
):
    if tournament is None:
        tournament = Tournament.objects.create(
            name='WC 2026',
            location='USA',
            start_date='2026-06-01',
            end_date='2026-07-01',
            is_active=True,
        )
    if round_obj is None:
        round_obj = Round.objects.create(tournament=tournament, name='Group A', sort_order=1)
    if stadium is None:
        stadium = Stadium.objects.create(name='Test Stadium', city='Test', country='USA')
    if team_home is None:
        team_home = Team.objects.create(name='Argentina', short_name='ARG', group_letter='A', fifa_ranking=1)
    if team_away is None:
        team_away = Team.objects.create(name='France', short_name='FRA', group_letter='A', fifa_ranking=2)
    if team_home.players.filter(is_active=True).count() == 0:
        Player.objects.create(team=team_home, first_name='Lionel', last_name='Messi', jersey_number=10, position='ST')
    return Match.objects.create(
        tournament=tournament,
        round=round_obj,
        match_number=match_number,
        team_home=team_home,
        team_away=team_away,
        stadium=stadium,
        kickoff_at=kickoff_at or timezone.now() + timedelta(hours=1),
    )


def _add_basic_questions(match):
    winner, _ = QuestionTemplate.objects.get_or_create(
        code='MATCH_WINNER',
        defaults={'question_text': 'Winner?', 'default_points': 10},
    )
    home_goals, _ = QuestionTemplate.objects.get_or_create(
        code='HOME_GOALS',
        defaults={'question_text': 'Home goals?', 'default_points': 5},
    )
    away_goals, _ = QuestionTemplate.objects.get_or_create(
        code='AWAY_GOALS',
        defaults={'question_text': 'Away goals?', 'default_points': 5},
    )
    options = [match.team_home.name, match.team_away.name, 'Draw', 'No Results']
    q1 = MatchQuestion.objects.create(
        match=match,
        question_template=winner,
        question_text='Winner?',
        options=options,
        points=10,
        sort_order=0,
    )
    q2 = MatchQuestion.objects.create(
        match=match,
        question_template=home_goals,
        question_text='Home goals?',
        options=['0', '1', '2'],
        points=5,
        sort_order=1,
    )
    q3 = MatchQuestion.objects.create(
        match=match,
        question_template=away_goals,
        question_text='Away goals?',
        options=['0', '1', '2'],
        points=5,
        sort_order=2,
    )
    return q1, q2, q3
