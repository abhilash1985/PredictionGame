from apps.accounts.oauth import google_oauth_configured


def auth_context(request):
    return {
        'google_oauth_enabled': google_oauth_configured(),
    }
