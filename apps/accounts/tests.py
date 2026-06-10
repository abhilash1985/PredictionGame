import os
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter

from apps.accounts.adapters import AccountAdapter, SocialAccountAdapter
from apps.accounts.context_processors import auth_context
from apps.accounts.forms import ProfileForm, SignupForm
from apps.accounts.models import UserProfile
from apps.accounts.oauth import google_oauth_configured
from apps.accounts.profile_service import ensure_user_profile

User = get_user_model()


class EnsureUserProfileTests(TestCase):
    def test_creates_profile_when_missing(self):
        user = User.objects.create_user(email='new@example.com', password='testpass123')
        UserProfile.objects.filter(user=user).delete()

        profile = ensure_user_profile(user)

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.display_name, 'new')

    def test_avoids_display_name_collision(self):
        other = User.objects.create_user(email='other@example.com', password='testpass123')
        UserProfile.objects.filter(user=other).delete()
        UserProfile.objects.create(user=other, display_name='player', point_boosters_remaining=5)

        user = User.objects.create_user(email='player@example.com', password='testpass123')
        UserProfile.objects.filter(user=user).delete()

        profile = ensure_user_profile(user)

        self.assertEqual(profile.display_name, 'player1')

    def test_returns_existing_profile(self):
        user = User.objects.create_user(email='exists@example.com', password='testpass123')
        profile = ensure_user_profile(user)
        again = ensure_user_profile(user)
        self.assertEqual(profile.pk, again.pk)


class ProfileFormTests(TestCase):
    def test_requires_user_argument(self):
        user = User.objects.create_user(email='form@example.com', password='testpass123')
        profile = ensure_user_profile(user)

        with self.assertRaises(TypeError):
            ProfileForm(instance=profile)

        form = ProfileForm(instance=profile, user=user)
        self.assertEqual(form.user, user)
        self.assertIn('timezone', form.fields)

    def test_rejects_invalid_timezone(self):
        user = User.objects.create_user(email='tz@example.com', password='testpass123')
        profile = ensure_user_profile(user)
        form = ProfileForm(
            {'display_name': profile.display_name, 'timezone': 'Not/A/Zone', 'ai_predict_enabled': False},
            instance=profile,
            user=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('timezone', form.errors)


class SignupFormTests(TestCase):
    def test_save_sets_display_name_when_profile_missing(self):
        user = User.objects.create_user(email='signup@example.com', password='testpass123')
        UserProfile.objects.filter(user=user).delete()

        form = SignupForm()
        form.cleaned_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'display_name': 'TestPlayer',
        }

        with patch('allauth.account.forms.SignupForm.save', return_value=user):
            saved = form.save(request=None)

        profile = UserProfile.objects.get(user=saved)
        self.assertEqual(profile.display_name, 'TestPlayer')


class AccountAdapterEmailTests(TestCase):
    @override_settings(EMAIL_FAIL_SILENTLY=True)
    def test_should_not_send_confirmation_when_fail_silent(self):
        adapter = AccountAdapter()
        self.assertFalse(adapter.should_send_confirmation_mail(None, None, True))

    @override_settings(EMAIL_FAIL_SILENTLY=True)
    @patch.object(DefaultAccountAdapter, 'send_mail', side_effect=Exception('smtp down'))
    def test_send_mail_skips_smtp_when_fail_silent(self, mock_send):
        adapter = AccountAdapter()
        adapter.send_mail('account/email/email_confirmation', 'user@example.com', {})
        mock_send.assert_not_called()

    @override_settings(EMAIL_FAIL_SILENTLY=False)
    @patch.object(DefaultAccountAdapter, 'send_mail', side_effect=Exception('smtp down'))
    def test_send_mail_raises_when_not_fail_silent(self, mock_send):
        adapter = AccountAdapter()
        with self.assertRaises(Exception):
            adapter.send_mail('account/email/email_confirmation', 'user@example.com', {})


class GoogleOAuthTests(TestCase):
    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            'google': {'APP': {'client_id': 'id', 'secret': 'secret', 'key': ''}},
        },
    )
    def test_google_oauth_configured_when_credentials_present(self):
        self.assertTrue(google_oauth_configured())
        self.assertTrue(auth_context(None)['google_oauth_enabled'])

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            'google': {'APP': {'client_id': '', 'secret': '', 'key': ''}},
        },
    )
    def test_google_oauth_disabled_without_credentials(self):
        self.assertFalse(google_oauth_configured())
        self.assertFalse(auth_context(None)['google_oauth_enabled'])

    @patch('apps.accounts.adapters.DefaultSocialAccountAdapter.save_user')
    def test_social_save_user_ensures_profile(self, mock_super_save):
        user = User.objects.create_user(email='google@example.com', password='testpass123')
        UserProfile.objects.filter(user=user).delete()
        mock_super_save.return_value = user
        sociallogin = MagicMock()
        sociallogin.user = user

        SocialAccountAdapter().save_user(RequestFactory().get('/'), sociallogin)

        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_pre_social_login_ensures_profile_for_existing_user(self):
        user = User.objects.create_user(email='linked@example.com', password='testpass123')
        UserProfile.objects.filter(user=user).delete()
        sociallogin = MagicMock()
        sociallogin.is_existing = True
        sociallogin.user = user

        SocialAccountAdapter().pre_social_login(RequestFactory().get('/'), sociallogin)

        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    @patch.dict(os.environ, {'GOOGLE_CLIENT_ID': 'test-id', 'GOOGLE_CLIENT_SECRET': 'test-secret'})
    def test_login_page_shows_google_button(self):
        response = self.client.get(reverse('account_login'))
        self.assertContains(response, 'Continue with Google')
        self.assertContains(response, 'btn-google')
