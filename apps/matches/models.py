from django.conf import settings
from django.db import models
from django.utils import timezone


class GameSettings(models.Model):
    point_booster_limit = models.PositiveIntegerField(default=5)
    ai_predict_hours_before = models.PositiveIntegerField(default=2)
    tournament_active = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'game settings'
        verbose_name_plural = 'game settings'

    def __str__(self):
        return 'Game Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(
            pk=1,
            defaults={'point_booster_limit': settings.DEFAULT_POINT_BOOSTER_LIMIT},
        )
        return obj


class QuestionTemplate(models.Model):
    class QuestionType(models.TextChoices):
        CHOICE = 'choice', 'Choice'
        NUMERIC = 'numeric', 'Numeric'
        PLAYER_PICK = 'player_pick', 'Player pick'

    class Category(models.TextChoices):
        WINNER = 'winner', 'Winner'
        GOALS = 'goals', 'Goals'
        PLAYER = 'player', 'Player'
        STATS = 'stats', 'Stats'
        RANDOM = 'random', 'Random'

    code = models.CharField(max_length=50, unique=True)
    question_text = models.TextField(help_text='Use {home_team} and {away_team} placeholders.')
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.CHOICE)
    default_points = models.PositiveIntegerField(default=3)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.RANDOM)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'code']

    def __str__(self):
        return self.code

    def render_text(self, match):
        return self.question_text.format(
            home_team=match.team_home.name,
            away_team=match.team_away.name,
        )


class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        LIVE = 'live', 'Live'
        FINISHED = 'finished', 'Finished'

    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE, related_name='matches')
    round = models.ForeignKey('tournaments.Round', on_delete=models.SET_NULL, null=True, blank=True)
    match_number = models.PositiveIntegerField()
    team_home = models.ForeignKey('tournaments.Team', on_delete=models.PROTECT, related_name='home_matches')
    team_away = models.ForeignKey('tournaments.Team', on_delete=models.PROTECT, related_name='away_matches')
    stadium = models.ForeignKey('tournaments.Stadium', on_delete=models.PROTECT)
    kickoff_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    won_in = models.CharField(max_length=10, default='FT')

    class Meta:
        ordering = ['kickoff_at', 'match_number']
        unique_together = [('tournament', 'match_number')]

    def __str__(self):
        return (
            f'Match {self.match_number}: {self.team_home.short_name} vs {self.team_away.short_name}'
        )

    @property
    def has_started(self):
        return timezone.now() >= self.kickoff_at

    @property
    def is_prediction_open(self):
        return not self.has_started and self.status == self.Status.SCHEDULED

    @property
    def total_question_points(self):
        return self.questions.aggregate(total=models.Sum('points'))['total'] or 0


class MatchQuestion(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='questions')
    question_template = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    question_text = models.TextField()
    options = models.JSONField(default=list, blank=True)
    points = models.PositiveIntegerField(default=3)
    correct_answer = models.CharField(max_length=255, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.match} — {self.question_text[:60]}'


class MatchPrediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_predictions')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='predictions')
    point_booster_used = models.BooleanField(default=False)
    total_points = models.IntegerField(default=0)
    is_ai_generated = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'match')]
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.display_name} — {self.match}'


class QuestionPrediction(models.Model):
    match_prediction = models.ForeignKey(
        MatchPrediction,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    match_question = models.ForeignKey(MatchQuestion, on_delete=models.CASCADE, related_name='predictions')
    user_answer = models.CharField(max_length=255)
    points_awarded = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [('match_prediction', 'match_question')]

    def __str__(self):
        return f'{self.match_prediction.user.display_name}: {self.user_answer}'
