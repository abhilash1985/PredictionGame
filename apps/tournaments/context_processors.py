from django.conf import settings
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.tournaments.services.standings import get_all_group_standings


def get_active_tournament():
    return Tournament.objects.filter(is_active=True).first()


def _site_url(request):
    if request.get_host():
        return request.build_absolute_uri('/').rstrip('/')
    host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
    scheme = 'https' if not settings.DEBUG else 'http'
    return f'{scheme}://{host}'


def site_context(request):
    adsense_active = (
        not settings.DEBUG
        and settings.GOOGLE_ADSENSE_ENABLED
        and bool(settings.GOOGLE_ADSENSE_CLIENT)
    )
    return {
        'site_name': settings.SITE_NAME,
        'site_contact_email': settings.SITE_CONTACT_EMAIL,
        'site_url': _site_url(request),
        'legal_last_updated': settings.LEGAL_LAST_UPDATED,
        'adsense_enabled': adsense_active,
        'adsense_client': settings.GOOGLE_ADSENSE_CLIENT if adsense_active else '',
        'adsense_slot_footer': settings.GOOGLE_ADSENSE_SLOT_FOOTER if adsense_active else '',
        'adsense_slot_sidebar': settings.GOOGLE_ADSENSE_SLOT_SIDEBAR if adsense_active else '',
    }


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
        Match.objects.filter(
            tournament=tournament,
            kickoff_at__gte=timezone.now(),
            round__name__startswith='Group ',
        )
        .select_related('team_home', 'team_away', 'stadium', 'round')
        .order_by('kickoff_at')[:limit]
    )
