import random
from functools import lru_cache
from pathlib import Path

import yaml

from apps.matches.models import MatchQuestion, QuestionTemplate

BANK_PATH = Path(__file__).with_name('question_bank.yaml')

BASIC_CODES = ('MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS')
PLAYER_BUCKET = 'player'
STATS_BUCKETS = ('attacking', 'attempts', 'discipline', 'distribution', 'set_plays', 'defending', 'duels', 'goalkeeping')

DYNAMIC_OPTION_BUILDERS = {
    'home_away_draw_no_results': lambda match: [
        match.team_home.name,
        match.team_away.name,
        'Draw',
        'No Results',
    ],
    'squad_players': lambda match: _squad_player_names(match),
    'squad_players_with_no_goal': lambda match: _squad_player_names(match) + ['No goal'],
}


def _squad_player_names(match):
    players = list(match.team_home.players.filter(is_active=True)) + list(
        match.team_away.players.filter(is_active=True)
    )
    return [player.full_name for player in players]


@lru_cache(maxsize=1)
def load_question_bank():
    with BANK_PATH.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def bank_templates():
    return load_question_bank()['templates']


def template_by_code():
    return {template['code']: template for template in bank_templates()}


def templates_in_bucket(bucket):
    return [template for template in bank_templates() if template.get('bucket') == bucket]


def resolve_options(template_entry, match):
    options = template_entry.get('options')
    if isinstance(options, dict) and 'dynamic' in options:
        builder = DYNAMIC_OPTION_BUILDERS.get(options['dynamic'])
        if builder:
            return builder(match)
        return []

    if isinstance(options, list):
        return [str(option) for option in options]

    return []


def default_options_for_code(code, match):
    entry = template_by_code().get(code)
    if not entry:
        return []
    return resolve_options(entry, match)


def render_question_text(template_entry, match):
    return template_entry['question_text'].format(
        home_team=match.team_home.name,
        away_team=match.team_away.name,
    )


def select_match_template_codes(match, rng=None):
    """Return 7 template codes: 3 basic + 1 player + 3 stats (one per stats bucket)."""
    rng = rng or random.Random(match.pk)

    player_pool = templates_in_bucket(PLAYER_BUCKET)
    player_pick = rng.choice(player_pool)
    stats_buckets = list(STATS_BUCKETS)
    rng.shuffle(stats_buckets)
    selected_stats = []
    for bucket in stats_buckets[:3]:
        selected_stats.append(rng.choice(templates_in_bucket(bucket)))

    selected = (
        [template_by_code()[code] for code in BASIC_CODES]
        + [player_pick]
        + selected_stats
    )
    return [entry['code'] for entry in selected]


def sync_question_templates_from_bank():
    """Upsert all QuestionTemplate rows from the YAML bank."""
    synced = 0
    for entry in bank_templates():
        QuestionTemplate.objects.update_or_create(
            code=entry['code'],
            defaults={
                'question_text': entry['question_text'],
                'category': entry['category'],
                'default_points': entry['points'],
                'question_type': entry['question_type'],
                'is_active': True,
            },
        )
        synced += 1
    return synced


def create_match_question_pack(match, rng=None, replace_existing=False):
    """Create the standard 7-question pack for a match."""
    if replace_existing and match.questions.exists():
        match.questions.all().delete()

    if match.questions.exists():
        return 0

    codes = select_match_template_codes(match, rng=rng)
    bank = template_by_code()
    created = 0
    for sort_order, code in enumerate(codes):
        entry = bank[code]
        template, _created = QuestionTemplate.objects.get_or_create(
            code=code,
            defaults={
                'question_text': entry['question_text'],
                'category': entry['category'],
                'default_points': entry['points'],
                'question_type': entry['question_type'],
                'is_active': True,
            },
        )
        MatchQuestion.objects.create(
            match=match,
            question_template=template,
            question_text=render_question_text(entry, match),
            options=resolve_options(entry, match),
            points=entry['points'],
            sort_order=sort_order,
        )
        created += 1
    return created
