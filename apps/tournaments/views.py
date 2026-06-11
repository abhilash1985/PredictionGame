from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils import timezone

# Google AdSense ads.txt certification authority ID (standard value).
ADSENSE_CERT_AUTHORITY_ID = 'f08c47fec0942fa0'

from apps.leaderboard.dashboard_stats import DashboardStatsService
from apps.leaderboard.services import LeaderboardService
from apps.matches.models import Match
from apps.matches.prediction_lookup import predicted_match_ids
from apps.matches.scorecard_service import MatchScorecardService
from apps.tournaments.context_processors import get_active_tournament, get_upcoming_matches
from apps.tournaments.models import PastWorldCupWinner


def default_verdict_match(verdict_matches):
    past_matches = verdict_matches.filter(kickoff_at__lt=timezone.now()).order_by('-kickoff_at', '-match_number')
    return past_matches.filter(prediction_count__gt=0).first() or past_matches.first()


def verdict_context_for_user(match, user):
    if not match:
        return None, None
    if match.prediction_count == 0:
        return None, 'No predictions submitted for this match yet.'
    verdict_context = MatchScorecardService.context_for_match(match, user)
    if not verdict_context['rows']:
        return None, 'You have not predicted this match yet.'
    return verdict_context, None


def _adsense_publisher_id():
    client = (settings.GOOGLE_ADSENSE_CLIENT or '').strip()
    if not client:
        return ''
    if client.startswith('ca-'):
        return client[3:]
    if client.startswith('pub-'):
        return client
    return f'pub-{client}'


def ads_txt_view(request):
    """
    Serve /ads.txt for Google AdSense authorization.
    Requires GOOGLE_ADSENSE_CLIENT (ca-pub-... or pub-...) in environment.
    """
    publisher_id = _adsense_publisher_id()
    if not publisher_id:
        return HttpResponseNotFound('ads.txt is not configured.\n')

    body = f'google.com, {publisher_id}, DIRECT, {ADSENSE_CERT_AUTHORITY_ID}\n'
    return HttpResponse(body, content_type='text/plain; charset=utf-8')


def _legal_page_context(page_title, page_subtitle=''):
    return {
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'last_updated': settings.LEGAL_LAST_UPDATED,
    }


def privacy_policy_view(request):
    return render(
        request,
        'pages/privacy_policy.html',
        _legal_page_context(
            'Privacy Policy',
            'How we collect, use, and protect your information — including cookies and advertising.',
        ),
    )


def about_view(request):
    return render(
        request,
        'pages/about.html',
        _legal_page_context(
            'About',
            'Free FIFA World Cup 2026 fantasy predictions — no real-money betting.',
        ),
    )


def contact_view(request):
    return render(
        request,
        'pages/contact.html',
        _legal_page_context(
            'Contact',
            'Support, feedback, and privacy requests.',
        ),
    )


def landing_view(request):
    tournament = get_active_tournament()
    winners = PastWorldCupWinner.objects.all()
    upcoming_matches = (
        get_upcoming_matches(limit=6)
        .annotate(prediction_count=Count('predictions'))
    )
    leaderboard_top = LeaderboardService.user_stats(tournament)[:10]
    recent_match_results = DashboardStatsService.recent_match_results(tournament)
    return render(request, 'tournaments/landing.html', {
        'winners': winners,
        'upcoming_matches': upcoming_matches,
        'tournament': tournament,
        'leaderboard_top': leaderboard_top,
        'recent_match_results': recent_match_results,
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
        else:
            selected_verdict_match = default_verdict_match(verdict_matches)

        if selected_verdict_match and not verdict_error:
            verdict_context, verdict_error = verdict_context_for_user(selected_verdict_match, request.user)

    leaderboard_rows = LeaderboardService.user_stats(tournament)
    user_leaderboard = next(
        (row for row in leaderboard_rows if row['user_id'] == request.user.id),
        None,
    )
    tab = request.GET.get('tab')

    return render(request, 'tournaments/dashboard.html', {
        'tournament': tournament,
        'upcoming_matches': upcoming_matches,
        'predicted_match_ids': predicted_match_ids(request.user, upcoming_matches),
        'dashboard_stats': DashboardStatsService.stats(tournament, user_timezone),
        'user_leaderboard': user_leaderboard,
        'leaderboard_total': len(leaderboard_rows),
        'show_predict': True,
        'verdict_matches': verdict_matches,
        'selected_verdict_match': selected_verdict_match,
        'verdict_context': verdict_context,
        'verdict_error': verdict_error,
        'open_stats_tab': tab == 'stats',
        'open_verdict_tab': bool(request.GET.get('verdict_match')) or tab == 'verdict',
        'open_matches_tab': tab == 'matches',
    })
