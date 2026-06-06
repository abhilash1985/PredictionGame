# FIFA 2026 World Cup Prediction Game

Python/Django web app for predicting FIFA World Cup 2026 match outcomes.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py update_wc2026_squads
python manage.py seed_wc2026 --clear-matches
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Data sync

Official FIFA team names, flags, and squad lists are loaded from fifa.com and Wikipedia (FIFA-published rosters):

```bash
python manage.py update_wc2026_squads   # refresh wc2026_squads.json + FIFA team names
python manage.py seed_wc2026            # load teams, squads, and group-stage matches
python manage.py seed_wc2026 --clear-matches   # re-seed fixtures (drops existing matches)
```

Group-stage only: knockout placeholders are not seeded, and point boosters apply to group matches only.

## Documentation

- [Architecture Plan](docs/ARCHITECTURE-PLAN.md)

## Modules

| App | Purpose |
|-----|---------|
| `apps.accounts` | User, profile, onboarding, auth |
| `apps.tournaments` | Teams, players, stadiums, landing/dashboard |
| `apps.matches` | Matches, questions, predictions, scoring |
| `apps.leaderboard` | Rankings, team points, graphs |
| `apps.ai_predict` | AI auto-predict service (Celery) |
