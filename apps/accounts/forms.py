from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from allauth.account.forms import SignupForm

from apps.accounts.models import UserProfile
from apps.accounts.profile_service import ensure_user_profile
from apps.accounts.timezones import BROWSER_DEFAULT, is_valid_timezone, timezone_choices


class SignupForm(SignupForm):
    first_name = forms.CharField(max_length=150, label='First name', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, label='Last name', widget=forms.TextInput(attrs={'class': 'form-control'}))
    display_name = forms.CharField(max_length=50, label='Display name', widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_display_name(self):
        display_name = self.cleaned_data['display_name'].strip()
        if UserProfile.objects.filter(display_name__iexact=display_name).exists():
            raise ValidationError('This display name is already taken.')
        return display_name

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save(update_fields=['first_name', 'last_name'])

        desired_name = self.cleaned_data['display_name']
        profile = ensure_user_profile(user)
        if profile.display_name != desired_name:
            profile.display_name = desired_name
            try:
                profile.save(update_fields=['display_name'])
            except IntegrityError as exc:
                raise ValidationError({'display_name': 'This display name is already taken.'}) from exc
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
    class Meta:
        model = UserProfile
        fields = ['favorite_team', 'ai_predict_enabled']
        widgets = {
            'favorite_team': forms.Select(attrs={'class': 'form-select'}),
            'ai_predict_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.onboarding_completed = True
        if commit:
            profile.save()
        return profile
