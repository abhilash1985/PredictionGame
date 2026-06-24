from django.db.models import Count, F

from apps.leaderboard.services import LeaderboardService
from apps.matches.models import Match, MatchPrediction, QuestionPrediction
from apps.matches.scorecard_service import MatchScorecardService
from apps.tournaments.context_processors import get_active_tournament


class DashboardStatsService:
    @staticmethod
    def stats(tournament=None, user_timezone=None):
        tournament = tournament or get_active_tournament()
        if not tournament:
            return DashboardStatsService._empty_stats()

        leaderboard = LeaderboardService.user_stats(tournament)
        return {
            'recent_match_results': DashboardStatsService.recent_match_results(tournament),
            'leaderboard_top': leaderboard[:5],
            'top_points': DashboardStatsService.top_single_match_scores(tournament, limit=3),
            'top_winner_predictors': DashboardStatsService.top_winner_predictors(tournament, limit=3),
            'top_accuracy': DashboardStatsService.top_by_accuracy(leaderboard, limit=3),
            'top_mvps': DashboardStatsService.top_by_match_tops(leaderboard, limit=3),
            'top_matches_predicted': DashboardStatsService.top_by_matches_predicted(leaderboard, limit=3),
        }

    @staticmethod
    def _empty_stats():
        return {
            'recent_match_results': [],
            'leaderboard_top': [],
            'top_points': [],
            'top_winner_predictors': [],
            'top_accuracy': [],
            'top_mvps': [],
            'top_matches_predicted': [],
        }

    @staticmethod
    def recent_match_results(tournament, limit=5):
        matches = (
            Match.objects.filter(tournament=tournament)
            .select_related('team_home', 'team_away', 'round')
            .prefetch_related('questions__question_template')
            .order_by('-kickoff_at')
        )

        results = []
        for match in matches:
            if not match.is_completed:
                continue
            prediction_winners = DashboardStatsService._match_prediction_winners(match)
            results.append({
                'match': match,
                'home_score': match.display_home_score_line,
                'away_score': match.display_away_score_line,
                'prediction_winners': prediction_winners,
                'prediction_winners_label': DashboardStatsService._prediction_winners_label(prediction_winners),
                'prediction_winner_points': prediction_winners[0]['total_points'] if prediction_winners else None,
            })
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def top_winner_predictors(tournament, limit=3):
        rows = (
            QuestionPrediction.objects.filter(
                match_question__question_template__code='MATCH_WINNER',
                match_question__correct_answer__isnull=False,
                match_prediction__match__tournament=tournament,
            )
            .exclude(match_question__correct_answer='')
            .filter(user_answer=F('match_question__correct_answer'))
            .values('match_prediction__user__profile__display_name')
            .annotate(correct_count=Count('id'))
            .order_by('-correct_count', 'match_prediction__user__profile__display_name')[:limit]
        )
        return [
            {
                'display_name': row['match_prediction__user__profile__display_name'],
                'correct_count': row['correct_count'],
            }
            for row in rows
            if row['match_prediction__user__profile__display_name']
        ]

    @staticmethod
    def _match_prediction_winners(match):
        scorecard = MatchScorecardService.build(match)
        if not scorecard['is_scored'] or not scorecard['rows']:
            return []

        top_scorer_ids = MatchScorecardService.top_scorer_user_ids(scorecard['rows'])
        winners = [
            {
                'display_name': row['display_name'],
                'total_points': row['total_points'],
            }
            for row in scorecard['rows']
            if row['user_id'] in top_scorer_ids
        ]
        winners.sort(key=lambda row: row['display_name'].lower())
        return winners

    @staticmethod
    def _prediction_winners_label(winners):
        return ', '.join(winner['display_name'] for winner in winners)

    @staticmethod
    def top_single_match_scores(tournament, limit=3):
        predictions = (
            MatchPrediction.objects.filter(
                match__tournament=tournament,
                total_points__gt=0,
            )
            .select_related('user__profile', 'match')
            .order_by('-total_points', 'user__profile__display_name')[:limit]
        )
        return [
            {
                'display_name': prediction.user.profile.display_name,
                'total_points': prediction.total_points,
            }
            for prediction in predictions
            if prediction.user.profile.display_name
        ]

    @staticmethod
    def top_by_match_tops(leaderboard, limit=3):
        eligible = [row for row in leaderboard if row['match_tops'] > 0]
        return sorted(eligible, key=lambda row: row['match_tops'], reverse=True)[:limit]

    @staticmethod
    def top_by_accuracy(leaderboard, limit=3):
        eligible = [row for row in leaderboard if row['matches_predicted'] > 0]
        return sorted(eligible, key=lambda row: row['prediction_percentage'], reverse=True)[:limit]

    @staticmethod
    def top_by_matches_predicted(leaderboard, limit=3):
        return sorted(leaderboard, key=lambda row: row['matches_predicted'], reverse=True)[:limit]
