import logging
import random
import re

logger = logging.getLogger(__name__)

DRAW_LABEL = 'Draw'
NO_RESULTS_LABEL = 'No Results'
NO_GOAL_LABEL = 'No goal'
NO_GOALS_LABEL = 'No Goals'
NO_GOALS_POSITION_LABEL = 'No goals'
CORE_TEMPLATE_CODES = ('MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS')

# --- Knockout-specific coherence ---
KNOCKOUT_DECISION_CODE = 'GAME_COMPLETED_IN'
KNOCKOUT_SHOOTOUT_TOTAL_CODE = 'TOTAL_PENALTY_SHOOTOUT_GOALS'
KNOCKOUT_EXCL_CODES = {
    'home': 'HOME_GOALS_EXCL_SHOOTOUT',
    'away': 'AWAY_GOALS_EXCL_SHOOTOUT',
    'total': 'TOTAL_GOALS_EXCL_SHOOTOUT',
}
KNOCKOUT_INCL_CODES = {
    'home': 'HOME_GOALS_INCL_SHOOTOUT',
    'away': 'AWAY_GOALS_INCL_SHOOTOUT',
    'total': 'TOTAL_GOALS_INCL_SHOOTOUT',
}
DECISION_FULL_TIME = 'Full Time'
DECISION_EXTRA_TIME = 'Extra Time'
DECISION_PENALTIES = 'Penalties'
NO_SHOOTOUT_FULL_TIME_LABEL = 'No shootout (decided in full time)'
NO_SHOOTOUT_EXTRA_TIME_LABEL = 'No shootout (decided in extra time)'
SHOOTOUT_SCORELINES = ((4, 3), (5, 4), (5, 3), (3, 2), (4, 2))
FIRST_GOAL_TEMPLATE_CODES = (
    'FIRST_GOAL_TEAM',
    'FIRST_GOAL_SCORER',
    'FIRST_GOAL_MINUTE',
    'FIRST_GOAL_TYPE',
    'FIRST_GOAL_POSITION',
    'FIRST_ASSIST_PROVIDER',
)


def questions_by_code(questions):
    mapping = {}
    for question in questions:
        template = question.question_template
        if template:
            mapping[template.code] = question
    return mapping


def core_questions_by_code(questions):
    mapping = {}
    for question in questions:
        template = question.question_template
        if template and template.code in CORE_TEMPLATE_CODES:
            mapping[template.code] = question
    return mapping


def parse_goal_value(option):
    if option is None:
        return None
    text = str(option).strip()
    plus_match = re.fullmatch(r'(\d+)\+', text)
    if plus_match:
        return int(plus_match.group(1))
    try:
        return int(text)
    except ValueError:
        return None


def format_goal_value(value, options):
    numeric_options = []
    for option in options:
        parsed = parse_goal_value(option)
        if parsed is not None:
            numeric_options.append((option, parsed))

    if not numeric_options:
        return str(value)

    for option, parsed in numeric_options:
        if parsed == value:
            return option

    plus_options = [(option, parsed) for option, parsed in numeric_options if str(option).endswith('+')]
    if plus_options and value >= max(parsed for _, parsed in plus_options):
        return max(plus_options, key=lambda item: item[1])[0]

    closest = min(numeric_options, key=lambda item: (abs(item[1] - value), item[1]))
    return closest[0]


def winner_side(winner, match):
    if winner == DRAW_LABEL:
        return 'draw'
    if winner == match.team_home.name:
        return 'home'
    if winner == match.team_away.name:
        return 'away'
    return None


def goals_consistent_with_winner(winner, home_goals, away_goals, match):
    side = winner_side(winner, match)
    if side is None:
        return False
    if side == 'draw':
        return home_goals == away_goals
    if side == 'home':
        return home_goals > away_goals
    return away_goals > home_goals


def infer_first_goal_team(winner, home_goals, away_goals, match, rng):
    home_name = match.team_home.name
    away_name = match.team_away.name

    if home_goals == 0 and away_goals == 0:
        return DRAW_LABEL

    if away_goals == 0:
        return home_name
    if home_goals == 0:
        return away_name

    if winner == home_name:
        return home_name if rng.random() < 0.7 else away_name
    if winner == away_name:
        return away_name if rng.random() < 0.7 else home_name
    return rng.choice([home_name, away_name])


def pick_player_from_team(match, team_side, rng):
    team = match.team_home if team_side == 'home' else match.team_away
    players = list(team.players.filter(is_active=True))
    if not players:
        return None
    return rng.choice(players).full_name


def normalize_related_answers(questions, normalized, match, rng):
    by_code = questions_by_code(questions)
    core = core_questions_by_code(questions)
    winner_question = core.get('MATCH_WINNER')
    home_question = core.get('HOME_GOALS')
    away_question = core.get('AWAY_GOALS')
    if not winner_question or not home_question or not away_question:
        return normalized

    winner = normalized.get(winner_question.pk)
    home_goals = parse_goal_value(normalized.get(home_question.pk))
    away_goals = parse_goal_value(normalized.get(away_question.pk))
    if home_goals is None or away_goals is None:
        return normalized

    total = home_goals + away_goals
    first_goal_team_question = by_code.get('FIRST_GOAL_TEAM')
    first_goal_team = None
    if first_goal_team_question:
        options = first_goal_team_question.options or []
        first_goal_team = infer_first_goal_team(winner, home_goals, away_goals, match, rng)
        if first_goal_team not in options:
            pickable = [option for option in options if option not in {NO_RESULTS_LABEL}]
            first_goal_team = pickable[0] if pickable else first_goal_team
        normalized[first_goal_team_question.pk] = first_goal_team

    if total == 0:
        if by_code.get('FIRST_GOAL_SCORER'):
            q = by_code['FIRST_GOAL_SCORER']
            if NO_GOAL_LABEL in (q.options or []):
                normalized[q.pk] = NO_GOAL_LABEL
        if by_code.get('FIRST_GOAL_MINUTE'):
            q = by_code['FIRST_GOAL_MINUTE']
            if NO_GOALS_LABEL in (q.options or []):
                normalized[q.pk] = NO_GOALS_LABEL
        if by_code.get('FIRST_GOAL_TYPE'):
            q = by_code['FIRST_GOAL_TYPE']
            if NO_GOALS_LABEL in (q.options or []):
                normalized[q.pk] = NO_GOALS_LABEL
        if by_code.get('FIRST_GOAL_POSITION'):
            q = by_code['FIRST_GOAL_POSITION']
            if NO_GOALS_POSITION_LABEL in (q.options or []):
                normalized[q.pk] = NO_GOALS_POSITION_LABEL
        if by_code.get('FIRST_ASSIST_PROVIDER'):
            q = by_code['FIRST_ASSIST_PROVIDER']
            if NO_GOAL_LABEL in (q.options or []):
                normalized[q.pk] = NO_GOAL_LABEL
        return normalized

    if first_goal_team and first_goal_team not in {DRAW_LABEL, NO_RESULTS_LABEL}:
        team_side = 'home' if first_goal_team == match.team_home.name else 'away'
        scorer_name = pick_player_from_team(match, team_side, rng)
        if by_code.get('FIRST_GOAL_SCORER') and scorer_name:
            q = by_code['FIRST_GOAL_SCORER']
            if scorer_name in (q.options or []):
                normalized[q.pk] = scorer_name

    if by_code.get('FIRST_GOAL_MINUTE'):
        q = by_code['FIRST_GOAL_MINUTE']
        minute_options = [option for option in (q.options or []) if option != NO_GOALS_LABEL]
        if minute_options and normalized.get(q.pk) in {NO_GOALS_LABEL, None}:
            normalized[q.pk] = rng.choice(minute_options)

    if by_code.get('FIRST_GOAL_TYPE'):
        q = by_code['FIRST_GOAL_TYPE']
        type_options = [option for option in (q.options or []) if option != NO_GOALS_LABEL]
        if type_options and normalized.get(q.pk) in {NO_GOALS_LABEL, None}:
            normalized[q.pk] = rng.choice(type_options)

    if by_code.get('FIRST_GOAL_POSITION'):
        q = by_code['FIRST_GOAL_POSITION']
        position_options = [option for option in (q.options or []) if option != NO_GOALS_POSITION_LABEL]
        if position_options and normalized.get(q.pk) in {NO_GOALS_POSITION_LABEL, None}:
            normalized[q.pk] = rng.choice(position_options)

    total_goals_question = by_code.get('TOTAL_GOALS')
    if total_goals_question:
        options = total_goals_question.options or []
        normalized[total_goals_question.pk] = format_goal_value(total, options)

    over_under_question = by_code.get('OVER_UNDER_2_5')
    if over_under_question:
        options = over_under_question.options or []
        over_under_answer = 'Over 2.5 goals' if total >= 3 else 'Under 2.5 goals'
        if over_under_answer in options:
            normalized[over_under_question.pk] = over_under_answer

    return normalized


def infer_winner_from_match(match, user=None, rng=None):
    randomizer = rng or random.Random()
    home_rank = match.team_home.fifa_ranking or 50
    away_rank = match.team_away.fifa_ranking or 50
    home_name = match.team_home.name
    away_name = match.team_away.name
    rank_gap = abs(home_rank - away_rank)

    favorite_name = None
    if user is not None and hasattr(user, 'profile'):
        favorite = user.profile.favorite_team
        favorite_name = favorite.name if favorite else None

    if favorite_name in {home_name, away_name} and rank_gap <= 12:
        return favorite_name

    if rank_gap <= 4:
        return DRAW_LABEL if randomizer.random() < 0.45 else (home_name if home_rank <= away_rank else away_name)

    if home_rank < away_rank:
        return home_name
    if away_rank < home_rank:
        return away_name
    return DRAW_LABEL


def suggest_scoreline(winner, match, rng):
    home_rank = match.team_home.fifa_ranking or 50
    away_rank = match.team_away.fifa_ranking or 50
    rank_gap = abs(home_rank - away_rank)

    if winner == DRAW_LABEL:
        draw_scores = [(0, 0), (1, 1), (2, 2)] if rank_gap <= 10 else [(0, 0), (1, 1)]
        return rng.choice(draw_scores)

    if winner == match.team_home.name:
        if rank_gap >= 20:
            pairs = [(2, 0), (3, 0), (3, 1), (2, 1)]
        elif rank_gap >= 8:
            pairs = [(2, 1), (1, 0), (2, 0), (3, 1)]
        else:
            pairs = [(2, 1), (1, 0), (3, 2), (2, 0)]
        return rng.choice(pairs)

    if rank_gap >= 20:
        pairs = [(0, 2), (0, 3), (1, 3), (1, 2)]
    elif rank_gap >= 8:
        pairs = [(1, 2), (0, 1), (0, 2), (1, 3)]
    else:
        pairs = [(1, 2), (2, 3), (0, 1), (1, 3)]
    return rng.choice(pairs)


def pick_goal_pair_for_winner(winner, home_question, away_question, match, rng, preferred_home=None, preferred_away=None):
    home_options = home_question.options or []
    away_options = away_question.options or []
    home_target, away_target = suggest_scoreline(winner, match, rng)

    if preferred_home is not None and preferred_away is not None:
        side = winner_side(winner, match)
        if side == 'draw' and preferred_home != preferred_away:
            home_target, away_target = suggest_scoreline(DRAW_LABEL, match, rng)
        elif side == 'home' and preferred_home <= preferred_away:
            home_target, away_target = suggest_scoreline(winner, match, rng)
        elif side == 'away' and preferred_away <= preferred_home:
            home_target, away_target = suggest_scoreline(winner, match, rng)
        else:
            home_target, away_target = preferred_home, preferred_away

    return (
        format_goal_value(home_target, home_options),
        format_goal_value(away_target, away_options),
    )


def generate_coherent_core_answers(match, questions, user=None, rng=None):
    randomizer = rng or random.Random()
    core = core_questions_by_code(questions)
    winner_question = core.get('MATCH_WINNER')
    home_question = core.get('HOME_GOALS')
    away_question = core.get('AWAY_GOALS')
    if not winner_question or not home_question or not away_question:
        return {}

    winner_options = [
        option for option in (winner_question.options or [])
        if option not in {NO_RESULTS_LABEL}
    ]
    winner = infer_winner_from_match(match, user=user, rng=randomizer)
    if winner not in winner_options:
        winner = winner_options[0] if winner_options else winner

    home_answer, away_answer = pick_goal_pair_for_winner(
        winner,
        home_question,
        away_question,
        match,
        randomizer,
    )

    return {
        winner_question.pk: winner,
        home_question.pk: home_answer,
        away_question.pk: away_answer,
    }


def normalize_core_answers(questions, answers, match, user=None, rng=None):
    if not answers:
        return answers

    randomizer = rng or random.Random()
    normalized = dict(answers)
    core = core_questions_by_code(questions)
    winner_question = core.get('MATCH_WINNER')
    home_question = core.get('HOME_GOALS')
    away_question = core.get('AWAY_GOALS')
    if not winner_question or not home_question or not away_question:
        return normalize_knockout_answers(questions, normalized, match, randomizer)

    winner_options = list(winner_question.options or [])
    pickable_winners = [option for option in winner_options if option != NO_RESULTS_LABEL]

    winner = normalized.get(winner_question.pk)
    home_raw = normalized.get(home_question.pk)
    away_raw = normalized.get(away_question.pk)
    home_goals = parse_goal_value(home_raw)
    away_goals = parse_goal_value(away_raw)

    if winner == NO_RESULTS_LABEL or winner not in winner_options:
        winner = infer_winner_from_match(match, user=user, rng=randomizer)
        if winner not in pickable_winners:
            winner = pickable_winners[0] if pickable_winners else winner
        normalized[winner_question.pk] = winner

    if home_goals is None or away_goals is None:
        home_answer, away_answer = pick_goal_pair_for_winner(
            normalized[winner_question.pk],
            home_question,
            away_question,
            match,
            randomizer,
        )
        normalized[home_question.pk] = home_answer
        normalized[away_question.pk] = away_answer
        normalized = normalize_related_answers(questions, normalized, match, randomizer)
        return normalize_knockout_answers(questions, normalized, match, randomizer)

    if not goals_consistent_with_winner(normalized[winner_question.pk], home_goals, away_goals, match):
        logger.info(
            'Adjusting inconsistent AI core answers for match=%s winner=%r goals=%s-%s',
            match.pk,
            normalized[winner_question.pk],
            home_raw,
            away_raw,
        )
        home_answer, away_answer = pick_goal_pair_for_winner(
            normalized[winner_question.pk],
            home_question,
            away_question,
            match,
            randomizer,
            preferred_home=home_goals,
            preferred_away=away_goals,
        )
        normalized[home_question.pk] = home_answer
        normalized[away_question.pk] = away_answer

    normalized = normalize_related_answers(questions, normalized, match, randomizer)
    return normalize_knockout_answers(questions, normalized, match, randomizer)


def range_option_for_count(value, options):
    """Pick the option whose numeric range/threshold contains value, ignoring non-numeric labels."""
    numeric_spans = []
    plus_options = []
    for option in options:
        text = str(option).strip()
        range_match = re.fullmatch(r'(\d+)\s*-\s*(\d+)', text)
        if range_match:
            low, high = int(range_match.group(1)), int(range_match.group(2))
            if low <= value <= high:
                return option
            numeric_spans.append((option, low, high))
            continue
        plus_match = re.fullmatch(r'(\d+)\+', text)
        if plus_match:
            plus_options.append((option, int(plus_match.group(1))))
            continue
        int_match = re.fullmatch(r'\d+', text)
        if int_match:
            number = int(text)
            if number == value:
                return option
            numeric_spans.append((option, number, number))

    applicable_plus = [(option, threshold) for option, threshold in plus_options if value >= threshold]
    if applicable_plus:
        return max(applicable_plus, key=lambda item: item[1])[0]

    if numeric_spans:
        return min(numeric_spans, key=lambda item: abs(((item[1] + item[2]) / 2) - value))[0]

    return None


def _set_count_option(normalized, question, value):
    if not question:
        return
    option = range_option_for_count(value, question.options or [])
    if option is not None:
        normalized[question.pk] = option


def _set_exact_option(normalized, question, label, fallback_exclude=(NO_RESULTS_LABEL,)):
    if not question:
        return
    options = question.options or []
    if label in options:
        normalized[question.pk] = label
        return
    pickable = [option for option in options if option not in fallback_exclude]
    if pickable:
        normalized[question.pk] = pickable[0]


def normalize_knockout_answers(questions, normalized, match, rng):
    """Make knockout-only answers (decision method, extra-time/shootout goals) coherent with the winner."""
    by_code = questions_by_code(questions)
    decision_question = by_code.get(KNOCKOUT_DECISION_CODE)
    shootout_question = by_code.get(KNOCKOUT_SHOOTOUT_TOTAL_CODE)
    excl_questions = {side: by_code.get(code) for side, code in KNOCKOUT_EXCL_CODES.items()}
    incl_questions = {side: by_code.get(code) for side, code in KNOCKOUT_INCL_CODES.items()}

    knockout_present = (
        decision_question
        or shootout_question
        or any(excl_questions.values())
        or any(incl_questions.values())
    )
    if not knockout_present:
        return normalized

    home_name = match.team_home.name
    away_name = match.team_away.name

    winner_question = by_code.get('MATCH_WINNER')
    home_question = by_code.get('HOME_GOALS')
    away_question = by_code.get('AWAY_GOALS')

    winner = normalized.get(winner_question.pk) if winner_question else None
    home_goals = parse_goal_value(normalized.get(home_question.pk)) if home_question else None
    away_goals = parse_goal_value(normalized.get(away_question.pk)) if away_question else None

    if home_goals is None or away_goals is None:
        seed_winner = winner if winner in {home_name, away_name, DRAW_LABEL} else infer_winner_from_match(match, rng=rng)
        home_goals, away_goals = suggest_scoreline(seed_winner, match, rng)

    if winner == home_name:
        winner_side_value = 'home'
    elif winner == away_name:
        winner_side_value = 'away'
    elif home_goals > away_goals:
        winner_side_value = 'home'
    elif away_goals > home_goals:
        winner_side_value = 'away'
    else:
        home_rank = match.team_home.fifa_ranking or 50
        away_rank = match.team_away.fifa_ranking or 50
        winner_side_value = 'home' if home_rank <= away_rank else 'away'

    # A knockout match must produce an eventual winner: a level scoreline goes to penalties.
    decision = DECISION_PENALTIES if home_goals == away_goals else DECISION_FULL_TIME

    # Resolve a Draw/No Results winner into the team that advances.
    if winner_question:
        eventual_winner_name = home_name if winner_side_value == 'home' else away_name
        if normalized.get(winner_question.pk) in {DRAW_LABEL, NO_RESULTS_LABEL, None}:
            if eventual_winner_name in (winner_question.options or []):
                normalized[winner_question.pk] = eventual_winner_name

    winner_pens = loser_pens = 0
    if decision == DECISION_PENALTIES:
        winner_pens, loser_pens = rng.choice(SHOOTOUT_SCORELINES)

    home_pens = winner_pens if winner_side_value == 'home' else loser_pens
    away_pens = winner_pens if winner_side_value == 'away' else loser_pens

    _set_count_option(normalized, excl_questions['home'], home_goals)
    _set_count_option(normalized, excl_questions['away'], away_goals)
    _set_count_option(normalized, excl_questions['total'], home_goals + away_goals)

    if decision_question:
        _set_exact_option(normalized, decision_question, decision)

    if shootout_question:
        if decision == DECISION_PENALTIES:
            _set_count_option(normalized, shootout_question, winner_pens + loser_pens)
        elif decision == DECISION_EXTRA_TIME:
            _set_exact_option(normalized, shootout_question, NO_SHOOTOUT_EXTRA_TIME_LABEL)
        else:
            _set_exact_option(normalized, shootout_question, NO_SHOOTOUT_FULL_TIME_LABEL)

    incl_home = home_goals + home_pens
    incl_away = away_goals + away_pens
    _set_count_option(normalized, incl_questions['home'], incl_home)
    _set_count_option(normalized, incl_questions['away'], incl_away)
    _set_count_option(normalized, incl_questions['total'], incl_home + incl_away)

    return normalized
