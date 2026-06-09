from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from apps.leaderboard.dashboard_stats import DashboardStatsService
from apps.leaderboard.services import LeaderboardService
from apps.matches.models import Match
from apps.matches.prediction_lookup import predicted_match_ids
from apps.matches.scorecard_service import MatchScorecardService
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
    tournament = get_active_tournament()
    upcoming_matches = (
        get_upcoming_matches(limit=20)
        .prefetch_related('questions__question_template')
        .annotate(prediction_count=Count('predictions'))
    )
    user_timezone = ''
    if hasattr(request.user, 'profile'):
        user_timezone = request.user.profile.timezone or ''

    verdict_matches = Match.objects.none()
    selected_verdict_match = None
    verdict_context = None
    verdict_error = None

    if tournament:
        verdict_matches = (
            Match.objects.filter(tournament=tournament, round__name__startswith='Group ')
            .select_related('team_home', 'team_away', 'round', 'stadium')
            .prefetch_related('questions__question_template')
            .annotate(prediction_count=Count('predictions'))
            .order_by('kickoff_at')
        )

        verdict_match_id = request.GET.get('verdict_match')
        if verdict_match_id:
            selected_verdict_match = verdict_matches.filter(pk=verdict_match_id).first()
            if not selected_verdict_match:
                verdict_error = 'Select a valid match.'
            elif selected_verdict_match.prediction_count == 0:
                verdict_error = 'No predictions submitted for this match yet.'
            else:
                verdict_context = MatchScorecardService.context_for_match(
                    selected_verdict_match,
                    request.user,
                )
                if not verdict_context['rows']:
                    verdict_error = 'You have not predicted this match yet.'
                    verdict_context = None

    return render(request, 'tournaments/dashboard.html', {
        'tournament': tournament,
        'upcoming_matches': upcoming_matches,
        'predicted_match_ids': predicted_match_ids(request.user, upcoming_matches),
        'dashboard_stats': DashboardStatsService.stats(tournament, user_timezone),
        'show_predict': True,
        'verdict_matches': verdict_matches,
        'selected_verdict_match': selected_verdict_match,
        'verdict_context': verdict_context,
        'verdict_error': verdict_error,
        'open_verdict_tab': bool(request.GET.get('verdict_match')),
    })
