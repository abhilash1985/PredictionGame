from django.db.models import Q

from apps.matches.models import Match, MatchPrediction
from apps.tournaments.services.standings import get_all_group_standings

SIMILAR_RANKING_WINDOW = 15


class AiPredictContextBuilder:
    CORE_TEMPLATE_CODES = {'MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS'}
    RECENT_PREDICTIONS_LIMIT = 5
    RECENT_RESULTS_LIMIT = 5

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
            'head_to_head': cls._head_to_head_payload(match),
            'recent_results': cls._recent_results_payload(match),
            'vs_similar_ranking': cls._similar_ranking_payload(match),
            'user_recent_predictions': cls._user_predictions_payload(user, match),
            'prediction_guidance': cls._prediction_guidance(match),
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
    def _prediction_guidance(cls, match):
        return {
            'never_pick': ['No Results'],
            'core_consistency_rules': [
                'If home team wins, home goals must be greater than away goals.',
                'If away team wins, away goals must be greater than home goals.',
                'If Draw is selected, home and away goals must be equal (e.g. 1-1, 0-0).',
                'Prefer realistic scorelines based on FIFA rankings, recent form, and head-to-head.',
            ],
            'data_priority': [
                'FIFA rankings and ranking gap',
                'Head-to-head history in this tournament',
                'Last 5 match results for each team',
                'Results vs opponents with similar FIFA ranking (±15)',
                'Group standings and goal difference',
                'User favorite team and recent prediction style',
            ],
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
    def _head_to_head_payload(cls, match):
        finished = (
            Match.objects.filter(
                tournament=match.tournament,
                status=Match.Status.FINISHED,
            )
            .filter(
                Q(team_home=match.team_home, team_away=match.team_away)
                | Q(team_home=match.team_away, team_away=match.team_home),
            )
            .exclude(pk=match.pk)
            .order_by('-kickoff_at')[: cls.RECENT_RESULTS_LIMIT]
        )
        meetings = []
        home_wins = away_wins = draws = 0
        for item in finished:
            if item.home_score is None or item.away_score is None:
                continue
            if item.team_home_id == match.team_home.id:
                home_score, away_score = item.home_score, item.away_score
            else:
                home_score, away_score = item.away_score, item.home_score

            if home_score > away_score:
                home_wins += 1
                outcome = f'{match.team_home.short_name} win'
            elif away_score > home_score:
                away_wins += 1
                outcome = f'{match.team_away.short_name} win'
            else:
                draws += 1
                outcome = 'Draw'

            meetings.append(
                {
                    'score': f'{home_score}-{away_score}',
                    'outcome_for_current_home': outcome,
                },
            )

        return {
            'meetings': meetings,
            'summary': {
                f'{match.team_home.short_name}_wins': home_wins,
                'draws': draws,
                f'{match.team_away.short_name}_wins': away_wins,
            },
        }

    @classmethod
    def _recent_results_payload(cls, match):
        return {
            'home_last_results': cls._team_recent_results(match.team_home, match),
            'away_last_results': cls._team_recent_results(match.team_away, match),
            'home_form': cls._team_form_summary(match.team_home, match),
            'away_form': cls._team_form_summary(match.team_away, match),
        }

    @classmethod
    def _similar_ranking_payload(cls, match):
        return {
            'home_vs_similar_rank': cls._team_vs_similar_ranking(match.team_home, match),
            'away_vs_similar_rank': cls._team_vs_similar_ranking(match.team_away, match),
        }

    @classmethod
    def _team_vs_similar_ranking(cls, team, current_match):
        team_rank = team.fifa_ranking or 50
        rank_min = max(1, team_rank - SIMILAR_RANKING_WINDOW)
        rank_max = team_rank + SIMILAR_RANKING_WINDOW

        finished = (
            Match.objects.filter(
                tournament=current_match.tournament,
                status=Match.Status.FINISHED,
            )
            .filter(_team_filter(team))
            .exclude(pk=current_match.pk)
            .select_related('team_home', 'team_away')
            .order_by('-kickoff_at')[: cls.RECENT_RESULTS_LIMIT * 2]
        )

        results = []
        for item in finished:
            opponent = item.team_away if item.team_home_id == team.id else item.team_home
            opponent_rank = opponent.fifa_ranking
            if opponent_rank is None or not (rank_min <= opponent_rank <= rank_max):
                continue
            if item.home_score is None or item.away_score is None:
                continue

            if item.team_home_id == team.id:
                team_score, opp_score = item.home_score, item.away_score
            else:
                team_score, opp_score = item.away_score, item.home_score

            if team_score > opp_score:
                outcome = 'W'
            elif team_score < opp_score:
                outcome = 'L'
            else:
                outcome = 'D'

            results.append(
                {
                    'opponent': opponent.short_name,
                    'opponent_rank': opponent_rank,
                    'score': f'{team_score}-{opp_score}',
                    'result': outcome,
                },
            )
            if len(results) >= cls.RECENT_RESULTS_LIMIT:
                break
        return results

    @classmethod
    def _team_form_summary(cls, team, current_match):
        finished = (
            Match.objects.filter(
                tournament=current_match.tournament,
                status=Match.Status.FINISHED,
            )
            .filter(_team_filter(team))
            .exclude(pk=current_match.pk)
            .order_by('-kickoff_at')[: cls.RECENT_RESULTS_LIMIT]
        )
        wins = draws = losses = 0
        goals_for = goals_against = 0
        for item in finished:
            if item.home_score is None or item.away_score is None:
                continue
            if item.team_home_id == team.id:
                team_score, opp_score = item.home_score, item.away_score
            else:
                team_score, opp_score = item.away_score, item.home_score

            goals_for += team_score
            goals_against += opp_score
            if team_score > opp_score:
                wins += 1
            elif team_score < opp_score:
                losses += 1
            else:
                draws += 1

        played = wins + draws + losses
        return {
            'played': played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'avg_goals_scored': round(goals_for / played, 2) if played else None,
            'avg_goals_conceded': round(goals_against / played, 2) if played else None,
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
            .select_related('team_home', 'team_away')
            .order_by('-kickoff_at')[: cls.RECENT_RESULTS_LIMIT]
        )
        results = []
        for item in finished:
            if item.home_score is None or item.away_score is None:
                continue
            opponent = item.team_away if item.team_home_id == team.id else item.team_home
            if item.team_home_id == team.id:
                team_score, opp_score = item.home_score, item.away_score
            else:
                team_score, opp_score = item.away_score, item.home_score

            if team_score > opp_score:
                outcome = 'W'
            elif team_score < opp_score:
                outcome = 'L'
            else:
                outcome = 'D'

            opponent_rank = opponent.fifa_ranking
            rank_note = f' (rank #{opponent_rank})' if opponent_rank else ''
            results.append(
                {
                    'summary': f'{outcome} {team_score}-{opp_score} vs {opponent.short_name}{rank_note}',
                    'goals_scored': team_score,
                    'goals_conceded': opp_score,
                },
            )
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
