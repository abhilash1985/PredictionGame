import logging
import random

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.ai_predict.context import AiPredictContextBuilder
from apps.ai_predict.gemini_client import GeminiPredictor
from apps.ai_predict.validators import missing_question_ids, validate_answers
from apps.matches.models import GameSettings, Match, MatchPrediction, QuestionPrediction

logger = logging.getLogger(__name__)


class AiPredictService:
    @staticmethod
    def heuristic_answer(question, match, user=None, rng=None):
        options = question.options or []
        template_code = question.question_template.code if question.question_template else ''
        randomizer = rng or random.Random(
            f'{user.pk}:{match.pk}:{question.pk}' if user is not None else None,
        )

        if template_code == 'MATCH_WINNER' and len(options) >= 2:
            home_rank = match.team_home.fifa_ranking or 50
            away_rank = match.team_away.fifa_ranking or 50
            favorite = user.profile.favorite_team if user is not None and hasattr(user, 'profile') else None
            favorite_name = favorite.name if favorite else None
            home_name = match.team_home.name
            away_name = match.team_away.name

            if favorite_name in {home_name, away_name} and favorite_name in options:
                if home_rank == away_rank or abs(home_rank - away_rank) <= 8:
                    return favorite_name

            if home_rank < away_rank and home_name in options:
                return home_name
            if away_rank < home_rank and away_name in options:
                return away_name
            pickable = [option for option in options if option not in {'Draw', 'No Results'}]
            return randomizer.choice(pickable or options)

        if 'GOALS' in template_code and options:
            return randomizer.choice(options)

        if (
            template_code == 'PLAYER_OF_MATCH'
            or (question.question_template and question.question_template.category == 'player')
        ):
            players = list(match.team_home.players.filter(is_active=True)) + list(
                match.team_away.players.filter(is_active=True)
            )
            player_names = {player.full_name for player in players}
            player_options = [option for option in options if option in player_names]
            if player_options:
                return randomizer.choice(player_options)

        if options:
            return randomizer.choice(options)

        return '0'

    @classmethod
    def build_answers(cls, user, match, questions):
        answers = {}
        if GeminiPredictor.is_configured():
            context = AiPredictContextBuilder.build(user, match)
            gemini_answers = GeminiPredictor.predict(context)
            answers = validate_answers(questions, gemini_answers)
            missing = missing_question_ids(questions, answers)
            if missing:
                logger.info(
                    'Gemini partial answers for user=%s match=%s; filling %s via fallback',
                    user.pk,
                    match.pk,
                    len(missing),
                )

        rng = random.Random(f'{user.pk}:{match.pk}')
        for question in questions:
            if question.pk not in answers:
                answers[question.pk] = cls.heuristic_answer(question, match, user=user, rng=rng)
        return answers

    @classmethod
    def predict_for_user(cls, user, match):
        if MatchPrediction.objects.filter(user=user, match=match).exists():
            return None
        if not match.is_prediction_open:
            return None

        questions = list(
            match.questions.select_related('question_template').order_by('sort_order', 'id'),
        )
        if not questions:
            return None

        answers = cls.build_answers(user, match, questions)
        prediction = MatchPrediction.objects.create(user=user, match=match, is_ai_generated=True)
        for question in questions:
            QuestionPrediction.objects.create(
                match_prediction=prediction,
                match_question=question,
                user_answer=answers[question.pk],
            )
        return prediction

    @classmethod
    def run_scheduled_predictions(cls):
        game_settings = GameSettings.load()
        hours = game_settings.ai_predict_hours_before
        window_start = timezone.now()
        window_end = window_start + timezone.timedelta(hours=hours)
        max_users = getattr(settings, 'AI_PREDICT_MAX_USERS_PER_RUN', 500)

        matches = Match.objects.filter(
            kickoff_at__gte=window_start,
            kickoff_at__lte=window_end,
            status=Match.Status.SCHEDULED,
        ).prefetch_related(
            'questions__question_template',
            'team_home__players',
            'team_away__players',
        ).select_related('team_home', 'team_away', 'round', 'stadium', 'tournament')

        profiles = list(
            UserProfile.objects.filter(ai_predict_enabled=True).select_related('user', 'favorite_team')[:max_users],
        )
        created = 0
        for match in matches:
            for profile in profiles:
                result = cls.predict_for_user(profile.user, match)
                if result:
                    created += 1
        return created
