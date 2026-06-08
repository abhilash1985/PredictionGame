from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.tournaments.data.loader import load_wc2026_data, parse_kickoff


class ParseKickoffTest(TestCase):
    def test_opening_match_ist(self):
        data = load_wc2026_data()
        fixture = data['group_matches'][0]
        kickoff = parse_kickoff(fixture['date'], fixture['time'], fixture['stadium'], data['stadiums'])
        ist = kickoff.astimezone(ZoneInfo('Asia/Kolkata'))

        self.assertEqual(kickoff, datetime(2026, 6, 11, 19, 0, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(ist, datetime(2026, 6, 12, 0, 30, tzinfo=ZoneInfo('Asia/Kolkata')))

    def test_korea_czechia_ist(self):
        data = load_wc2026_data()
        fixture = data['group_matches'][1]
        kickoff = parse_kickoff(fixture['date'], fixture['time'], fixture['stadium'], data['stadiums'])
        ist = kickoff.astimezone(ZoneInfo('Asia/Kolkata'))

        self.assertEqual(kickoff, datetime(2026, 6, 12, 2, 0, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(ist, datetime(2026, 6, 12, 7, 30, tzinfo=ZoneInfo('Asia/Kolkata')))
