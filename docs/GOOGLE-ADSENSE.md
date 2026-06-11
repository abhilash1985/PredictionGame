# Google AdSense integration

How to monetize **myprediction.today** with **Google AdSense** (display ads; revenue from clicks and impressions). This is **not** Google Ads (the advertiser product).

**Live pages required for approval:**

- [Privacy Policy](/privacy/) — `/privacy/`
- [About](/about/) — `/about/`
- [Contact](/contact/) — `/contact/`

---

## 1. Get approved

1. Sign up at [Google AdSense](https://www.google.com/adsense).
2. Add site: `https://myprediction.today` (and `www` if used).
3. Wait for review (days to weeks).

Google typically expects:

- Original content (landing, matches, leaderboard)
- Privacy Policy mentioning cookies and advertising
- About and contact information
- Custom domain, site live in production
- Compliance with [AdSense program policies](https://support.google.com/adsense/answer/48182)

### Policy notes for this app

| Topic | Guidance |
|-------|----------|
| Prediction / fantasy | OK if **no real-money betting** |
| FIFA branding | Trademark is separate from AdSense; use official assets carefully |
| Thin pages | Minimize or skip ads on login, signup, onboarding |
| Invalid clicks | Never ask users to click ads or click your own ads |

---

## 2. After approval — ad units

AdSense → **Ads** → **By ad unit** → create responsive **Display** units.

You receive:

- **Publisher client ID:** `ca-pub-XXXXXXXXXXXXXXXX`
- **Ad slot IDs** per unit (footer, sidebar, in-content, etc.)

---

## 3. Environment variables

Add to Railway web service and `.env` (production only):

```text
GOOGLE_ADSENSE_ENABLED=True
GOOGLE_ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX
GOOGLE_ADSENSE_SLOT_FOOTER=1234567890
GOOGLE_ADSENSE_SLOT_SIDEBAR=0987654321
SITE_CONTACT_EMAIL=contact@myprediction.today
```

Keep `GOOGLE_ADSENSE_ENABLED=False` locally (`DEBUG=True`).

---

## 4. Django integration (when ready to enable ads)

### Settings (`config/settings.py`)

```python
GOOGLE_ADSENSE_CLIENT = os.environ.get('GOOGLE_ADSENSE_CLIENT', '')
GOOGLE_ADSENSE_ENABLED = os.environ.get('GOOGLE_ADSENSE_ENABLED', 'False').lower() in ('true', '1', 'yes')
GOOGLE_ADSENSE_SLOT_FOOTER = os.environ.get('GOOGLE_ADSENSE_SLOT_FOOTER', '')
GOOGLE_ADSENSE_SLOT_SIDEBAR = os.environ.get('GOOGLE_ADSENSE_SLOT_SIDEBAR', '')
SITE_CONTACT_EMAIL = os.environ.get('SITE_CONTACT_EMAIL', 'contact@myprediction.today')
SITE_NAME = os.environ.get('SITE_NAME', 'FIFA WC 2026 Prediction Game')
```

Enable ads only when `GOOGLE_ADSENSE_ENABLED`, client ID is set, and `DEBUG=False`.

### Context processor

Expose `adsense_enabled`, `adsense_client`, and slot IDs to templates.

### Templates

| Placement | Suggested pages | Avoid |
|-----------|-----------------|-------|
| Footer banner | Landing, leaderboard, match list | Predict form, modals |
| In-content | Dashboard, leaderboard | Login, signup, onboarding |

**`templates/base.html` `<head>`** (once, when enabled):

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={{ adsense_client }}"
     crossorigin="anonymous"></script>
```

**`templates/partials/adsense_unit.html`:**

```html
{% if adsense_enabled and adsense_client and slot %}
<div class="adsense-unit my-3 text-center" aria-label="Advertisement">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="{{ adsense_client }}"
       data-ad-slot="{{ slot }}"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
{% endif %}
```

### Suggested rollout

1. Privacy, About, Contact pages live (done in repo).
2. Apply for AdSense on production domain.
3. After approval, set env vars on Railway.
4. Add partial + context processor + footer unit.
5. Enable on public pages first; skip predict/login flows.
6. Add EU/UK **cookie consent** (Consent Mode v2) if you have European users.

---

## 5. Privacy and cookies

AdSense uses cookies for ad delivery and personalization. The [Privacy Policy](/privacy/) covers:

- Session and timezone cookies
- Google Sign-In (OAuth)
- SendGrid (transactional email)
- Gemini AI Predict (when enabled)
- **Google AdSense** (when `GOOGLE_ADSENSE_ENABLED=True`)

If you serve users in the EU/UK, add a consent banner before loading personalized ads.

---

## 6. What not to do

- Do not click your own ads or incentivize clicks
- Do not hide ads or place them over buttons
- Do not run AdSense on `localhost` for real impressions
- Do not put ads inside submit/sign-out flows (accidental clicks violate policy)

---

## 7. Revenue expectations

Earnings depend on traffic, geography, and seasonality. A niche WC 2026 prediction community may earn modest amounts unless page views are large. Sports RPM varies; scale during the tournament matters most.

---

## Related

- [README.md](../README.md) — deployment
- [AI-PREDICT.md](AI-PREDICT.md) — Gemini / cron
- Live: `/privacy/`, `/about/`, `/contact/`
