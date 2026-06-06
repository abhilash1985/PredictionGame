from django import template

from apps.tournaments.team_flags import flag_url_for_team

register = template.Library()


@register.filter
def team_flag_url(team, size='w40'):
    return flag_url_for_team(team, size=size)


@register.inclusion_tag('tournaments/partials/team_badge.html')
def team_badge(team, show_name=False):
    return {
        'team': team,
        'show_name': show_name,
    }
