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
│  Railway cron (every 10 min) or Celery Beat                 │
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
GOOGLE_API_KEY=              # Gemini Developer API key (env only — secret)
```

**Game Settings** (Django admin → singleton row, not env):

| Field | Default | Purpose |
|-------|---------|---------|
| `ai_predict_enabled` | True | Gemini kill switch |
| `ai_predict_model` | gemini-2.5-flash | Model name |
| `ai_predict_hours_before` | 2 | Run window before kickoff |
| `ai_predict_max_users_per_run` | 500 | Safety cap per cron run |
| `point_booster_limit` | 5 | Boosters granted to new users |

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

A match with kickoff at 20:00 gets processed between 18:00 and 20:00 (when `ai_predict_hours_before = 2`). Running every **10 minutes** (`*/10 * * * *`) picks it up soon after it enters the window. Every 15 minutes also works; hourly may delay the first run by up to an hour.

### Management command modes

**Scheduled (cron — default):** only matches whose kickoff is within the next `ai_predict_hours_before` hours.

```bash
python manage.py run_ai_predictions
```

**Manual:** next N upcoming scheduled matches, ignoring the hours-before window (testing or one-off runs).

```bash
python manage.py run_ai_predictions --upcoming-matches 2
```

Before first local run after pulling code, apply migrations:

```bash
python manage.py migrate
```

### Recommended Celery Beat schedule

```python
# config/celery.py or django-celery-beat
'schedule': crontab(minute='*/10'),
'task': 'apps.ai_predict.tasks.run_ai_predictions',
```

Useful when Celery worker is not deployed yet.

### Idempotency

| Check | Enforced by |
|-------|-------------|
| User already predicted | `MatchPrediction.objects.filter(user, match).exists()` |
| Predictions closed | `match.is_prediction_open` |
| AI disabled | `profile.ai_predict_enabled` |
| Duplicate Celery runs | DB unique constraint on (user, match) |

---

## 9. Infrastructure (production)

### Does AI Predict require Redis?

**No — not if you use the management command or Railway cron.**

| Approach | Redis required? | Celery worker? | Best for |
|----------|-----------------|----------------|----------|
| **`python manage.py run_ai_predictions`** | No | No | **Railway cron (recommended)**, local cron, manual runs |
| **Celery Beat + worker** | Yes | Yes | High volume, retries, queue monitoring |

The app ships both:

- **Primary:** `apps/ai_predict/management/commands/run_ai_predictions.py`
- **Optional:** `apps.ai_predict.tasks.run_ai_predictions` (Celery) — same service logic

### Local development

1. Add to `.env`:

```text
GOOGLE_API_KEY=your-key-from-aistudio.google.com
```

Configure limits/model/window in **Django admin → Game Settings** (defaults: enabled, `gemini-2.5-flash`, 2h window, 500 users/run).

2. Install deps: `pip install -r requirements.txt`

3. Enable AI Predict on a test user (profile or onboarding toggle).

4. Ensure a match kickoff is within the next 2 hours and has questions seeded.

5. Run scheduled mode (match kickoff must be within `ai_predict_hours_before`, default 2h):

```bash
python manage.py run_ai_predictions
```

Or manual mode (next 2 fixtures, ignores the window):

```bash
python manage.py run_ai_predictions --upcoming-matches 2
```

Without `GOOGLE_API_KEY`, the service falls back to heuristics (still creates predictions).

**Optional local cron** (every 10 minutes):

```bash
crontab -e
```

```cron
*/10 * * * * cd /path/to/PredictionGame && /path/to/PredictionGame/.venv/bin/python manage.py run_ai_predictions >> /tmp/predictiongame-ai-predict.log 2>&1
```

**Optional local Celery** (only if you want to test the task queue):

```bash
# terminal 1 — requires Redis running locally
redis-server
# terminal 2
celery -A config worker -l info
# terminal 3
celery -A config beat -l info   # or: watch -n 900 python manage.py run_ai_predictions
```

celery -A config beat -l info   # or: watch -n 600 python manage.py run_ai_predictions
```

### Railway production (recommended: separate cron service, no Redis)

Use **two services** from the same GitHub repo. Do **not** attach a cron schedule to the web service.

| Service | Start command | Cron schedule | Teardown | Public domain |
|---------|---------------|---------------|----------|---------------|
| **PredictionGame** (web) | `gunicorn config.wsgi --log-file -` | **None** | Off | Yes (`myprediction.today`) |
| **AI Predictions Cron** | `python manage.py run_ai_predictions` | **`*/10 * * * *`** (every 10 min) | **On** | No |

1. **Web service variables** (shared at project level if possible):

```text
GOOGLE_API_KEY=...
SECRET_KEY=...
DATABASE_URL=...   # from Postgres plugin
```

Tune AI Predict and point booster defaults in **Django admin → Game Settings** (`ai_predict_hours_before`, `ai_predict_enabled`, model name, max users/run).

2. **Cron service** → **Settings → Deploy**:

```bash
python manage.py run_ai_predictions
```

- **Cron Schedule:** customize to `*/10 * * * *` (every 10 minutes). Alternatives: `*/15 * * * *` or `0 * * * *` (hourly).
- **Enable Teardown:** on (container exits after the command finishes).
- **Variables:** same as web (`DATABASE_URL`, `GOOGLE_API_KEY`, etc.).

3. **Migrations:** the web service `Procfile` runs `release: python manage.py migrate` on deploy. Ensure migration `0002_gamesettings_ai_predict_fields` has been applied before the first cron run.

4. **Manual run on Railway** (inside the platform — uses internal DB):

   - **AI Predictions Cron** → **Console**:

```bash
python manage.py run_ai_predictions --upcoming-matches 2
```

   - Or CLI (service name must match Railway exactly, including spaces):

```bash
railway link
railway run --service "AI Predictions Cron" python manage.py run_ai_predictions --upcoming-matches 2
```

   `railway run` from your Mac may fail if `DATABASE_URL` uses `postgres.railway.internal`; prefer the **Console** on the cron or web service.

5. View run history on the cron service **Cron Runs** tab. No Redis or Celery worker required.

### Railway production (optional: Celery)

| Component | Purpose | Railway |
|-----------|---------|---------|
| **Upstash Redis** | Celery broker | Add Redis; set `CELERY_BROKER_URL` |
| **Worker service** | Runs tasks | `celery -A config worker -l info` |
| **Beat service** | Scheduler | `celery -A config beat -l info` |

### Procfile (optional Celery)

```text
release: python manage.py migrate
web: gunicorn config.wsgi --log-file -
worker: celery -A config worker -l info
beat: celery -A config beat -l info
```

Or use **Railway cron** instead of Beat (simpler).

### Management command reference

```bash
# Cron / scheduled window (default)
python manage.py run_ai_predictions

# Manual: next N upcoming matches
python manage.py run_ai_predictions --upcoming-matches 2
```

Prints: `Created N AI prediction(s).`

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

- Cap users per run (`GameSettings.ai_predict_max_users_per_run`)
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
- [ ] Env: `GOOGLE_API_KEY`; Game Settings in admin

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
| API cost spike | `GameSettings.ai_predict_enabled` kill switch; daily cap |
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
