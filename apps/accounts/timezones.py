import zoneinfo

BROWSER_DEFAULT = ''

TIMEZONE_FRIENDLY_LABELS = {
    'UTC': 'UTC',
    'America/New_York': 'US Eastern (ET)',
    'America/Chicago': 'US Central (CT)',
    'America/Denver': 'US Mountain (MT)',
    'America/Los_Angeles': 'US Pacific (PT)',
    'Europe/London': 'UK (GMT/BST)',
    'Europe/Paris': 'Central Europe (CET)',
    'Europe/Berlin': 'Central Europe (CET)',
    'Asia/Dubai': 'Gulf (GST)',
    'Asia/Kolkata': 'India (IST)',
    'Asia/Singapore': 'Singapore (SGT)',
    'Asia/Tokyo': 'Japan (JST)',
    'Asia/Seoul': 'Korea (KST)',
    'Australia/Sydney': 'Australia Eastern (AEST)',
}

COMMON_TIMEZONES = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Mexico_City',
    'America/Toronto',
    'America/Vancouver',
    'America/Sao_Paulo',
    'America/Buenos_Aires',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Europe/Madrid',
    'Europe/Rome',
    'Europe/Amsterdam',
    'Europe/Istanbul',
    'Africa/Cairo',
    'Africa/Johannesburg',
    'Asia/Dubai',
    'Asia/Kolkata',
    'Asia/Bangkok',
    'Asia/Singapore',
    'Asia/Tokyo',
    'Asia/Seoul',
    'Australia/Sydney',
    'Pacific/Auckland',
]


def is_valid_timezone(name):
    if not name:
        return True
    try:
        zoneinfo.ZoneInfo(name)
        return True
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return False


def timezone_label(name):
    if name in TIMEZONE_FRIENDLY_LABELS:
        return TIMEZONE_FRIENDLY_LABELS[name]
    return name.replace('_', ' ')


def timezone_choices():
    choices = [(BROWSER_DEFAULT, 'Browser default (auto-detect)')]
    seen = set()

    for name in COMMON_TIMEZONES:
        if name not in seen and is_valid_timezone(name):
            choices.append((name, timezone_label(name)))
            seen.add(name)

    for name in sorted(zoneinfo.available_timezones()):
        if name in seen or '/' not in name:
            continue
        choices.append((name, timezone_label(name)))
        seen.add(name)

    return choices
