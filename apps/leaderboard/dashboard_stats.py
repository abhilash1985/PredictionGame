from datetime import datetime, time, timedelta
import zoneinfo

from django.db.models import Count, F
from django.utils import timezone

from apps.leaderboard.services import LeaderboardService
from apps.matches.models import Match, QuestionPrediction
from apps.tournaments.context_processors import get_active_tournament


class DashboardStatsService:
    @staticmethod
    def stats(tournament=None, user_timezone=None):
        tournament = tournament or get_active_tournament()
        if not tournament:
            return DashboardStatsService._empty_stats()

        leaderboard = LeaderboardService.user_stats(tournament)
        return {
            'previous_day_results': DashboardStatsService.previous_day_results(tournament, user_timezone),
            'leaderboard_top': leaderboard[:3],
            'top_points': leaderboard[:3],
            'top_winner_predictors': DashboardStatsService.top_winner_predictors(tournament, limit=3),
            'top_accuracy': DashboardStatsService.top_by_accuracy(leaderboard, limit=3),
            'top_matches_predicted': DashboardStatsService.top_by_matches_predicted(leaderboard, limit=3),
        }

    @staticmethod
    def _empty_stats():
        return {
            'previous_day_results': [],
            'leaderboard_top': [],
            'top_points': [],
            'top_winner_predictors': [],
            'top_accuracy': [],
            'top_matches_predicted': [],
        }

    @staticmethod
    def _resolve_timezone(user_timezone):
        if user_timezone:
            try:
                return zoneinfo.ZoneInfo(user_timezone)
            except zoneinfo.ZoneInfoNotFoundError:
                pass
        return timezone.get_current_timezone()

    @staticmethod
    def previous_day_results(tournament, user_timezone=None, limit=10):
        tz = DashboardStatsService._resolve_timezone(user_timezone)
        now_local = timezone.now().astimezone(tz)
        yesterday = now_local.date() - timedelta(days=1)
        start_local = datetime.combine(yesterday, time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        utc = zoneinfo.ZoneInfo('UTC')
        start_utc = start_local.astimezone(utc)
        end_utc = end_local.astimezone(utc)

        matches = (
            Match.objects.filter(
                tournament=tournament,
                kickoff_at__gte=start_utc,
                kickoff_at__lt=end_utc,
            )
            .select_related('team_home', 'team_away', 'round')
            .prefetch_related('questions__question_template')
            .order_by('kickoff_at')
        )

        results = []
        for match in matches:
            if not match.is_completed:
                continue
            results.append({
                'match': match,
                'winner': match.winning_team,
                'is_draw': match.is_draw,
                'home_score': match.display_home_score,
                'away_score': match.display_away_score,
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
    def top_by_accuracy(leaderboard, limit=3):
        eligible = [row for row in leaderboard if row['matches_predicted'] > 0]
        return sorted(eligible, key=lambda row: row['prediction_percentage'], reverse=True)[:limit]

    @staticmethod
    def top_by_matches_predicted(leaderboard, limit=3):
        return sorted(leaderboard, key=lambda row: row['matches_predicted'], reverse=True)[:limit]
