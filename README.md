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

Optional: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, SendGrid vars (see [Email with SendGrid](#email-with-sendgrid)), `CELERY_BROKER_URL` (Redis URL for AI predict worker).

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
   EMAIL_HOST_PASSWORD=<sendgrid-api-key>
   DEFAULT_FROM_EMAIL=WC 2026 Predictions <noreply@mail.yourdomain.com>
   ACCOUNT_EMAIL_VERIFICATION=mandatory
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
   heroku config:set EMAIL_HOST_PASSWORD=SG.your_sendgrid_api_key
   heroku config:set DEFAULT_FROM_EMAIL="WC 2026 Predictions <noreply@mail.yourdomain.com>"
   heroku config:set ACCOUNT_EMAIL_VERIFICATION=mandatory
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
5. Start: `gunicorn config.wsgi --log-file -` (or rely on the repo `Procfile`)
6. Run seed commands via Railway shell (same as Render).

**Build error: `No GitHub artifact attestations found for python@3.12.8`**

Railway's builder uses `mise` to install Python from `runtime.txt`. This repo includes `mise.toml` to disable attestation checks. If the error persists, add a Railway **build** variable:

```text
MISE_PYTHON_GITHUB_ATTESTATIONS=false
```

Then redeploy.

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

## Email with SendGrid

Signup confirmation, password reset, and other transactional mail are handled by **django-allauth** over Django's email backend. Production uses **SendGrid SMTP** when `DEBUG=False`.

### What sends email automatically

| Flow | URL / trigger | Email sent? |
|------|---------------|-------------|
| Signup confirmation | User registers at `/accounts/signup/` | Yes — link to verify address |
| Password reset (forgot) | `/accounts/password/reset/` | Yes — reset link |
| Password change (logged in) | `/accounts/password/` | No — user is already authenticated |

With `DEBUG=False`, `ACCOUNT_EMAIL_VERIFICATION` defaults to **`mandatory`** only when SendGrid is configured. If no API key is set, or `EMAIL_FAIL_SILENTLY=True`, verification stays **`optional`** so signup does not return 500 when mail fails.

### Disable email / avoid signup 500 errors (temporary)

If SendGrid is not working yet, set on Railway and **deploy the latest code**:

```text
EMAIL_FAIL_SILENTLY=True
```

You do not need `ACCOUNT_EMAIL_VERIFICATION=optional` — when `EMAIL_FAIL_SILENTLY=True`, verification is forced to **`none`** (no confirmation emails, signup completes and logs in).

Signup and password reset will succeed; emails are skipped and logged instead of crashing the request. Re-enable mail after SendGrid is working.

### View logs on Railway

1. **Dashboard:** Project → **web service** → **Deployments** → latest deploy → **View logs** (HTTP requests and Python tracebacks).
2. **CLI:** `railway logs` (from linked project directory).
3. Search logs for `Failed to send email` or `SMTPAuthenticationError` after deploying with `EMAIL_FAIL_SILENTLY=True`.

Set `DEBUG=False` in production so stack traces are not shown to users (logs still appear in Railway).

### 1. Create a SendGrid account

1. Sign up at [sendgrid.com](https://sendgrid.com) (free tier: ~100 emails/day).
2. **Settings → API Keys → Create API Key** with **Mail Send** permission.
3. Copy the key (`SG....`) — shown once.

### 2. Verify a sender

**Quick test (no custom domain):**

- **Settings → Sender Authentication → Single Sender Verification**
- Verify one address; `DEFAULT_FROM_EMAIL` must match it exactly.

**Production (recommended):**

- **Settings → Sender Authentication → Authenticate Your Domain**
- Add SendGrid DNS records (SPF, DKIM) at your registrar or Cloudflare.
- Use a subdomain sender, e.g. `WC 2026 Predictions <noreply@mail.yourdomain.com>`.

### 3. Environment variables

Production (add to Render, Heroku, Railway, etc.):

```bash
DEBUG=False
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your_sendgrid_api_key
# or use SENDGRID_API_KEY instead of EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL=WC 2026 Predictions <noreply@mail.yourdomain.com>
ACCOUNT_EMAIL_VERIFICATION=mandatory
ACCOUNT_EMAIL_SUBJECT_PREFIX=[WC 2026]
```

`EMAIL_HOST_USER` must be the literal string `apikey` (SendGrid convention).

Include SendGrid vars in deploy examples:

```text
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
DEFAULT_FROM_EMAIL=WC 2026 Predictions <noreply@mail.yourdomain.com>
ACCOUNT_EMAIL_VERIFICATION=mandatory
EMAIL_FAIL_SILENTLY=False
```

### 4. Test email delivery

**Production shell:**

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail
send_mail('SendGrid test', 'SMTP works.', None, ['you@example.com'], fail_silently=False)
```

**Local SendGrid test** (override console backend):

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
SENDGRID_API_KEY=SG.your_key \
DEFAULT_FROM_EMAIL="WC 2026 Predictions <your-verified-sender@example.com>" \
python manage.py shell
```

With `DEBUG=True`, mail prints to the terminal by default — no SendGrid call.

### 5. Troubleshooting

| Problem | Fix |
|---------|-----|
| Mail only in terminal locally | Expected with `DEBUG=True` and console backend |
| `535 Authentication failed` | Wrong API key, or `EMAIL_HOST_USER` not `apikey` |
| SendGrid 403 / sender rejected | Complete Single Sender or domain authentication |
| Emails in spam | Add SPF, DKIM, and DMARC for your domain |
| Reset link wrong host | Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to your live URL |

### 6. Resend confirmation (admin)

In Django admin, open the user's email address record (django-allauth) and use **Send confirmation** if a user did not receive the signup email.

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
