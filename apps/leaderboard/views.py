from django.shortcuts import render

from apps.leaderboard.services import LeaderboardService
from apps.tournaments.context_processors import get_active_tournament


def leaderboard_view(request):
    tournament = get_active_tournament()
    rows = LeaderboardService.user_stats(tournament)
    return render(request, 'leaderboard/leaderboard.html', {
        'rows': rows,
        'tournament': tournament,
    })


def team_points_view(request):
    tournament = get_active_tournament()
    rows = LeaderboardService.team_points(tournament)
    return render(request, 'leaderboard/team_points.html', {
        'rows': rows,
        'tournament': tournament,
    })


def match_points_view(request):
    tournament = get_active_tournament()
    matrix = LeaderboardService.match_points_matrix(tournament)
    return render(request, 'leaderboard/match_points.html', {
        'match_columns': matrix['matches'],
        'rows': matrix['rows'],
        'tournament': tournament,
    })


def prediction_graph_view(request):
    tournament = get_active_tournament()
    matches = LeaderboardService.graph_match_choices(tournament)
    selected_match = None

    match_id = request.GET.get('match_id')
    if match_id:
        selected_match = matches.filter(pk=match_id).first()

    if not selected_match:
        selected_match = LeaderboardService.default_graph_match(tournament)

    graph_data = LeaderboardService.prediction_graph_data_for_match(selected_match)

    return render(request, 'leaderboard/graphs.html', {
        'matches': matches,
        'selected_match': selected_match,
        'graph_data': graph_data,
        'tournament': tournament,
    })
