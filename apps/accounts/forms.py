from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from django.contrib.auth.forms import PasswordChangeForm

from allauth.account.forms import LoginForm, ResetPasswordForm, ResetPasswordKeyForm, SignupForm

from apps.accounts.form_helpers import configure_favorite_team_field
from apps.accounts.models import UserProfile
from apps.accounts.profile_service import ensure_user_profile
from apps.accounts.timezones import BROWSER_DEFAULT, is_valid_timezone, timezone_choices


def _apply_form_control(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            continue
        existing = field.widget.attrs.get('class', '')
        if 'form-control' not in existing and 'form-select' not in existing:
            field.widget.attrs['class'] = f'{existing} form-control'.strip()


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


class LoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)
        if 'remember' in self.fields:
            self.fields['remember'].label = 'Remember me'
            self.fields['remember'].widget.attrs.update({'class': 'form-check-input'})

    def login(self, request, redirect_url=None):
        # allauth sets the session expiry based on the "Remember me" checkbox inside
        # super().login(); re-apply a persistent expiry afterwards for users flagged
        # keep_signed_in so the admin toggle always wins.
        response = super().login(request, redirect_url)
        user = getattr(self, 'user', None)
        profile = getattr(user, 'profile', None) if user else None
        if profile and profile.keep_signed_in:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        return response


class ResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


class ResetPasswordKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


class SignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)

    def save(self, request):
        user = super().save(request)
        ensure_user_profile(user)
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    timezone = forms.ChoiceField(
        choices=[],
        required=False,
        label='Timezone',
        help_text='Leave as browser default to use your device timezone, or pick a fixed zone for match times.',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = UserProfile
        fields = ['display_name', 'favorite_team', 'timezone', 'ai_predict_enabled']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'favorite_team': forms.Select(attrs={'class': 'form-select'}),
            'ai_predict_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        if user is None:
            raise TypeError('ProfileForm requires a user keyword argument.')
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['timezone'].choices = timezone_choices()
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['ai_predict_enabled'].label = ''
        self.fields['ai_predict_enabled'].widget.attrs.update({
            'class': 'form-check-input ai-predict-switch-input',
            'role': 'switch',
        })
        configure_favorite_team_field(self.fields['favorite_team'])
        self.order_fields(['display_name', 'first_name', 'last_name', 'favorite_team', 'timezone', 'ai_predict_enabled'])

    def clean_display_name(self):
        display_name = self.cleaned_data['display_name'].strip()
        exists = UserProfile.objects.filter(display_name__iexact=display_name).exclude(pk=self.instance.pk).exists()
        if exists:
            raise ValidationError('This display name is already taken.')
        return display_name

    def clean_timezone(self):
        timezone_name = self.cleaned_data.get('timezone', BROWSER_DEFAULT)
        if timezone_name and not is_valid_timezone(timezone_name):
            raise ValidationError('Select a valid timezone.')
        return timezone_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.save(update_fields=['first_name', 'last_name'])
        if commit:
            profile.save()
        return profile


class OnboardingForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label='First name', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, label='Last name', widget=forms.TextInput(attrs={'class': 'form-control'}))
    timezone = forms.ChoiceField(
        choices=[],
        required=False,
        label='Timezone',
        help_text='Leave as browser default to use your device timezone, or pick a fixed zone for match times.',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = UserProfile
        fields = ['display_name', 'favorite_team', 'timezone', 'ai_predict_enabled']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control onboarding-display-input'}),
            'ai_predict_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input ai-predict-switch-input', 'role': 'switch'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        if user is None:
            raise TypeError('OnboardingForm requires a user keyword argument.')
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['timezone'].choices = timezone_choices()
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['display_name'].help_text = 'This is how other players see you on the leaderboard.'
        self.fields['display_name'].widget.attrs.update({
            'placeholder': 'Choose a unique display name',
            'autocomplete': 'nickname',
        })
        self.fields['ai_predict_enabled'].label = ''
        configure_favorite_team_field(self.fields['favorite_team'])
        self.order_fields(['display_name', 'first_name', 'last_name', 'ai_predict_enabled', 'favorite_team', 'timezone'])

    def clean_display_name(self):
        display_name = self.cleaned_data['display_name'].strip()
        exists = UserProfile.objects.filter(display_name__iexact=display_name).exclude(pk=self.instance.pk).exists()
        if exists:
            raise ValidationError('This display name is already taken.')
        return display_name

    def clean_timezone(self):
        timezone_name = self.cleaned_data.get('timezone', BROWSER_DEFAULT)
        if timezone_name and not is_valid_timezone(timezone_name):
            raise ValidationError('Select a valid timezone.')
        return timezone_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.onboarding_completed = True
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.save(update_fields=['first_name', 'last_name'])
        if commit:
            profile.save()
        return profile
