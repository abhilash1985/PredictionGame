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

## Production deployment

This app is a standard Django project with Gunicorn, WhiteNoise (static files), and optional Celery + Redis (AI auto-predict). See also [Question Bank](docs/QUESTION-BANK.md) for seeding match questions.

### Database: will SQLite work in production?

| Environment | SQLite | PostgreSQL |
|-------------|--------|------------|
| Local dev | Yes (default) | Optional |
| Heroku, Render, Railway, Fly.io | **No** — ephemeral filesystem; data is lost on restart | **Yes — required** |
| VPS (DigitalOcean, Oracle Cloud VM) | Possible but not recommended | Recommended |

`config/settings.py` already reads `DATABASE_URL`. Set it to a Postgres connection string in production. Local SQLite data does **not** migrate automatically; use `dumpdata` / `loaddata`, or re-run seed commands on the new database.

**Safe seeding on an existing production DB:**

```bash
python manage.py migrate
python manage.py update_wc2026_squads
python manage.py seed_wc2026   # syncs question templates; keeps matches that already have questions
```

Avoid `seed_wc2026 --clear-matches` in production — it deletes all matches, predictions, and scores.

### Production checklist

```bash
# Build
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# One-time data (new database)
python manage.py update_wc2026_squads
python manage.py seed_wc2026
python manage.py createsuperuser
```

Required environment variables:

| Variable | Production example |
|----------|-------------------|
| `DEBUG` | `False` |
| `SECRET_KEY` | long random string (never commit) |
| `ALLOWED_HOSTS` | `your-app.onrender.com,yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com,https://yourdomain.com` |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` |

Optional: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `EMAIL_HOST_PASSWORD` (SendGrid), `CELERY_BROKER_URL` (Redis URL for AI predict worker).

### Hosting options (cost overview)

Heroku **no longer has a free tier** (discontinued 2022). Expect roughly **$5–10/month** minimum (web dyno + Postgres), or use external free Postgres (Neon) to save on DB cost.

| Platform | Free / low cost | Good for this app | Caveats |
|----------|-----------------|-------------------|---------|
| [Render](https://render.com) | Free web tier; DB 90-day trial | **Easiest Django deploy** | Free web sleeps after ~15 min idle; use [Neon](https://neon.tech) free Postgres long-term |
| [Railway](https://railway.app) | ~$5 credit/month | Git push deploy, Postgres addon | Credit runs out; then paid |
| [Fly.io](https://fly.io) | Small free allowance | Docker / global regions | More setup; learn `fly.toml` |
| [Heroku](https://www.heroku.com) | Paid (Eco ~$5/mo + DB) | Mature Django docs, `Procfile` included in repo | No free tier; add Heroku Postgres or Neon |
| [PythonAnywhere](https://www.pythonanywhere.com) | Beginner free tier | Pure Django | Limited traffic; no custom domain on free |
| [Koyeb](https://www.koyeb.com) | Free hobby tier | Container deploy | Smaller community |
| [Neon](https://neon.tech) | Free Postgres | Database only | Pair with Render/Railway/Heroku |
| [Upstash](https://upstash.com) | Free Redis | Celery broker only | AI predict needs a worker + Redis |
| Oracle Cloud / VPS | Always-free ARM VM | Full control | You manage OS, nginx, Postgres |

**Recommendation for a ~1-month trial with minimal spend:** Render free web service + Neon free Postgres + optional Upstash Redis if you need AI predict. Total: **$0** if traffic is low (accept cold starts).

**Recommendation for paid simplicity:** Heroku Eco dyno + Neon free Postgres (~$5/month total).

---

### Deploy on Render (recommended free start)

1. Push this branch to GitHub/GitLab.
2. [render.com](https://render.com) → **New → Web Service** → connect repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start command:** `gunicorn config.wsgi --log-file -`
   - **Instance type:** Free
4. **New → PostgreSQL** (trial) or create a database on [Neon](https://neon.tech) and copy the connection string.
5. Environment variables on the web service:

   ```text
   DEBUG=False
   SECRET_KEY=<generate-a-long-random-string>
   ALLOWED_HOSTS=your-service.onrender.com
   CSRF_TRUSTED_ORIGINS=https://your-service.onrender.com
   DATABASE_URL=<postgres-connection-string>
   ```

6. After first deploy, open the **Shell** and run:

   ```bash
   python manage.py update_wc2026_squads
   python manage.py seed_wc2026
   python manage.py createsuperuser
   ```

7. (Optional) Add a **Background Worker** for Celery + link **Upstash Redis** as `CELERY_BROKER_URL`.

---

### Deploy on Heroku

The repo includes a `Procfile` (`release` runs migrations; `web` runs Gunicorn).

1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) and log in.
2. Create app and Postgres:

   ```bash
   heroku login
   heroku create your-prediction-game
   heroku addons:create heroku-postgresql:essential-0
   ```

   Or use a free [Neon](https://neon.tech) database and set `DATABASE_URL` manually (cheaper than Heroku Postgres).

3. Set config:

   ```bash
   heroku config:set DEBUG=False
   heroku config:set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
   heroku config:set ALLOWED_HOSTS=your-prediction-game.herokuapp.com
   heroku config:set CSRF_TRUSTED_ORIGINS=https://your-prediction-game.herokuapp.com
   ```

   `DATABASE_URL` is set automatically if you use Heroku Postgres.

4. Deploy:

   ```bash
   git push heroku main
   ```

5. Seed data (one time):

   ```bash
   heroku run python manage.py update_wc2026_squads
   heroku run python manage.py seed_wc2026
   heroku run python manage.py createsuperuser
   ```

6. (Optional) AI predict — add Redis and a worker dyno:

   ```bash
   heroku addons:create heroku-redis:mini
   heroku ps:scale worker=1
   ```

   Add to `Procfile` a worker line: `worker: celery -A config worker -l info` (and a scheduler or cron for `run_ai_predictions`).

**Will your current local DB work on Heroku?** Not directly. Export/import with `dumpdata`/`loaddata`, or re-seed on Postgres. SQLite files cannot be uploaded to Heroku.

---

### Deploy on Railway

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub.
2. Add **PostgreSQL** plugin; Railway injects `DATABASE_URL`.
3. Set `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` (use the `*.up.railway.app` hostname).
4. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
5. Start: `gunicorn config.wsgi --log-file -`
6. Run seed commands via Railway shell (same as Render).

---

### Moving local data to production Postgres

```bash
# Export (local SQLite)
python manage.py dumpdata accounts tournaments matches leaderboard --indent 2 -o backup.json

# On production (after migrate)
python manage.py loaddata backup.json
```

Re-run `seed_wc2026` if you prefer a clean fixture load instead of migrating dev data.

---

## Documentation

- [Architecture Plan](docs/ARCHITECTURE-PLAN.md)
- [Question Bank](docs/QUESTION-BANK.md)

## Modules

| App | Purpose |
|-----|---------|
| `apps.accounts` | User, profile, onboarding, auth |
| `apps.tournaments` | Teams, players, stadiums, landing/dashboard |
| `apps.matches` | Matches, questions, predictions, scoring |
| `apps.leaderboard` | Rankings, team points, graphs |
| `apps.ai_predict` | AI auto-predict service (Celery) |
