import logging

from django.conf import settings

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from apps.accounts.profile_service import ensure_user_profile

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name = form.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_authenticated:
            profile = ensure_user_profile(user)
            if not profile.onboarding_completed:
                return '/profile/onboarding/'
        return super().get_login_redirect_url(request)

    def should_send_confirmation_mail(self, request, email_address, signup):
        if settings.EMAIL_FAIL_SILENTLY:
            return False
        return super().should_send_confirmation_mail(request, email_address, signup)

    def send_mail(self, template_prefix, email, context):
        if settings.EMAIL_FAIL_SILENTLY:
            logger.info('Email skipped (EMAIL_FAIL_SILENTLY): %s to %s', template_prefix, email)
            return
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception:
            logger.exception('Failed to send email to %s (template=%s)', email, template_prefix)
            raise


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        ensure_user_profile(user)
        return user

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)
        if sociallogin.is_existing:
            ensure_user_profile(sociallogin.user)
