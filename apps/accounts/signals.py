from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.accounts.profile_service import ensure_user_profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    ensure_user_profile(instance)
