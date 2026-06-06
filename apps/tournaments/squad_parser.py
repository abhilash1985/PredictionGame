"""Fetch and parse FIFA World Cup 2026 squad lists."""

import json
import re
import urllib.request
from pathlib import Path

FIFA_CXM_API = 'https://cxm-api.fifa.com/fifaplusweb/api'
FIFA_TOURNAMENT_PATH = '/en/tournaments/mens/worldcup/canadamexicousa2026'
FIFA_TEAMS_MODULE = (
    f'{FIFA_CXM_API}/sections/teamsModule/4v5Yng3VdGD9c1cpnOIff1'
    '?locale=en&skip=0&limit=48'
)

WIKI_PAGE = '2026_FIFA_World_Cup_squads'
WIKI_API = 'https://en.wikipedia.org/w/api.php'

# Wikipedia section titles (not FIFA display names) mapped to FIFA 3-letter codes.
WIKI_SECTION_TO_CODE = {
    'Algeria': 'ALG',
    'Argentina': 'ARG',
    'Australia': 'AUS',
    'Austria': 'AUT',
    'Belgium': 'BEL',
    'Bosnia and Herzegovina': 'BIH',
    'Brazil': 'BRA',
    'Cabo Verde': 'CPV',
    'Cape Verde': 'CPV',
    'Canada': 'CAN',
    'Colombia': 'COL',
    'Congo DR': 'COD',
    'Croatia': 'CRO',
    'Curaçao': 'CUW',
    'Czech Republic': 'CZE',
    'DR Congo': 'COD',
    'Ecuador': 'ECU',
    'Egypt': 'EGY',
    'England': 'ENG',
    'France': 'FRA',
    'Germany': 'GER',
    'Ghana': 'GHA',
    'Haiti': 'HAI',
    'IR Iran': 'IRN',
    'Iran': 'IRN',
    'Iraq': 'IRQ',
    'Japan': 'JPN',
    'Jordan': 'JOR',
    'Korea Republic': 'KOR',
    'Mexico': 'MEX',
    'Morocco': 'MAR',
    'Netherlands': 'NED',
    'New Zealand': 'NZL',
    'Norway': 'NOR',
    'Panama': 'PAN',
    'Paraguay': 'PAR',
    'Portugal': 'POR',
    'Qatar': 'QAT',
    'Saudi Arabia': 'KSA',
    'Scotland': 'SCO',
    'Senegal': 'SEN',
    'South Africa': 'RSA',
    'South Korea': 'KOR',
    'Spain': 'ESP',
    'Switzerland': 'SUI',
    'Sweden': 'SWE',
    'Tunisia': 'TUN',
    'Türkiye': 'TUR',
    'Turkey': 'TUR',
    'United States': 'USA',
    'Uruguay': 'URU',
    'Uzbekistan': 'UZB',
    "Côte d'Ivoire": 'CIV',
    'Ivory Coast': 'CIV',
}

POSITION_MAP = {
    'GK': 'GK',
    'DF': 'CB',
    'MF': 'CM',
    'FW': 'ST',
}

TEAM_HEADER = re.compile(r'^===\s*(.+?)\s*===')
PLAYER_RE = re.compile(
    r'\{\{nat fs g player\|no=(\d+)\|pos=(GK|DF|MF|FW)\|'
    r'name=\[\[(?:[^\]|]+\|)?([^\]]+)\]\](?:\|sortname=([^|{}]+))?'
)

REQUEST_HEADERS = {
    'User-Agent': 'PredictionGame/1.0 (local dev; squad sync)',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.fifa.com',
    'Referer': 'https://www.fifa.com/',
}


def _request_json(url, timeout=120):
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def fetch_fifa_teams():
    """Return FIFA teams keyed by 3-letter code with official display name and slug."""
    payload = _request_json(FIFA_TEAMS_MODULE)
    teams = {}
    for team in payload.get('teams', []):
        flag_url = team.get('teamFlag', '')
        code_match = re.search(r'/([A-Z]{3})$', flag_url)
        if not code_match:
            continue
        code = code_match.group(1)
        if code in teams:
            continue
        slug = team.get('teamPageUrl', '').rstrip('/').split('/')[-1]
        teams[code] = {
            'code': code,
            'name': team.get('teamName'),
            'slug': slug,
            'team_id': team.get('teamId'),
            'flag_url': flag_url.replace('{format}-{size}', 'sq-1'),
            'squad_url': (
                f'https://www.fifa.com{FIFA_TOURNAMENT_PATH}/teams/{slug}/squad'
            ),
        }
    return teams


def fetch_wikipedia_text():
    params = (
        f'{WIKI_API}?action=parse&page={WIKI_PAGE.replace(" ", "%20")}'
        '&prop=wikitext&format=json'
    )
    payload = _request_json(params)
    return payload['parse']['wikitext']['*']


def split_display_name(full_name):
    full_name = re.sub(r'\(captain\)', '', full_name, flags=re.I).strip()
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], ''
    return ' '.join(parts[:-1]), parts[-1]


def parse_player_match(match):
    number = int(match.group(1))
    position = POSITION_MAP[match.group(2)]
    sort_name = (match.group(4) or '').strip()
    if sort_name and ',' in sort_name:
        last_name, first_name = [part.strip() for part in sort_name.split(',', 1)]
    else:
        first_name, last_name = split_display_name(match.group(3).strip())
    return first_name, last_name, number, position


def parse_squads_from_wikipedia(text):
    squads = {}
    current_team = None

    for line in text.splitlines():
        header = TEAM_HEADER.match(line.strip())
        if header:
            team_name = header.group(1).strip()
            current_team = WIKI_SECTION_TO_CODE.get(team_name)
            if current_team and current_team not in squads:
                squads[current_team] = []
            continue

        if not current_team:
            continue

        match = PLAYER_RE.search(line)
        if not match:
            continue

        squads[current_team].append(list(parse_player_match(match)))

    return squads


def sync_wc2026_team_names(fifa_teams=None, data_path=None):
    """Update wc2026.json team display names from FIFA."""
    data_path = data_path or Path(__file__).resolve().parent / 'data' / 'wc2026.json'
    fifa_teams = fifa_teams or fetch_fifa_teams()
    data = json.loads(data_path.read_text(encoding='utf-8'))
    for team in data['teams']:
        fifa_team = fifa_teams.get(team['code'])
        if fifa_team:
            team['name'] = fifa_team['name']
    data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return data


def write_squads_json(output_path=None):
    output_path = output_path or Path(__file__).resolve().parent / 'data' / 'wc2026_squads.json'
    fifa_teams = fetch_fifa_teams()
    sync_wc2026_team_names(fifa_teams=fifa_teams)
    text = fetch_wikipedia_text()
    squads = parse_squads_from_wikipedia(text)
    output_path.write_text(json.dumps(squads, indent=2, ensure_ascii=False) + '\n')
    return squads
