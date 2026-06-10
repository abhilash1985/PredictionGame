import logging

from django.conf import settings
from django.contrib import messages

from allauth.account.adapter import DefaultAccountAdapter

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
        if user.is_authenticated and hasattr(user, 'profile') and not user.profile.onboarding_completed:
            return '/profile/onboarding/'
        return super().get_login_redirect_url(request)

    def send_mail(self, template_prefix, email, context):
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception:
            if settings.EMAIL_FAIL_SILENTLY:
                logger.exception('Failed to send email to %s (template=%s)', email, template_prefix)
                return
            raise

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        try:
            super().send_confirmation_mail(request, emailconfirmation, signup)
        except Exception:
            if settings.EMAIL_FAIL_SILENTLY:
                logger.exception(
                    'Failed to send confirmation email to %s',
                    emailconfirmation.email_address.email,
                )
                if request is not None:
                    messages.warning(
                        request,
                        'Your account was created, but we could not send the confirmation email yet. '
                        'You can sign in if email verification is optional.',
                    )
                return
            raise
