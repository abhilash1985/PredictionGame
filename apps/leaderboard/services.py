from collections import Counter, defaultdict

from django.db.models import Count, F, Sum

from apps.matches.models import Match, MatchPrediction, MatchQuestion, QuestionPrediction
from apps.tournaments.context_processors import get_active_tournament


class LeaderboardService:
    @staticmethod
    def user_stats(tournament=None):
        tournament = tournament or get_active_tournament()
        if not tournament:
            return []

        predictions = (
            MatchPrediction.objects.filter(match__tournament=tournament)
            .select_related('user', 'user__profile', 'match')
        )

        winner_picks_by_user = LeaderboardService._winner_picks_by_user(tournament)
        match_tops_by_user = LeaderboardService._match_tops_by_user(tournament)

        stats = defaultdict(lambda: {
            'display_name': '',
            'matches_predicted': 0,
            'total_points': 0,
            'max_points': 0,
            'boosters_used': 0,
            'winner_picks': 0,
            'match_tops': 0,
        })

        match_max_points = {}
        for match in Match.objects.filter(tournament=tournament).prefetch_related('questions'):
            match_max_points[match.id] = sum(q.points for q in match.questions.all())

        for pred in predictions:
            user_id = pred.user_id
            entry = stats[user_id]
            entry['display_name'] = pred.user.display_name
            entry['matches_predicted'] += 1
            entry['total_points'] += pred.total_points
            entry['max_points'] += match_max_points.get(pred.match_id, 0)
            if pred.point_booster_used:
                entry['boosters_used'] += 1

        results = []
        for user_id, entry in stats.items():
            percentage = 0
            if entry['max_points'] > 0:
                percentage = round(100 * entry['total_points'] / entry['max_points'], 2)
            results.append({
                'user_id': user_id,
                'display_name': entry['display_name'],
                'matches_predicted': entry['matches_predicted'],
                'total_points': entry['total_points'],
                'prediction_percentage': percentage,
                'boosters_used': entry['boosters_used'],
                'winner_picks': winner_picks_by_user.get(user_id, 0),
                'match_tops': match_tops_by_user.get(user_id, 0),
            })

        sorted_results = sorted(results, key=lambda row: row['total_points'], reverse=True)
        for index, row in enumerate(sorted_results, start=1):
            row['rank'] = index
        return sorted_results

    @staticmethod
    def user_row(user, tournament=None):
        for row in LeaderboardService.user_stats(tournament):
            if row['user_id'] == user.id:
                return row
        return None

    @staticmethod
    def _winner_picks_by_user(tournament):
        rows = (
            QuestionPrediction.objects.filter(
                match_question__question_template__code='MATCH_WINNER',
                match_question__correct_answer__isnull=False,
                match_prediction__match__tournament=tournament,
            )
            .exclude(match_question__correct_answer='')
            .filter(user_answer=F('match_question__correct_answer'))
            .values('match_prediction__user_id')
            .annotate(count=Count('id'))
        )
        return {row['match_prediction__user_id']: row['count'] for row in rows}

    @staticmethod
    def _match_tops_by_user(tournament):
        match_tops = defaultdict(int)
        matches = Match.objects.filter(tournament=tournament).prefetch_related('questions')

        for match in matches:
            if not any(question.correct_answer for question in match.questions.all()):
                continue

            predictions = list(
                MatchPrediction.objects.filter(match=match).values('user_id', 'total_points')
            )
            if not predictions:
                continue

            max_points = max(prediction['total_points'] for prediction in predictions)
            if max_points <= 0:
                continue

            for prediction in predictions:
                if prediction['total_points'] == max_points:
                    match_tops[prediction['user_id']] += 1

        return match_tops

    @staticmethod
    def team_points(tournament=None):
        tournament = tournament or get_active_tournament()
        if not tournament:
            return []

        from apps.accounts.models import UserProfile

        team_totals = (
            MatchPrediction.objects.filter(match__tournament=tournament, user__profile__favorite_team__isnull=False)
            .values('user__profile__favorite_team_id')
            .annotate(total_points=Sum('total_points'), fan_count=Count('user', distinct=True))
            .order_by('-total_points')
        )

        from apps.tournaments.models import Team

        team_ids = [row['user__profile__favorite_team_id'] for row in team_totals]
        teams_by_id = Team.objects.in_bulk(team_ids)

        results = []
        for row in team_totals:
            team = teams_by_id.get(row['user__profile__favorite_team_id'])
            results.append({
                'team': team,
                'total_points': row['total_points'],
                'fan_count': row['fan_count'],
            })
        return results

    @staticmethod
    def prediction_graph_data(tournament=None):
        tournament = tournament or get_active_tournament()
        if not tournament:
            return []

        questions = MatchQuestion.objects.filter(match__tournament=tournament).select_related('match')
        graph_data = []
        for question in questions:
            answers = question.predictions.values_list('user_answer', flat=True)
            counter = Counter(answers)
            graph_data.append({
                'question': question.question_text,
                'match': str(question.match),
                'labels': list(counter.keys()),
                'counts': list(counter.values()),
                'total': sum(counter.values()),
            })
        return graph_data
