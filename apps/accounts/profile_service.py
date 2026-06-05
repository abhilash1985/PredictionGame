from django.conf import settings
from django.db import IntegrityError, transaction

from apps.accounts.models import UserProfile
from apps.matches.models import GameSettings


def _default_booster_limit():
    try:
        return GameSettings.load().point_booster_limit
    except Exception:
        return settings.DEFAULT_POINT_BOOSTER_LIMIT


def _base_display_name(user):
    return user.email.split('@')[0]


def ensure_user_profile(user, display_name=None):
    """
    Return the user's profile, creating it if missing.

    Display name allocation retries on IntegrityError so concurrent signups
    cannot collide on the unique display_name constraint.
    """
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None

    if profile is not None:
        if display_name and profile.display_name != display_name:
            profile.display_name = display_name
            profile.save(update_fields=['display_name'])
        return profile

    base_name = _base_display_name(user)
    booster_limit = _default_booster_limit()
    preferred_name = display_name
    counter = 0

    while counter < 100:
        if preferred_name:
            candidate = preferred_name
            preferred_name = None
        elif counter == 0:
            candidate = base_name
        else:
            candidate = f'{base_name}{counter}'

        try:
            with transaction.atomic():
                return UserProfile.objects.create(
                    user=user,
                    display_name=candidate,
                    point_boosters_remaining=booster_limit,
                )
        except IntegrityError:
            try:
                existing = UserProfile.objects.get(user=user)
                if display_name and existing.display_name != display_name:
                    existing.display_name = display_name
                    existing.save(update_fields=['display_name'])
                return existing
            except UserProfile.DoesNotExist:
                counter += 1

    raise RuntimeError(f'Unable to allocate a unique display name for user {user.pk}')
