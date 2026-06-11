from django.db.models import Q

from apps.matches.models import Match, MatchPrediction
from apps.tournaments.models import Tournament
from apps.tournaments.services.standings import get_all_group_standings


class AiPredictContextBuilder:
    CORE_TEMPLATE_CODES = {'MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS'}
    RECENT_PREDICTIONS_LIMIT = 5
    RECENT_RESULTS_LIMIT = 3

    @classmethod
    def build(cls, user, match):
        profile = user.profile
        tournament = match.tournament
        favorite_team = profile.favorite_team

        return {
            'user': {
                'id': user.pk,
                'display_name': profile.display_name,
                'favorite_team': favorite_team.name if favorite_team else None,
                'favorite_team_rank': favorite_team.fifa_ranking if favorite_team else None,
            },
            'match': cls._match_payload(match),
            'standings': cls._standings_payload(tournament, match),
            'recent_results': cls._recent_results_payload(match),
            'user_recent_predictions': cls._user_predictions_payload(user, match),
            'questions': cls._questions_payload(match),
        }

    @classmethod
    def _match_payload(cls, match):
        return {
            'id': match.pk,
            'match_number': match.match_number,
            'home_team': match.team_home.name,
            'away_team': match.team_away.name,
            'home_rank': match.team_home.fifa_ranking,
            'away_rank': match.team_away.fifa_ranking,
            'kickoff_utc': match.kickoff_at.isoformat(),
            'round': match.round.name if match.round else None,
            'stadium': match.stadium.name if match.stadium_id else None,
        }

    @classmethod
    def _standings_payload(cls, tournament, match):
        if not tournament:
            return {}

        all_standings = get_all_group_standings(tournament)
        letters = {
            letter
            for letter in (match.team_home.group_letter, match.team_away.group_letter)
            if letter
        }
        payload = {}
        for letter in letters:
            rows = all_standings.get(letter.upper(), [])
            payload[f'group_{letter.upper()}'] = [
                {
                    'team': row['team'].name,
                    'played': row['played'],
                    'points': row['points'],
                    'goal_diff': row['goal_diff'],
                }
                for row in rows
            ]
        return payload

    @classmethod
    def _recent_results_payload(cls, match):
        return {
            'home_last_results': cls._team_recent_results(match.team_home, match),
            'away_last_results': cls._team_recent_results(match.team_away, match),
        }

    @classmethod
    def _team_recent_results(cls, team, current_match):
        finished = (
            Match.objects.filter(
                tournament=current_match.tournament,
                status=Match.Status.FINISHED,
            )
            .filter(_team_filter(team))
            .exclude(pk=current_match.pk)
            .order_by('-kickoff_at')[: cls.RECENT_RESULTS_LIMIT]
        )
        results = []
        for item in finished:
            if item.home_score is None or item.away_score is None:
                continue
            if item.team_home_id == team.id:
                opponent = item.team_away.short_name
                score = f'{item.home_score}-{item.away_score}'
            else:
                opponent = item.team_home.short_name
                score = f'{item.away_score}-{item.home_score}'
            results.append(f'vs {opponent}: {score}')
        return results

    @classmethod
    def _user_predictions_payload(cls, user, current_match):
        predictions = (
            MatchPrediction.objects.filter(user=user)
            .exclude(match=current_match)
            .select_related('match__team_home', 'match__team_away')
            .prefetch_related('answers__match_question__question_template')
            .order_by('-submitted_at')[: cls.RECENT_PREDICTIONS_LIMIT]
        )
        payload = []
        for prediction in predictions:
            match = prediction.match
            summary = {
                'match': f'{match.team_home.short_name} vs {match.team_away.short_name}',
                'answers': {},
            }
            for answer in prediction.answers.all():
                template = answer.match_question.question_template
                code = template.code if template else f'q{answer.match_question_id}'
                summary['answers'][code] = answer.user_answer
            payload.append(summary)
        return payload

    @classmethod
    def _questions_payload(cls, match):
        questions = []
        for question in match.questions.select_related('question_template').all():
            template_code = question.question_template.code if question.question_template else ''
            questions.append(
                {
                    'id': question.pk,
                    'code': template_code,
                    'text': question.question_text,
                    'options': list(question.options or []),
                    'points': question.points,
                    'personalization': 'core' if template_code in cls.CORE_TEMPLATE_CODES else 'varied',
                },
            )
        return questions


def _team_filter(team):
    return Q(team_home=team) | Q(team_away=team)
