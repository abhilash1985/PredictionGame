from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.leaderboard.services import LeaderboardService
from apps.matches.prediction_lookup import predicted_match_ids
from apps.tournaments.context_processors import get_active_tournament, get_upcoming_matches
from apps.tournaments.models import PastWorldCupWinner


def landing_view(request):
    tournament = get_active_tournament()
    winners = PastWorldCupWinner.objects.all()
    upcoming_matches = get_upcoming_matches(limit=10)
    leaderboard_top = LeaderboardService.user_stats(tournament)[:10]
    return render(request, 'tournaments/landing.html', {
        'winners': winners,
        'upcoming_matches': upcoming_matches,
        'tournament': tournament,
        'leaderboard_top': leaderboard_top,
        'predicted_match_ids': predicted_match_ids(request.user, upcoming_matches),
    })


@login_required
def dashboard_view(request):
    upcoming_matches = get_upcoming_matches(limit=20)
    return render(request, 'tournaments/dashboard.html', {
        'upcoming_matches': upcoming_matches,
        'predicted_match_ids': predicted_match_ids(request.user, upcoming_matches),
    })
