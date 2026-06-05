from allauth.account.adapter import DefaultAccountAdapter


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
