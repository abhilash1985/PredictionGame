import logging
import random
import re

logger = logging.getLogger(__name__)

DRAW_LABEL = 'Draw'
NO_RESULTS_LABEL = 'No Results'
CORE_TEMPLATE_CODES = ('MATCH_WINNER', 'HOME_GOALS', 'AWAY_GOALS')


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
        return normalized

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
        return normalized

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

    return normalized
