# FIFA 2026 Prediction Game — Question Bank

Master question bank for group-stage matches. Source of truth: [`apps/matches/data/question_bank.yaml`](../apps/matches/data/question_bank.yaml).

---

## Match question pattern (7 per match)

Every match gets **exactly 7 questions**:

| Slot | Source | Count | Points each | Max |
|------|--------|-------|-------------|-----|
| 1–3 | **Basic** (always) | 3 | 10 / 5 / 5 | 20 |
| 4 | **Player / Scoring** (random pick) | 1 | 4 | 4 |
| 5–7 | **Stats buckets** (random, one per bucket) | 3 | 2 | 6 |

**Stats buckets** (pick 3 different buckets, one question each):

- Attacking
- Attempts
- Discipline
- Distribution
- Set plays
- Defending

**Typical max per match:** 20 + 4 + 6 = **30 points** (60 with point booster).

Selection is deterministic per match (`random.Random(match.pk)`) so re-seeding produces the same pack unless questions are cleared.

---

## Placeholders

| Placeholder | Resolves to |
|-------------|-------------|
| `{home_team}` | Home team full name |
| `{away_team}` | Away team full name |

Team options in basic/winner questions use actual team names plus `Draw` and `No Results`.

Player questions use both squads (`Player.full_name`) where applicable.

---

## Basic questions (always included)

| Code | Question | Points | Options |
|------|----------|--------|---------|
| `MATCH_WINNER` | Who will win the match? | **10** | `{home_team}`, `{away_team}`, `Draw`, `No Results` |
| `HOME_GOALS` | Goals scored by {home_team}? | **5** | `0`, `1`, `2`, `3`, `4`, `5`, `5+` |
| `AWAY_GOALS` | Goals scored by {away_team}? | **5** | `0`, `1`, `2`, `3`, `4`, `5`, `5+` |

---

## Player / Scoring (pick 1 — 4 pts each)

| Code | Question | Options |
|------|----------|---------|
| `PLAYER_OF_MATCH` | Who will be Player of the match? | Squad players (both teams) |
| `FIRST_GOAL_SCORER` | Who will score the first goal in the match? | Squad players + `No goal` |
| `FIRST_GOAL_TYPE` | First goal in the match will be? | `Penalty`, `Free Kick`, `Corner`, `Inside the Box (Open Play)`, `Outside the Box (Long Range)`, `Own Goal`, `No Goals`, `Others` |
| `FIRST_GOAL_MINUTE` | When will the first goal be scored (minute)? | `0-15`, `16-30`, `31-45`, `46-60`, `61-75`, `76-90`, `90+`, `No Goals` |
| `FIRST_GOAL_TEAM` | Which team will score first? | `{home_team}`, `{away_team}`, `Draw`, `No Results` |
| `LAST_MINUTE_GOAL` | Will there be a last-minute (after 85') goal? | `Yes`, `No`, `No Results` |
| `FIRST_ASSIST_PROVIDER` | Who will provide the first assist of the match? | Squad players + `No goal` |
| `BRACE_SCORED` | Will any player score a brace? | `Yes`, `No`, `No Results` |
| `HAT_TRICK` | Will there be a hat-trick in the match? | `Yes`, `No`, `No Results` |
| `FIRST_GOAL_POSITION` | Which position will score the first goal of the match? | `No goals`, `ST (Striker)`, `LW (Left Wing)`, `CAM (Attacking Midfielder)`, `RB (Right Back)`, `CM (Central Midfielder)`, `RW (Right Wing)`, `Others` |
| `FIRST_ASSIST_POSITION` | Which position will assist the first goal of the match? | `No goals`, `LW`, `RW`, `CM`, `LM`, `CB`, `GK`, `Others` |

---

## Attacking (2 pts each — random pool)

| Code | Question | Options |
|------|----------|---------|
| `HOME_POSSESSION` | Total possession by {home_team}? | `0-25%`, `26-35%`, `36-45%`, `46-60%`, `61-75%`, `75%+` |
| `AWAY_POSSESSION` | Total possession by {away_team}? | same bands |
| `TOTAL_GOALS` | Total goals in the match? | `0`–`5`, `5+` |
| `GOALS_INSIDE_BOX` | Total goals inside penalty area? | `0`–`5`, `5+` |
| `GOALS_OUTSIDE_BOX` | Total goals outside penalty area? | `0`–`5`, `5+` |
| `TOTAL_ASSISTS` | Total assists in the match? | `0`–`5`, `5+` |
| `GOALS_FIRST_HALF` | Total goals scored in the first half? | `0`–`5`, `5+` |
| `ASSISTS_FIRST_HALF` | Total assists in the first half? | `0`–`5`, `5+` |
| `GOALS_SECOND_HALF` | Total goals scored in the second half? | `0`–`5`, `5+` |
| `ASSISTS_SECOND_HALF` | Total assists in the second half? | `0`–`5`, `5+` |

---

## Attempts (2 pts each)

| Code | Question | Options |
|------|----------|---------|
| `TOTAL_ATTEMPTS` | Total attempts at goal? | `0-3`, `4-7`, `8-10`, `11-13`, `14-17`, `17-20`, `20+` |
| `HOME_ATTEMPTS` | Total attempts at goal by {home_team}? | `0-3`, `4-6`, `7-9`, `10-12`, `13-15`, `15+` |
| `AWAY_ATTEMPTS` | Total attempts at goal by {away_team}? | same |
| `TOTAL_ATTEMPTS_ON_TARGET` | Total attempts at goal on target? | `0-3`, `4-6`, `7-9`, `10-12`, `13-15`, `15+` |
| `HOME_ATTEMPTS_ON_TARGET` | On target by {home_team}? | `0`, `1-3`, `4-6`, `7-8`, `9-10`, `10+` |
| `AWAY_ATTEMPTS_ON_TARGET` | On target by {away_team}? | same |
| `TOTAL_ATTEMPTS_OFF_TARGET` | Total attempts at goal off target? | `0-3`, `4-6`, `7-9`, `10-12`, `13-15`, `15+` |
| `HOME_ATTEMPTS_OFF_TARGET` | Off target by {home_team}? | `0`, `1-3`, `4-6`, `7-8`, `9-10`, `10+` |
| `AWAY_ATTEMPTS_OFF_TARGET` | Off target by {away_team}? | same |

---

## Discipline (2 pts each)

| Code | Question | Options |
|------|----------|---------|
| `TOTAL_YELLOW_CARDS` | Total yellow cards in the match? | `0`–`5`, `5+` |
| `TOTAL_RED_CARDS` | Total red cards in the match? | `0`–`5`, `5+` |
| `TOTAL_CARDS` | Total cards in the match? | `0`–`5`, `5+` |
| `TOTAL_FOULS` | Total fouls against in the match? | `0-5`, `6-10`, `11-15`, `16-20`, `21-25`, `26-30`, `30+` |
| `TOTAL_OFFSIDES` | Total offsides in the match? | `0`–`5`, `5+` |
| `HOME_FOULS` | Fouls against by {home_team}? | `0-5`, `6-8`, `9-12`, `13-15`, `16-18`, `19-20`, `20+` |
| `AWAY_FOULS` | Fouls against by {away_team}? | same |

---

## Distribution (2 pts each)

| Code | Question | Options |
|------|----------|---------|
| `TOTAL_PASSES` | Total passes in the match? | `0-300`, `301-400`, `401-500`, `501-650`, `651-750`, `751-850`, `850+` |
| `HOME_PASSES` | Total passes by {home_team}? | `0-200`, `201-300`, `301-400`, `401-500`, `501-600`, `600+` |
| `AWAY_PASSES` | Total passes by {away_team}? | same |
| `TOTAL_PASSES_COMPLETED` | Total passes completed in the match? | `0-300`, `301-400`, `401-500`, `501-650`, `651-750`, `750+` |
| `HOME_PASSES_COMPLETED` | Completed by {home_team}? | `0-100`, `101-200`, `201-300`, `301-400`, `401-500`, `500+` |
| `AWAY_PASSES_COMPLETED` | Completed by {away_team}? | same |
| `TOTAL_CROSSES` | Total crosses in the match? | `0-10`, `11-20`, `21-25`, `26-30`, `31-35`, `36-40`, `40+` |
| `HOME_CROSSES` | Crosses by {home_team}? | `0-5`, `6-10`, `11-13`, `14-17`, `18-20`, `20+` |
| `AWAY_CROSSES` | Crosses by {away_team}? | same |
| `TOTAL_CROSSES_COMPLETED` | Total crosses completed? | `0`–`5`, `5+` |
| `HOME_CROSSES_COMPLETED` | Completed by {home_team}? | `0`–`4`, `4+` |
| `AWAY_CROSSES_COMPLETED` | Completed by {away_team}? | `0`–`4`, `4+` |
| `SWITCHES_OF_PLAY_COMPLETED` | Total switches of play completed? | `0-2`, `3-4`, `5-6`, `7-8`, `9-10`, `10+` |

---

## Set plays (2 pts each)

| Code | Question | Options |
|------|----------|---------|
| `TOTAL_CORNERS` | Total corners in the match? | `0-2`, `3-4`, `5-6`, `7-8`, `9-10`, `10+` |
| `HOME_CORNERS` | Corners by {home_team}? | `0`–`5`, `5+` |
| `AWAY_CORNERS` | Corners by {away_team}? | `0`–`5`, `5+` |
| `TOTAL_FREE_KICKS` | Total free kicks in the match? | `0-10`, `11-20`, `21-25`, `26-30`, `31-40`, `40+` |
| `HOME_FREE_KICKS` | Free kicks by {home_team}? | `0-5`, `6-10`, `11-13`, `14-17`, `18-20`, `20+` |
| `AWAY_FREE_KICKS` | Free kicks by {away_team}? | `0-5`, `6-10`, `11-13`, `14-17`, `18-20`, `20+` |
| `PENALTIES_SCORED` | Total penalties scored in the match? | `0`, `1`, `2`, `3`, `4`, `4+` |

---

## Defending (2 pts each)

| Code | Question | Options |
|------|----------|---------|
| `TOTAL_GOAL_PREVENTIONS` | Total goal preventions in the match? | `0-5`, `6-10`, `11-13`, `14-17`, `18-20`, `21-25`, `25+` |
| `TOTAL_OWN_GOALS` | Total own goals in the match? | `0`–`4`, `4+` |
| `TOTAL_FORCED_TURNOVERS` | Total forced turnovers in the match? | `0-30`, `31-60`, `61-75`, `76-100`, `101-120`, `121-150`, `150+` |
| `HOME_FORCED_TURNOVERS` | Forced turnovers by {home_team}? | `0-10`, `11-20`, `21-35`, `36-50`, `51-60`, `61-75`, `75+` |
| `AWAY_FORCED_TURNOVERS` | Forced turnovers by {away_team}? | same |
| `TOTAL_PRESSING_APPLIED` | Total pressing applied in the match? | `0-50`, `51-100`, `101-200`, `201-300`, `301-400`, `401-500`, `500+` |
| `HOME_PRESSING_APPLIED` | Pressing by {home_team}? | `0-50`, `51-100`, `101-150`, `151-200`, `201-250`, `251-300`, `300+` |
| `AWAY_PRESSING_APPLIED` | Pressing by {away_team}? | same |

---

## Bank summary

| Bucket | Questions in bank | Used per match |
|--------|-------------------|----------------|
| Basic | 3 | 3 (all) |
| Player / Scoring | 11 | 1 (random) |
| Attacking | 10 | 0–1 |
| Attempts | 9 | 0–1 |
| Discipline | 7 | 0–1 |
| Distribution | 13 | 0–1 |
| Set plays | 7 | 0–1 |
| Defending | 8 | 0–1 |
| **Total in bank** | **68** | **7** |

---

## Implementation

| Component | Role |
|-----------|------|
| `question_bank.yaml` | All templates, option presets, match pattern rules |
| `question_bank.py` | Load bank, resolve options, select 7-question pack, seed helpers |
| `seed_wc2026` | Syncs templates and creates 7-question packs for new matches |
| `question_builder.py` | Admin UI defaults from bank |

### Commands

```bash
pip install -r requirements.txt   # includes PyYAML
python manage.py seed_wc2026 --clear-matches   # re-seed with new question packs
```

### Scoring notes

- Answers are scored by **exact string match** against `correct_answer`.
- `HOME_GOALS` / `AWAY_GOALS` numeric sync to match score only works for plain integers (`0`–`5`); `5+` is scored but not synced to `home_score`/`away_score`.
