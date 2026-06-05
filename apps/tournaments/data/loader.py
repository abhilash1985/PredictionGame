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


def parse_kickoff(date_str, time_str, stadium_key, stadiums):
    stadium = stadiums[stadium_key]
    tz_name = stadium[3]
    local_dt = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
    return local_dt.replace(tzinfo=ZoneInfo(tz_name))
