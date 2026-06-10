# FIFA 2026 Prediction Game — Question Bank

Reusable prediction questions for group-stage matches. Each template becomes a per-match `MatchQuestion` with options filled in at match setup time (team names, squad players, etc.).

## How templates map to the app

| Field | Purpose |
|-------|---------|
| `code` | Unique identifier (used by scoring, AI predict, graphs) |
| `question_text` | Supports `{home_team}` and `{away_team}` placeholders |
| `question_type` | `choice`, `numeric`, or `player_pick` (affects graph layout) |
| `category` | `winner`, `goals`, `player`, `stats`, or `random` |
| `default_points` | Suggested weight; admin can override per match |
| `options` | Stored on `MatchQuestion`; one answer per line in admin UI |

**Scoring:** exact string match against `correct_answer`. Options must match what players see.

**Dynamic options** (generated per match in `question_builder.default_options_for_template` or admin):

- Team names from `match.team_home` / `match.team_away`
- Player names from both squads (`Player.full_name`)
- Numeric ranges as string values (`"0"`, `"1"`, …)

---

## Tier 1 — Core set (currently seeded)

Use on every group-stage match. Total default points: **27** (before point booster).

| Code | Question text | Type | Category | Pts | Options |
|------|---------------|------|----------|-----|---------|
| `MATCH_WINNER` | Who will win the match? | choice | winner | 8 | `{home_team}` · `{away_team}` · `Draw` |
| `HOME_GOALS` | Goals scored by {home_team}? | numeric | goals | 5 | `0` · `1` · `2` · `3` · `4` · `5` |
| `AWAY_GOALS` | Goals scored by {away_team}? | numeric | goals | 5 | `0` · `1` · `2` · `3` · `4` · `5` |
| `PLAYER_OF_MATCH` | Player of the match | player_pick | player | 6 | All active players from both squads (alphabetical by team) |
| `TOTAL_YELLOW_CARDS` | Total yellow cards in the match | numeric | stats | 3 | `0` · `1` · `2` · `3` · `4` · `5` · `6` · `7` |

### Notes

- `HOME_GOALS` + `AWAY_GOALS` correct answers sync the match result (`home_score` / `away_score`).
- `MATCH_WINNER` correct answer drives winner display when scores are not set.
- Extend goal options to `0`–`10` for high-scoring fixtures if desired.
- Extend yellow cards to `0`–`10` for more granularity.

---

## Tier 2 — Recommended additions (from architecture plan)

Good for variety across matches; pick 2–4 per match so total questions stay around 6–8.

| Code | Question text | Type | Category | Pts | Options |
|------|---------------|------|----------|-----|---------|
| `FIRST_GOAL_SCORER` | Who scores the first goal? | player_pick | player | 4 | `{home_team} players` · `{away_team} players` · `No goal` · `Own goal` |
| `FIRST_GOAL_TEAM` | Which team scores first? | choice | goals | 3 | `{home_team}` · `{away_team}` · `No goal` |
| `TOTAL_GOALS` | Total goals in the match (both teams) | numeric | goals | 4 | `0` · `1` · `2` · `3` · `4` · `5` · `6` · `7` · `8` |
| `TOTAL_GOALS_1H` | Total goals in the first half | numeric | goals | 3 | `0` · `1` · `2` · `3` · `4` · `5` · `6` |
| `BOTH_TEAMS_SCORE` | Will both teams score? | choice | goals | 3 | `Yes` · `No` |
| `OVER_UNDER_2_5` | Total goals over or under 2.5? | choice | goals | 3 | `Over 2.5` · `Under 2.5` |
| `WINNING_MARGIN` | Winning margin (or draw) | choice | winner | 4 | `{home_team} by 1` · `{home_team} by 2+` · `Draw` · `{away_team} by 1` · `{away_team} by 2+` |
| `TOTAL_CORNERS` | Total corners in the match | numeric | stats | 3 | `0`–`20` (each as string) or buckets: `0-4` · `5-8` · `9-12` · `13+` |
| `TOTAL_FOULS` | Total fouls committed | numeric | stats | 2 | `0`–`30` or buckets: `0-15` · `16-22` · `23-28` · `29+` |
| `POSSESSION_HOME` | Possession band for {home_team} | choice | stats | 2 | `Under 40%` · `40-49%` · `50-59%` · `60% or more` |

### First goal scorer — option build rule

```
[all home squad players]
[all away squad players]
No goal
Own goal
```

Cap at ~30 outfield names if squads are large; prefer starters + key subs.

---

## Tier 3 — Fun / engagement questions

Lower stakes; good for knockout rounds or “wildcard” group matches.

| Code | Question text | Type | Category | Pts | Options |
|------|---------------|------|----------|-----|---------|
| `RED_CARD` | Will a player be sent off (red card)? | choice | stats | 3 | `Yes` · `No` |
| `PENALTY_AWARDED` | Will a penalty be awarded? | choice | stats | 3 | `Yes` · `No` |
| `GOAL_FIRST_15` | Goal in the first 15 minutes? | choice | random | 2 | `Yes` · `No` |
| `GOAL_LAST_15` | Goal in the last 15 minutes? | choice | random | 2 | `Yes` · `No` |
| `HIGHEST_SCORING_HALF` | Higher-scoring half | choice | goals | 2 | `1st half` · `2nd half` · `Equal` |
| `CLEAN_SHEET_HOME` | Will {home_team} keep a clean sheet? | choice | goals | 3 | `Yes` · `No` |
| `CLEAN_SHEET_AWAY` | Will {away_team} keep a clean sheet? | choice | goals | 3 | `Yes` · `No` |
| `HAT_TRICK` | Will any player score a hat-trick? | choice | player | 2 | `Yes` · `No` |
| `OWN_GOAL` | Will there be an own goal? | choice | random | 2 | `Yes` · `No` |
| `SUB_GOAL` | Will a substitute score? | choice | player | 2 | `Yes` · `No` |
| `MATCH_EXTRA_TIME` | Will the match go to extra time? | choice | random | 2 | `Yes` · `No` *(knockout only; omit in group stage)* |
| `MATCH_PENALTIES` | Will the match be decided on penalties? | choice | random | 2 | `Yes` · `No` *(knockout only)* |

---

## Tier 4 — Team-specific player questions

Requires squad data. Rotate across matches so the same question does not repeat every game.

| Code | Question text | Type | Category | Pts | Options |
|------|---------------|------|----------|-----|---------|
| `HOME_TOP_SCORER` | {home_team} player to score | player_pick | player | 4 | Active `{home_team}` squad · `None` |
| `AWAY_TOP_SCORER` | {away_team} player to score | player_pick | player | 4 | Active `{away_team}` squad · `None` |
| `ANYTIME_SCORER` | Anytime goal scorer (either team) | player_pick | player | 3 | Combined squads · `No goal` |
| `HOME_CAPTAIN_SCORES` | Will {home_team} captain score? | choice | player | 2 | `Yes` · `No` |
| `AWAY_CAPTAIN_SCORES` | Will {away_team} captain score? | choice | player | 2 | `Yes` · `No` |
| `MOST_SHOTS_TEAM` | Team with more shots on target | choice | stats | 3 | `{home_team}` · `{away_team}` · `Equal` |

---

## Suggested match packs

### Pack A — Standard (default seed)

1. `MATCH_WINNER` (8)
2. `HOME_GOALS` (5)
3. `AWAY_GOALS` (5)
4. `PLAYER_OF_MATCH` (6)
5. `TOTAL_YELLOW_CARDS` (3)

**Max points:** 27 · **Booster max:** 54

### Pack B — Result + narrative

1. `MATCH_WINNER` (8)
2. `HOME_GOALS` (5)
3. `AWAY_GOALS` (5)
4. `FIRST_GOAL_TEAM` (3)
5. `BOTH_TEAMS_SCORE` (3)
6. `PLAYER_OF_MATCH` (6)

**Max points:** 30

### Pack C — Stats heavy

1. `MATCH_WINNER` (8)
2. `TOTAL_GOALS` (4)
3. `OVER_UNDER_2_5` (3)
4. `TOTAL_YELLOW_CARDS` (3)
5. `TOTAL_CORNERS` (3)
6. `RED_CARD` (3)
7. `PENALTY_AWARDED` (3)

**Max points:** 27

### Pack D — Player focus

1. `MATCH_WINNER` (8)
2. `FIRST_GOAL_SCORER` (4)
3. `PLAYER_OF_MATCH` (6)
4. `HOME_TOP_SCORER` (4)
5. `AWAY_TOP_SCORER` (4)
6. `SUB_GOAL` (2)

**Max points:** 28

---

## Point weighting guide

| Difficulty | Pts | Examples |
|------------|-----|----------|
| Easy | 2–3 | Yes/No, over/under, card bands |
| Medium | 4–5 | Goal counts, first goal team, margin |
| Hard | 6–8 | Match winner, player of the match, first scorer |

Keep **total max per match between 24–36** so boosters feel meaningful but matches are not overwhelming.

---

## Admin scoring reference

| Code | Typical correct answer source |
|------|------------------------------|
| `MATCH_WINNER` | Derived from final score or manual |
| `HOME_GOALS` / `AWAY_GOALS` | Final score per team |
| `TOTAL_GOALS` | `home_score + away_score` as string |
| `BOTH_TEAMS_SCORE` | `Yes` if both > 0 |
| `OVER_UNDER_2_5` | `Over 2.5` if total ≥ 3 |
| `FIRST_GOAL_TEAM` | Match report / event data |
| `FIRST_GOAL_SCORER` | Player name or `No goal` / `Own goal` |
| `PLAYER_OF_MATCH` | Official FIFA award |
| `TOTAL_YELLOW_CARDS` | Count from match stats |
| `TOTAL_CORNERS` | Count from match stats |
| `RED_CARD` / `PENALTY_AWARDED` | `Yes` / `No` from events |

---

## Implementation checklist

To add a new template to the database:

1. Insert row in `question_templates` (or extend `seed_wc2026._seed_question_templates`).
2. Add option builder logic in `apps/matches/question_builder.py` → `default_options_for_template`.
3. Optionally extend `AiPredictService.heuristic_answer` for smarter AI picks.
4. Assign templates to matches via **Admin → Manage Match Questions**.

### Seed snippet (Tier 2 example)

```python
templates = [
    # (code, question_text, category, default_points, question_type)
    ('FIRST_GOAL_TEAM', 'Which team scores first?', 'goals', 3, 'choice'),
    ('BOTH_TEAMS_SCORE', 'Will both teams score?', 'goals', 3, 'choice'),
    ('TOTAL_GOALS', 'Total goals in the match (both teams)', 'goals', 4, 'numeric'),
    ('OVER_UNDER_2_5', 'Total goals over or under 2.5?', 'goals', 3, 'choice'),
    ('FIRST_GOAL_SCORER', 'Who scores the first goal?', 'player', 4, 'player_pick'),
    ('TOTAL_CORNERS', 'Total corners in the match', 'stats', 3, 'numeric'),
]
```

---

## Quick copy — options only

### Fixed lists

```
Yes / No
Over 2.5 / Under 2.5
1st half / 2nd half / Equal
No goal / Own goal
Under 40% / 40-49% / 50-59% / 60% or more
0-4 / 5-8 / 9-12 / 13+   (corners buckets)
0-15 / 16-22 / 23-28 / 29+   (fouls buckets)
```

### Per-match dynamic

```
Winner:     {Home Team} / {Away Team} / Draw
Goals:      0 / 1 / 2 / 3 / 4 / 5  (extend to 10 if needed)
Cards:      0 / 1 / 2 / 3 / 4 / 5 / 6 / 7  (extend to 10)
Players:    [Home squad] + [Away squad] + No goal + Own goal
Margin:     {Home} by 1 / {Home} by 2+ / Draw / {Away} by 1 / {Away} by 2+
```
