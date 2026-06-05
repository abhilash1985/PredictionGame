from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.tournaments.context_processors import get_upcoming_matches
from apps.tournaments.models import PastWorldCupWinner


def landing_view(request):
    winners = PastWorldCupWinner.objects.all()[:12]
    upcoming_matches = get_upcoming_matches(limit=10)
    return render(request, 'tournaments/landing.html', {
        'winners': winners,
        'upcoming_matches': upcoming_matches,
    })


@login_required
def dashboard_view(request):
    upcoming_matches = get_upcoming_matches(limit=20)
    winner_2022 = PastWorldCupWinner.objects.filter(year=2022).first()
    return render(request, 'tournaments/dashboard.html', {
        'upcoming_matches': upcoming_matches,
        'winner_2022': winner_2022,
    })
