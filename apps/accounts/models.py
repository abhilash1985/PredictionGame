from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ['email']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email.split('@')[0]

    @property
    def display_name(self):
        if hasattr(self, 'profile') and self.profile.display_name:
            return self.profile.display_name
        return self.full_name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=50, unique=True)
    favorite_team = models.ForeignKey(
        'tournaments.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fans',
    )
    ai_predict_enabled = models.BooleanField(default=False)
    onboarding_completed = models.BooleanField(default=False)
    point_boosters_remaining = models.PositiveIntegerField(default=5)
    timezone = models.CharField(max_length=63, blank=True, default='')
    keep_signed_in = models.BooleanField(
        default=False,
        help_text='Always keep this user signed in (persistent session), regardless of the login "Remember me" checkbox.',
    )

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    @property
    def boosters_used(self):
        from apps.matches.models import MatchPrediction

        return MatchPrediction.objects.filter(user=self.user, point_booster_used=True).count()
