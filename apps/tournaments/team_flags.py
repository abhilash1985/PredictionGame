"""Team flag URLs for UI badges."""

FIFA_FLAG_URL = 'https://api.fifa.com/api/v3/picture/flags-sq-1/{code}'

WINNER_COUNTRY_TO_CODE = {
    'Argentina': 'ARG',
    'Brazil': 'BRA',
    'England': 'ENG',
    'France': 'FRA',
    'Germany': 'GER',
    'Italy': 'ITA',
    'Spain': 'ESP',
    'Uruguay': 'URU',
}

FIFA_CODE_TO_ISO2 = {
    'ALG': 'dz',
    'ARG': 'ar',
    'AUS': 'au',
    'AUT': 'at',
    'BEL': 'be',
    'BIH': 'ba',
    'BRA': 'br',
    'CAN': 'ca',
    'CIV': 'ci',
    'COL': 'co',
    'CPV': 'cv',
    'CRO': 'hr',
    'CZE': 'cz',
    'CUW': 'cw',
    'ECU': 'ec',
    'EGY': 'eg',
    'ENG': 'gb-eng',
    'ESP': 'es',
    'FRA': 'fr',
    'GER': 'de',
    'GHA': 'gh',
    'HAI': 'ht',
    'IRN': 'ir',
    'IRQ': 'iq',
    'ITA': 'it',
    'JOR': 'jo',
    'JPN': 'jp',
    'KOR': 'kr',
    'KSA': 'sa',
    'MAR': 'ma',
    'MEX': 'mx',
    'NED': 'nl',
    'NOR': 'no',
    'NZL': 'nz',
    'PAN': 'pa',
    'PAR': 'py',
    'POR': 'pt',
    'QAT': 'qa',
    'RSA': 'za',
    'SCO': 'gb-sct',
    'SEN': 'sn',
    'SUI': 'ch',
    'SWE': 'se',
    'TUN': 'tn',
    'TUR': 'tr',
    'URU': 'uy',
    'USA': 'us',
    'UZB': 'uz',
    'COD': 'cd',
}


def flag_url_for_code(fifa_code, size='w40'):
    code = (fifa_code or '').upper()
    if not code:
        return ''
    return FIFA_FLAG_URL.format(code=code)


def flag_url_for_team(team, size='w40'):
    code = team.fifa_code or team.short_name
    return flag_url_for_code(code, size=size)


def flag_url_for_country(country_name):
    code = WINNER_COUNTRY_TO_CODE.get(country_name or '')
    return flag_url_for_code(code)
