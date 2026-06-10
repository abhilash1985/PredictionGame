import os

from django.conf import settings


def google_oauth_configured():
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
    if client_id and secret:
        return True

    app = settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APP', {})
    return bool(app.get('client_id') and app.get('secret'))
