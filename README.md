# FIFA 2026 World Cup Prediction Game

Python/Django web app for predicting FIFA World Cup 2026 match outcomes.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_wc2026 --clear-matches
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

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
