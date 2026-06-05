from django.shortcuts import render
from django.utils.safestring import mark_safe
import json

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


def prediction_graph_view(request):
    tournament = get_active_tournament()
    graph_data = LeaderboardService.prediction_graph_data(tournament)
    return render(request, 'leaderboard/graphs.html', {
        'graph_data': graph_data,
        'graph_data_json': mark_safe(json.dumps(graph_data)),
        'tournament': tournament,
    })
