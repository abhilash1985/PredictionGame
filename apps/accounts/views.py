from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from apps.accounts.forms import OnboardingForm, ProfileForm
from apps.accounts.profile_service import ensure_user_profile
from apps.leaderboard.services import LeaderboardService
from apps.tournaments.context_processors import get_active_tournament


def _sync_timezone_cookie(response, profile):
    if profile.timezone:
        response.set_cookie(
            'django_timezone',
            profile.timezone,
            max_age=31536000,
            path='/',
            samesite='Lax',
        )
    else:
        response.delete_cookie('django_timezone', path='/')
    return response


@login_required
def onboarding_view(request):
    profile = ensure_user_profile(request.user)
    if profile.onboarding_completed:
        return redirect('dashboard')

    if request.method == 'POST':
        form = OnboardingForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            profile = form.save()
            messages.success(request, 'Welcome! Your preferences have been saved.')
            response = redirect('dashboard')
            return _sync_timezone_cookie(response, profile)
    else:
        form = OnboardingForm(instance=profile, user=request.user)

    return render(request, 'accounts/onboarding.html', {'form': form})


@login_required
def profile_view(request):
    profile = ensure_user_profile(request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            profile = form.save()
            messages.success(request, 'Profile updated.')
            response = redirect('profile')
            return _sync_timezone_cookie(response, profile)
    else:
        form = ProfileForm(instance=profile, user=request.user)

    tournament = get_active_tournament()
    leaderboard_rows = LeaderboardService.user_stats(tournament)
    user_leaderboard = next(
        (row for row in leaderboard_rows if row['user_id'] == request.user.id),
        None,
    )
    return render(request, 'accounts/profile.html', {
        'form': form,
        'user_leaderboard': user_leaderboard,
        'leaderboard_total': len(leaderboard_rows),
        'tournament': tournament,
    })


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('profile')
