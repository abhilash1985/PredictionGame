from apps.matches.models import Match
from apps.tournaments.models import Team


def _empty_row(team):
    return {
        'team': team,
        'played': 0,
        'won': 0,
        'drawn': 0,
        'lost': 0,
        'goals_for': 0,
        'goals_against': 0,
        'goal_diff': 0,
        'points': 0,
    }


def _sort_key(row):
    return (-row['points'], -row['goal_diff'], -row['goals_for'], row['team'].name)


def compute_group_standings(tournament, group_letter):
    teams = list(Team.objects.filter(group_letter=group_letter.upper()).order_by('name'))
    rows = {team.id: _empty_row(team) for team in teams}

    matches = Match.objects.filter(
        tournament=tournament,
        status=Match.Status.FINISHED,
        round__name=f'Group {group_letter.upper()}',
    ).select_related('team_home', 'team_away')

    for match in matches:
        if match.home_score is None or match.away_score is None:
            continue

        home_row = rows.get(match.team_home_id)
        away_row = rows.get(match.team_away_id)
        if not home_row or not away_row:
            continue

        home_row['played'] += 1
        away_row['played'] += 1
        home_row['goals_for'] += match.home_score
        home_row['goals_against'] += match.away_score
        away_row['goals_for'] += match.away_score
        away_row['goals_against'] += match.home_score

        if match.home_score > match.away_score:
            home_row['won'] += 1
            away_row['lost'] += 1
            home_row['points'] += 3
        elif match.home_score < match.away_score:
            away_row['won'] += 1
            home_row['lost'] += 1
            away_row['points'] += 3
        else:
            home_row['drawn'] += 1
            away_row['drawn'] += 1
            home_row['points'] += 1
            away_row['points'] += 1

    for row in rows.values():
        row['goal_diff'] = row['goals_for'] - row['goals_against']

    return sorted(rows.values(), key=_sort_key)


def get_all_group_standings(tournament):
    if not tournament:
        return {}

    letters = (
        Team.objects.filter(group_letter__gt='')
        .values_list('group_letter', flat=True)
        .distinct()
        .order_by('group_letter')
    )
    return {letter: compute_group_standings(tournament, letter) for letter in letters}
