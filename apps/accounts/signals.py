from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User, UserProfile
from apps.matches.models import GameSettings


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    base_name = instance.email.split('@')[0]
    display_name = base_name
    counter = 1
    while UserProfile.objects.filter(display_name=display_name).exists():
        display_name = f'{base_name}{counter}'
        counter += 1

    from django.conf import settings as django_settings

    try:
        booster_limit = GameSettings.load().point_booster_limit
    except Exception:
        booster_limit = django_settings.DEFAULT_POINT_BOOSTER_LIMIT

    UserProfile.objects.create(
        user=instance,
        display_name=display_name,
        point_boosters_remaining=booster_limit,
    )
