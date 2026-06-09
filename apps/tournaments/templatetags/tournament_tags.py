from django import template

from apps.leaderboard.services import LeaderboardService
from apps.tournaments.context_processors import get_active_tournament
from apps.tournaments.models import Team
from apps.tournaments.team_flags import flag_url_for_team

register = template.Library()

NON_TEAM_LABELS = frozenset({'Draw', 'No Results'})


@register.filter
def team_flag_url(team, size='w40'):
    return flag_url_for_team(team, size=size)


@register.filter
def team_flag_for_label(label):
    if not label or label in NON_TEAM_LABELS:
        return ''
    team = Team.objects.filter(name=label).first()
    if not team:
        team = Team.objects.filter(short_name=label).first()
    if team:
        return flag_url_for_team(team)
    return ''


@register.inclusion_tag('tournaments/partials/team_badge.html')
def team_badge(team, show_name=False, show_short=True, show_ranking=False):
    return {
        'team': team,
        'show_name': show_name,
        'show_short': show_short,
        'show_ranking': show_ranking,
    }


@register.inclusion_tag('tournaments/partials/leaderboard_top.html')
def leaderboard_top_preview(limit=10):
    tournament = get_active_tournament()
    if not tournament:
        return {'leaderboard_top': []}
    return {'leaderboard_top': LeaderboardService.user_stats(tournament)[:limit]}
