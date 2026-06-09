from collections import Counter, defaultdict

from django.db.models import Count, F, Sum
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.matches.models import Match, MatchPrediction, MatchQuestion, QuestionPrediction, QuestionTemplate
from apps.tournaments.context_processors import get_active_tournament
from apps.tournaments.models import Team


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

        stats = {}
        for profile in UserProfile.objects.select_related('user').all():
            stats[profile.user_id] = {
                'display_name': profile.display_name,
                'matches_predicted': 0,
                'total_points': 0,
                'max_points': 0,
                'boosters_used': 0,
                'winner_picks': winner_picks_by_user.get(profile.user_id, 0),
                'match_tops': match_tops_by_user.get(profile.user_id, 0),
            }

        match_max_points = {}
        for match in Match.objects.filter(tournament=tournament).prefetch_related('questions'):
            match_max_points[match.id] = sum(q.points for q in match.questions.all())

        for pred in predictions:
            user_id = pred.user_id
            if user_id not in stats:
                continue
            entry = stats[user_id]
            entry['matches_predicted'] += 1
            entry['total_points'] += pred.total_points
            entry['max_points'] += match_max_points.get(pred.match_id, 0)
            if pred.point_booster_used:
                entry['boosters_used'] += 1
            entry['winner_picks'] = winner_picks_by_user.get(user_id, 0)
            entry['match_tops'] = match_tops_by_user.get(user_id, 0)

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
                'max_points': entry['max_points'],
                'prediction_percentage': percentage,
                'boosters_used': entry['boosters_used'],
                'winner_picks': winner_picks_by_user.get(user_id, 0),
                'match_tops': match_tops_by_user.get(user_id, 0),
            })

        sorted_results = sorted(
            results,
            key=lambda row: (-row['total_points'], row['display_name'].lower()),
        )
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

        fan_counts = (
            UserProfile.objects.filter(favorite_team__isnull=False)
            .values('favorite_team_id')
            .annotate(fan_count=Count('id'))
        )
        fan_count_by_team = {row['favorite_team_id']: row['fan_count'] for row in fan_counts}

        point_totals = (
            MatchPrediction.objects.filter(
                match__tournament=tournament,
                user__profile__favorite_team__isnull=False,
            )
            .values('user__profile__favorite_team_id')
            .annotate(total_points=Sum('total_points'))
        )
        points_by_team = {
            row['user__profile__favorite_team_id']: row['total_points'] or 0
            for row in point_totals
        }

        team_ids = set(fan_count_by_team.keys()) | set(points_by_team.keys())
        teams_by_id = Team.objects.in_bulk(team_ids)

        results = []
        for team_id in team_ids:
            team = teams_by_id.get(team_id)
            if not team:
                continue
            results.append({
                'team': team,
                'total_points': points_by_team.get(team_id, 0),
                'fan_count': fan_count_by_team.get(team_id, 0),
            })

        return sorted(
            results,
            key=lambda row: (-row['total_points'], -row['fan_count'], row['team'].name.lower()),
        )

    @staticmethod
    def graph_match_choices(tournament=None):
        tournament = tournament or get_active_tournament()
        if not tournament:
            return Match.objects.none()

        return (
            Match.objects.filter(tournament=tournament)
            .select_related('team_home', 'team_away', 'round', 'stadium')
            .annotate(prediction_count=Count('predictions'))
            .order_by('kickoff_at', 'match_number')
        )

    @staticmethod
    def default_graph_match(tournament=None):
        matches = LeaderboardService.graph_match_choices(tournament)
        upcoming = matches.filter(kickoff_at__gte=timezone.now()).first()
        if upcoming:
            return upcoming
        return matches.first()

    @staticmethod
    def prediction_graph_data_for_match(match):
        if not match:
            return []

        graph_data = []
        questions = match.questions.select_related('question_template').order_by('sort_order', 'id')
        for question in questions:
            answers = (
                question.predictions
                .exclude(user_answer='')
                .values_list('user_answer', flat=True)
            )
            counter = Counter(answers)
            labels, counts = LeaderboardService._graph_labels_from_answers(question, counter)
            template = question.question_template
            chart_type = LeaderboardService._chart_type_for_question(template)
            graph_data.append({
                'question_id': question.id,
                'question': question.question_text,
                'labels': labels,
                'counts': counts,
                'total': sum(counts),
                'points': question.points,
                'chart_type': chart_type,
                'chart_label': LeaderboardService._chart_label_for_type(chart_type),
            })
        return graph_data

    @staticmethod
    def _graph_labels_from_answers(question, counter):
        template = question.question_template
        if question.options:
            labels = [str(option) for option in question.options]
            counts = [counter.get(label, 0) for label in labels]
            if template and template.question_type == QuestionTemplate.QuestionType.NUMERIC:
                pairs = sorted(
                    zip(labels, counts),
                    key=lambda pair: (LeaderboardService._numeric_sort_key(pair[0]), pair[0].lower()),
                )
                labels, counts = zip(*pairs)
                return list(labels), list(counts)
            return labels, counts

        return LeaderboardService._sorted_graph_labels(counter, template)

    @staticmethod
    def _sorted_graph_labels(counter, template):
        labels = list(counter.keys())
        counts = [counter[label] for label in labels]
        if not labels:
            return [], []

        if template and template.question_type == QuestionTemplate.QuestionType.NUMERIC:
            pairs = sorted(
                zip(labels, counts),
                key=lambda pair: (LeaderboardService._numeric_sort_key(pair[0]), pair[0].lower()),
            )
            labels, counts = zip(*pairs)
            return list(labels), list(counts)

        pairs = sorted(zip(labels, counts), key=lambda pair: (-pair[1], pair[0].lower()))
        labels, counts = zip(*pairs)
        return list(labels), list(counts)

    @staticmethod
    def _numeric_sort_key(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return float('inf')

    @staticmethod
    def _chart_type_for_question(template):
        if not template:
            return 'bar'

        if template.code == 'MATCH_WINNER' or template.category == QuestionTemplate.Category.WINNER:
            return 'doughnut'

        if template.question_type == QuestionTemplate.QuestionType.NUMERIC:
            return 'bar'

        if template.question_type == QuestionTemplate.QuestionType.PLAYER_PICK:
            return 'horizontalBar'

        if template.category in {QuestionTemplate.Category.GOALS, QuestionTemplate.Category.STATS}:
            return 'bar'

        if template.category == QuestionTemplate.Category.PLAYER:
            return 'horizontalBar'

        return 'polarArea'

    @staticmethod
    def _chart_label_for_type(chart_type):
        labels = {
            'doughnut': 'Pie chart',
            'bar': 'Bar chart',
            'horizontalBar': 'Horizontal bar',
            'polarArea': 'Polar chart',
        }
        return labels.get(chart_type, 'Chart')
