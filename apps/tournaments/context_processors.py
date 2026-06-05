from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.tournaments.services.standings import get_all_group_standings


def get_active_tournament():
    return Tournament.objects.filter(is_active=True).first()


def tournament_context(request):
    return {
        'active_tournament': get_active_tournament(),
    }


def standings_context(request):
    tournament = get_active_tournament()
    group_standings = get_all_group_standings(tournament)
    group_letters = sorted(group_standings.keys())
    return {
        'group_standings_list': [(letter, group_standings[letter]) for letter in group_letters],
    }


def get_upcoming_matches(limit=10):
    from apps.matches.models import Match

    tournament = get_active_tournament()
    if not tournament:
        return Match.objects.none()

    return (
        Match.objects.filter(tournament=tournament, kickoff_at__gte=timezone.now())
        .select_related('team_home', 'team_away', 'stadium', 'round')
        .order_by('kickoff_at')[:limit]
    )
