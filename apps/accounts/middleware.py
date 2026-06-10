from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.profile_service import ensure_user_profile


class OnboardingRequiredMiddleware:
    """Redirect authenticated users to onboarding until completed."""

    EXEMPT_PREFIXES = (
        '/accounts/',
        '/admin/',
        '/static/',
        '/media/',
        '/profile/onboarding/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            path = request.path
            if not path.startswith(self.EXEMPT_PREFIXES):
                profile = ensure_user_profile(request.user)
                if not profile.onboarding_completed:
                    return redirect(reverse('onboarding'))

        return self.get_response(request)
