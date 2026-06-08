import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.utils import timezone

DATA_DIR = Path(__file__).resolve().parent


def load_wc2026_data():
    with open(DATA_DIR / 'wc2026.json', encoding='utf-8') as handle:
        return json.load(handle)


def load_wc2026_squads():
    with open(DATA_DIR / 'wc2026_squads.json', encoding='utf-8') as handle:
        return json.load(handle)


def parse_kickoff(date_str, time_str, stadium_key=None, stadiums=None):
    """Parse kickoff from FIFA fixtures (date/time are UTC on fifa.com)."""
    kickoff = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
    return kickoff.replace(tzinfo=ZoneInfo('UTC'))
