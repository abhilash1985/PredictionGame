from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from apps.accounts.forms import OnboardingForm, ProfileForm
from apps.accounts.profile_service import ensure_user_profile


@login_required
def onboarding_view(request):
    profile = ensure_user_profile(request.user)
    if profile.onboarding_completed:
        return redirect('dashboard')

    if request.method == 'POST':
        form = OnboardingForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Welcome! Your preferences have been saved.')
            return redirect('dashboard')
    else:
        form = OnboardingForm(instance=profile)

    return render(request, 'accounts/onboarding.html', {'form': form})


@login_required
def profile_view(request):
    profile = ensure_user_profile(request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('profile')
