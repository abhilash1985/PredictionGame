from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.forms import ProfileForm, SignupForm
from apps.accounts.models import UserProfile
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
