import logging
import random

from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.ai_predict.context import AiPredictContextBuilder
from apps.ai_predict.core_prediction import (
    generate_coherent_core_answers,
    normalize_core_answers,
)
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
        rng = random.Random(f'{user.pk}:{match.pk}')
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

        core_fallback = generate_coherent_core_answers(match, questions, user=user, rng=rng)
        for question in questions:
            template_code = question.question_template.code if question.question_template else ''
            if question.pk not in answers and template_code in {'MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS'}:
                if question.pk in core_fallback:
                    answers[question.pk] = core_fallback[question.pk]

        for question in questions:
            if question.pk not in answers:
                answers[question.pk] = cls.heuristic_answer(question, match, user=user, rng=rng)

        return normalize_core_answers(questions, answers, match, user=user, rng=rng)

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
    def _upcoming_matches_queryset(cls):
        return (
            Match.objects.filter(
                kickoff_at__gte=timezone.now(),
                status=Match.Status.SCHEDULED,
            )
            .prefetch_related(
                'questions__question_template',
                'team_home__players',
                'team_away__players',
            )
            .select_related('team_home', 'team_away', 'round', 'stadium', 'tournament')
            .order_by('match_number')
        )

    @classmethod
    def run_scheduled_predictions(cls, upcoming_match_limit=None):
        game_settings = GameSettings.load()
        max_users = game_settings.ai_predict_max_users_per_run

        if upcoming_match_limit:
            matches = cls._upcoming_matches_queryset()[:upcoming_match_limit]
        else:
            hours = game_settings.ai_predict_hours_before
            window_end = timezone.now() + timezone.timedelta(hours=hours)
            matches = cls._upcoming_matches_queryset().filter(kickoff_at__lte=window_end)

        profiles = list(
            UserProfile.objects.filter(ai_predict_enabled=True).select_related('user', 'favorite_team')[:max_users],
        )
        match_list = list(matches)
        total_jobs = len(match_list) * len(profiles)
        logger.info(
            'AI predict run: %s match(es), %s enabled user(s), up to %s prediction job(s)',
            len(match_list),
            len(profiles),
            total_jobs,
        )
        created = 0
        completed = 0
        for match in match_list:
            for profile in profiles:
                completed += 1
                if completed == 1 or completed % 25 == 0 or completed == total_jobs:
                    logger.info('AI predict progress: %s/%s', completed, total_jobs)
                result = cls.predict_for_user(profile.user, match)
                if result:
                    created += 1
        return created
