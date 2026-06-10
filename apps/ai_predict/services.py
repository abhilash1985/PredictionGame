import random

from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.matches.models import GameSettings, Match, MatchPrediction, MatchQuestion, QuestionPrediction


class AiPredictService:
    @staticmethod
    def heuristic_answer(question, match):
        options = question.options or []
        template_code = question.question_template.code if question.question_template else ''

        if template_code == 'MATCH_WINNER' and len(options) >= 2:
            home_rank = match.team_home.fifa_ranking or 50
            away_rank = match.team_away.fifa_ranking or 50
            if home_rank < away_rank:
                return match.team_home.name
            if away_rank < home_rank:
                return match.team_away.name
            pickable = [option for option in options if option not in {'Draw', 'No Results'}]
            return random.choice(pickable or options)

        if 'GOALS' in template_code and options:
            return random.choice(options)

        if template_code == 'PLAYER_OF_MATCH':
            players = list(match.team_home.players.filter(is_active=True)) + list(
                match.team_away.players.filter(is_active=True)
            )
            if players:
                player = random.choice(players)
                return player.full_name

        if options:
            return random.choice(options)

        return '0'

    @classmethod
    def predict_for_user(cls, user, match):
        if MatchPrediction.objects.filter(user=user, match=match).exists():
            return None
        if not match.is_prediction_open:
            return None

        prediction = MatchPrediction.objects.create(user=user, match=match, is_ai_generated=True)
        for question in match.questions.all():
            QuestionPrediction.objects.create(
                match_prediction=prediction,
                match_question=question,
                user_answer=cls.heuristic_answer(question, match),
            )
        return prediction

    @classmethod
    def run_scheduled_predictions(cls):
        settings = GameSettings.load()
        hours = settings.ai_predict_hours_before
        window_start = timezone.now()
        window_end = window_start + timezone.timedelta(hours=hours)

        matches = Match.objects.filter(
            kickoff_at__gte=window_start,
            kickoff_at__lte=window_end,
            status=Match.Status.SCHEDULED,
        ).prefetch_related('questions', 'team_home__players', 'team_away__players')

        profiles = UserProfile.objects.filter(ai_predict_enabled=True).select_related('user')
        created = 0
        for match in matches:
            for profile in profiles:
                result = cls.predict_for_user(profile.user, match)
                if result:
                    created += 1
        return created
