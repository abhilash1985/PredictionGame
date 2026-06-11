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

`GOOGLE_ADSENSE_CLIENT` alone is enough for **ads.txt** (ads do not need to be enabled yet).

---

## 4. ads.txt (required for AdSense)

AdSense checks `https://myprediction.today/ads.txt` for your publisher ID.

| AdSense status | Meaning |
|----------------|---------|
| **Not found** | No file at `/ads.txt` — fix below |
| **Authorized** | Your `pub-…` ID is in the file — good |
| **Unauthorized** | File exists but wrong/missing publisher ID |
| **Not applicable** | Rare; usually N/A for standard publishers |

This app serves `/ads.txt` dynamically when `GOOGLE_ADSENSE_CLIENT` is set on the **web** service:

```text
google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0
```

(`ca-pub-…` in env is converted to `pub-…` automatically.)

### Railway setup

1. Web service → **Variables** → set:

```text
GOOGLE_ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX
```

2. Deploy the web service (not only the cron service).

3. Verify in a browser:

```text
https://myprediction.today/ads.txt
```

4. In AdSense → **Sites** → open your site → use **Check for updates** on ads.txt (crawl can take up to 24–48 hours).

If you use **www** as well as apex, both hosts must serve the same file (redirect `www` → apex, or add both domains in Railway).

---

## 5. Django integration (implemented)

### Railway variables (web service)

Minimum for **ads.txt** + **site verification** (meta tag + script in `<head>`):

```text
DEBUG=False
GOOGLE_ADSENSE_CLIENT=ca-pub-2549684217163666
```

Optional — show footer ad units after you create an ad unit in AdSense:

```text
GOOGLE_ADSENSE_ENABLED=True
GOOGLE_ADSENSE_SLOT_FOOTER=your-ad-slot-id
```

### What the app injects in production

When `GOOGLE_ADSENSE_CLIENT` is set and `DEBUG=False`, `templates/base.html` includes:

**Meta tag (verification):**

```html
<meta name="google-adsense-account" content="ca-pub-2549684217163666">
```

**Loader script:**

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2549684217163666"
        crossorigin="anonymous"></script>
```

**ads.txt** (dynamic route `/ads.txt`):

```text
google.com, pub-2549684217163666, DIRECT, f08c47fec0942fa0
```

Footer display units render only when `GOOGLE_ADSENSE_ENABLED=True` and `GOOGLE_ADSENSE_SLOT_FOOTER` is set (`templates/partials/adsense_unit.html`).

### Suggested rollout

1. Set `GOOGLE_ADSENSE_CLIENT` on Railway → deploy.
2. Confirm `https://myprediction.today/ads.txt` and view page source for meta tag.
3. In AdSense → Sites → **Check for updates** on ads.txt.
4. After approval, create an ad unit → set `GOOGLE_ADSENSE_ENABLED=True` and slot env vars.
5. Add EU/UK **cookie consent** (Consent Mode v2) if you have European users.

---

## 6. Privacy and cookies

AdSense uses cookies for ad delivery and personalization. The [Privacy Policy](/privacy/) covers:

- Session and timezone cookies
- Google Sign-In (OAuth)
- SendGrid (transactional email)
- Gemini AI Predict (when enabled)
- **Google AdSense** (when `GOOGLE_ADSENSE_ENABLED=True`)

If you serve users in the EU/UK, add a consent banner before loading personalized ads.

---

## 7. What not to do

- Do not click your own ads or incentivize clicks
- Do not hide ads or place them over buttons
- Do not run AdSense on `localhost` for real impressions
- Do not put ads inside submit/sign-out flows (accidental clicks violate policy)

---

## 8. Revenue expectations

Earnings depend on traffic, geography, and seasonality. A niche WC 2026 prediction community may earn modest amounts unless page views are large. Sports RPM varies; scale during the tournament matters most.

---

## Related

- [README.md](../README.md) — deployment
- [AI-PREDICT.md](AI-PREDICT.md) — Gemini / cron
- Live: `/privacy/`, `/about/`, `/contact/`
