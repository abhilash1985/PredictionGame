# AI Predict — Design & Implementation Plan

**Project:** PredictionGame (`myprediction.today`)  
**Status:** Documentation (pre-implementation)  
**Last updated:** June 2026

---

## Table of contents

1. [Is this possible?](#1-is-this-possible)
2. [What already exists in the codebase](#2-what-already-exists-in-the-codebase)
3. [Requirements mapping](#3-requirements-mapping)
4. [Recommended AI approach](#4-recommended-ai-approach)
5. [Architecture](#5-architecture)
6. [Personalization strategy](#6-personalization-strategy)
7. [Prompt & data context](#7-prompt--data-context)
8. [Scheduling & idempotency](#8-scheduling--idempotency)
9. [Infrastructure (production)](#9-infrastructure-production)
10. [Cost & free-tier limits](#10-cost--free-tier-limits)
11. [Implementation phases](#11-implementation-phases)
12. [Risks & fallbacks](#12-risks--fallbacks)
13. [Alternatives considered](#13-alternatives-considered)

---

## 1. Is this possible?

**Yes.** The app already has most of the plumbing:

| Piece | Status |
|-------|--------|
| User toggle `ai_predict_enabled` | Done |
| 2-hour window before kickoff | Done (`GameSettings.ai_predict_hours_before = 2`) |
| Skip if user already predicted | Done (`MatchPrediction` unique on user+match) |
| Celery task skeleton | Done (`run_ai_predictions`) |
| Match question packs (7 questions) | Done (question bank) |
| Mark AI predictions | Done (`is_ai_generated=True`) |

What is **not** done yet:

- Intelligent answers (today: random/heuristic ranking in `AiPredictService.heuristic_answer`)
- Production Celery worker + Redis + scheduler
- LLM integration (Gemini / ADK)
- Per-user varied answers for player/stats questions
- Tests for AI predict flow

---

## 2. What already exists in the codebase

### Service (`apps/ai_predict/services.py`)

```text
run_scheduled_predictions()
  → matches with kickoff in [now, now + 2 hours]
  → users with ai_predict_enabled=True
  → predict_for_user() if no existing MatchPrediction

predict_for_user()
  → skip if prediction exists or match closed
  → create MatchPrediction(is_ai_generated=True)
  → for each MatchQuestion: heuristic_answer()  ← replace with AI
```

### Current heuristic (v0)

- **MATCH_WINNER:** lower FIFA ranking wins; else random
- **Goals / stats:** random from options
- **Player questions:** random squad player

This satisfies scheduling but **does not** meet personalization requirements.

### Celery task (`apps/ai_predict/tasks.py`)

- `run_ai_predictions` — must be triggered on a schedule (Celery Beat or Railway cron)

### Match questions (7 per match)

| Slot | Questions | Points | Personalization priority |
|------|-----------|--------|------------------------|
| 1–3 | MATCH_WINNER, HOME_GOALS, AWAY_GOALS | 10 + 5 + 5 | Shared logic OK; bias by favorite team + rankings |
| 4 | Random player bucket | 4 | **Per-user variation** |
| 5–7 | Random stats buckets (3 of 6) | 2 each | **Per-user variation** |

See [QUESTION-BANK.md](QUESTION-BANK.md) for full template list.

---

## 3. Requirements mapping

| Requirement | How we satisfy it |
|-------------|-------------------|
| Only if AI Predict enabled | `UserProfile.ai_predict_enabled` (already enforced) |
| Run **2 hours before** match | `GameSettings.ai_predict_hours_before` (default 2); Celery job scans window |
| **Do not change** existing user prediction | `predict_for_user` returns early if `MatchPrediction` exists |
| Use favorite team | Include in LLM context; optional bias on winner/goals |
| Use previous predictions | Load last N `MatchPrediction` + answers for user |
| Use match details | From DB: teams, rankings, stadium, round, group; finished scores in tournament |
| Use rankings & previous results | `Team.fifa_ranking`, group standings service, past finished matches |
| “Match details from Google” | See [§4](#4-recommended-ai-approach) — grounding has free-tier limits |
| **Not identical** for all users | Per-user prompt + seeded variation on Q4–Q7; see [§6](#6-personalization-strategy) |
| Different last 3/4 questions | LLM instructed to vary player + stats picks using user history + user id seed |

---

## 4. Recommended AI approach

### Option A — **Gemini API directly** (recommended for v1)

Use the [`google-genai`](https://pypi.org/project/google-genai/) Python SDK with **Gemini 2.0 Flash** (or `gemini-2.5-flash`):

- **Free tier:** input/output tokens free on Gemini Developer API (rate limits apply)
- **Structured JSON output:** return exactly 7 answers validated against question `options`
- **Simple Celery integration:** one HTTP call per user+match
- **No agent framework overhead** for a batch prediction job

```text
pip install google-genai
GOOGLE_API_KEY=...   # from Google AI Studio
```

### Option B — **Google ADK (Agent Development Kit)**

[ADK](https://google.github.io/adk-docs/) is useful when you need:

- Multi-step agents with tools (Google Search, Maps, custom APIs)
- Conversational sessions
- Complex orchestration

For **auto-filling 7 fixed multiple-choice answers**, ADK is **heavier than needed** for v1. Consider ADK in **v2** if you add:

- Live Google Search grounding for injuries/lineups
- Multi-tool research before each prediction

**ADK requirements:** Python 3.11+, `pip install google-adk`, same `GOOGLE_API_KEY`.

### Option C — **Other free / low-cost options**

| Provider | Pros | Cons |
|----------|------|------|
| **Gemini Flash (AI Studio)** | Free tier, good JSON, same Google ecosystem | Rate limits; Search grounding limited on free tier |
| **Ollama (local Llama)** | Free, private | Not suitable on Railway serverless; ops burden |
| **Groq free tier** | Fast inference | Another API key; less structured tooling |
| **Rule-based only** | Zero cost, deterministic | Already partially implemented; poor personalization |

**Recommendation:** **Gemini Flash via `google-genai`** for v1, keep existing heuristics as **fallback** if API fails or quota exceeded.

### “Match details from Google”

| Approach | Free? | Notes |
|----------|-------|-------|
| Gemini + **Google Search grounding** | Paid tier for most models | Best for live news; not on free tier for all models |
| **Database-only context** | Yes | Rankings, squads, standings, past results in Postgres — sufficient for v1 |
| **API-Football / football-data.org** | Free tier limited | Optional v2 enrichment |

For v1, build rich context from **your seeded WC 2026 data** plus finished match results. Add Google Search grounding in v2 when billing is enabled.

---

## 5. Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Celery Beat (every 15 min) or Railway cron                 │
│    └─ run_ai_predictions                                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  AiPredictService.run_scheduled_predictions()               │
│    • matches: kickoff ∈ [now, now + 2h], status=SCHEDULED   │
│    • profiles: ai_predict_enabled=True                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
              for each (user, match) without prediction
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  AiPredictContextBuilder.build(user, match)                 │
│    • favorite team, recent predictions, standings, H2H      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  GeminiPredictor.predict(context, questions)                │
│    • structured JSON: { question_id: answer }               │
│    • validate each answer ∈ question.options                │
└───────────────────────────┬─────────────────────────────────┘
                            │ on failure
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Fallback: heuristic_answer() + user-seeded random Q4–7    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Save MatchPrediction(is_ai_generated=True) + answers       │
└─────────────────────────────────────────────────────────────┘
```

### New modules (proposed)

```text
apps/ai_predict/
├── services.py          # orchestration (extend existing)
├── context.py           # build prompt context from ORM
├── gemini_client.py     # API wrapper + JSON schema
├── validators.py        # answer ∈ options, type checks
├── tasks.py             # (existing)
└── tests/
```

### Environment variables

```text
GOOGLE_API_KEY=              # Gemini Developer API key
AI_PREDICT_MODEL=gemini-2.0-flash
AI_PREDICT_ENABLED=True      # kill switch
AI_PREDICT_MAX_USERS_PER_RUN=500   # safety cap
```

---

## 6. Personalization strategy

Goal: **same match, different users → different answers**, especially on questions 4–7.

### Layer 1 — Shared “sensible core” (Q1–Q3)

Use the same inputs for everyone (rankings, form, home advantage) but **adjust for favorite team**:

- If user’s favorite team is playing, slightly favor them in winner/goals **when rankings are close**
- If favorite team not in match, neutral model based on FIFA ranking + recent group results

Example: Brazil (rank 3) vs Serbia (rank 30) → almost everyone gets Brazil winner; that is OK for Q1–Q3.

### Layer 2 — Per-user variation (Q4–Q7)

| Technique | Purpose |
|-----------|---------|
| Include **user id + display name** in prompt | LLM varies player/stats picks |
| Include **last 5 predictions** (answers summary) | Continuity (“user often picks high-scoring games”) |
| **Seeded shuffle** of plausible stat options | Deterministic uniqueness: `random.Random(f"{user.pk}:{match.pk}")` |
| Instruction: “Pick different player/stat answers than a generic default” | Reduces mode collapse |

### Layer 3 — Post-validation

- Reject LLM answer not in `question.options`
- If duplicate collision across many users on a rare question, re-roll with user-specific seed (stats only)

### What we will **not** do

- Point booster on AI predictions (leave `point_booster_used=False` unless product says otherwise)
- Overwrite manual predictions
- Run after kickoff

---

## 7. Prompt & data context

### Context payload (built from DB)

```json
{
  "user": {
    "display_name": "Alex",
    "favorite_team": "Argentina",
    "favorite_team_fifa_rank": 1
  },
  "match": {
    "home": "Argentina",
    "away": "France",
    "home_rank": 1,
    "away_rank": 2,
    "kickoff_utc": "2026-06-15T19:00:00Z",
    "round": "Group A",
    "stadium": "MetLife Stadium"
  },
  "standings": {
    "group_a": [{"team": "Argentina", "pts": 3, "gd": 2}, "..."]
  },
  "recent_results": {
    "home_last_3": ["W 2-0 vs X", "..."],
    "away_last_3": ["..."]
  },
  "user_recent_predictions": [
    {"match": "Brazil vs Croatia", "winner": "Brazil", "home_goals": "2", "away_goals": "1"}
  ],
  "questions": [
    {
      "id": 101,
      "code": "MATCH_WINNER",
      "text": "Who will win the match?",
      "options": ["Argentina", "France", "Draw", "No Results"],
      "personalization": "core"
    },
    {
      "id": 104,
      "code": "FIRST_GOALSCORER",
      "options": ["Lionel Messi", "..."],
      "personalization": "varied"
    }
  ]
}
```

### LLM output (strict JSON)

```json
{
  "answers": {
    "101": "Argentina",
    "102": "2",
    "103": "1",
    "104": "Lionel Messi",
    "105": "Over 4.5",
    "106": "3",
    "107": "France"
  },
  "reasoning_short": "Optional one-line summary for logs only"
}
```

Server validates every value against the question’s `options` list before save.

---

## 8. Scheduling & idempotency

### Window logic (existing)

```python
window_start = now
window_end = now + timedelta(hours=ai_predict_hours_before)  # default 2
matches = Match.filter(kickoff_at__gte=window_start, kickoff_at__lte=window_end)
```

A match with kickoff at 20:00 gets processed between 18:00 and 20:00. Running every **15 minutes** ensures it is picked up once inside the window.

### Idempotency

| Check | Enforced by |
|-------|-------------|
| User already predicted | `MatchPrediction.objects.filter(user, match).exists()` |
| Predictions closed | `match.is_prediction_open` |
| AI disabled | `profile.ai_predict_enabled` |
| Duplicate Celery runs | DB unique constraint on (user, match) |

### Recommended Celery Beat schedule

```python
# config/celery.py or django-celery-beat
'schedule': crontab(minute='*/15'),
'task': 'apps.ai_predict.tasks.run_ai_predictions',
```

### Management command (dev / Railway cron fallback)

```bash
python manage.py run_ai_predictions
```

Useful when Celery worker is not deployed yet.

---

## 9. Infrastructure (production)

AI Predict **requires a background worker**. Web-only Railway deploy is not enough.

| Component | Purpose | Railway / free options |
|-----------|---------|------------------------|
| **Redis** | Celery broker | Upstash free Redis |
| **Celery worker** | Runs `run_ai_predictions` | Railway worker service |
| **Celery Beat** or **cron** | Every 15 min | Railway cron job or Beat process |
| **GOOGLE_API_KEY** | Gemini calls | Google AI Studio |

### Procfile addition

```text
release: python manage.py migrate
web: gunicorn config.wsgi --log-file -
worker: celery -A config worker -l info
beat: celery -A config beat -l info
```

Or single Railway cron invoking `python manage.py run_ai_predictions` every 15 minutes (simpler, no Beat).

---

## 10. Cost & free-tier limits

### Gemini Developer API (free tier, 2026)

- Free input/output tokens on Flash models (subject to RPM/RPD limits)
- Content may be used to improve Google products on free tier
- **Google Search grounding:** generally **not** on free tier — plan DB context for v1
- Monitor usage in [Google AI Studio](https://aistudio.google.com/)

### Rough volume estimate

| Scale | Calls / day | Notes |
|-------|-------------|-------|
| 50 users, 3 matches/day | ~150 Gemini calls | Well within free tier |
| 500 users, 5 matches/day | ~2,500 calls | May hit rate limits; batch + cache context |

**Cost control:**

- Cap users per run (`AI_PREDICT_MAX_USERS_PER_RUN`)
- Cache match-level context (same for all users) — only user slice differs
- Fallback to heuristics on 429/5xx

---

## 11. Implementation phases

### Phase 1 — Production scheduling (no LLM)

- [ ] `run_ai_predictions` management command
- [ ] Railway cron or Celery worker + Redis
- [ ] Tests for window + skip-existing logic
- [ ] Logging / admin visibility of AI predictions

**Outcome:** Heuristic AI fills predictions 2h before kickoff in production.

### Phase 2 — Gemini integration (v1 AI)

- [ ] `google-genai` client + structured JSON
- [ ] `AiPredictContextBuilder` from ORM
- [ ] Validate answers against options
- [ ] Fallback to heuristics on error
- [ ] Env: `GOOGLE_API_KEY`, `AI_PREDICT_ENABLED`

**Outcome:** Personalized predictions with favorite team + history.

### Phase 3 — Variation & quality

- [ ] Stronger per-user variation on Q4–Q7
- [ ] Match-level context cache
- [ ] Metrics: % AI predictions, API errors, fallback rate
- [ ] Optional: email/notification “AI predicted for you”

### Phase 4 — Optional ADK / grounding (v2)

- [ ] ADK agent with Google Search tool (paid)
- [ ] Live injury/lineup enrichment
- [ ] A/B test vs Phase 2 accuracy on scored matches

---

## 12. Risks & fallbacks

| Risk | Mitigation |
|------|------------|
| Gemini API down / quota | Fallback to `heuristic_answer` + user seed |
| Invalid LLM answer | Validator rejects; retry once; then fallback |
| All users same stats answer | Per-user seed + explicit prompt for Q4–Q7 |
| Worker not running | Document Railway cron; monitor “missed predictions” |
| API cost spike | `AI_PREDICT_ENABLED` kill switch; daily cap |
| Wrong team/player in options | Always constrain to `question.options` from DB |

---

## 13. Alternatives considered

| Approach | Verdict |
|----------|---------|
| **Google ADK agent** | Good for v2 with search tools; overkill for v1 batch JSON |
| **Gemini direct API** | **Best for v1** |
| **OpenAI API** | Paid; no free tier for production volume |
| **Pure heuristics** | Already exists; insufficient personalization |
| **Train custom ML model** | Out of scope; needs historical WC data |

---

## Summary

| Question | Answer |
|----------|--------|
| Can we implement this? | **Yes** — foundation exists |
| Best free AI option? | **Gemini 2.0 Flash** via Google AI Studio (`GOOGLE_API_KEY`) |
| Use ADK now? | **Optional v2**; start with direct Gemini API |
| Same predictions for everyone? | Avoid by per-user context + varied Q4–Q7 |
| Production blocker? | **Celery worker + Redis/cron** not yet on Railway |

---

## Related docs

- [ARCHITECTURE-PLAN.md](ARCHITECTURE-PLAN.md) — §8 AI Predict Design (original v0 spec)
- [QUESTION-BANK.md](QUESTION-BANK.md) — 7 questions per match
- [README.md](../README.md) — Celery / Redis deployment notes
