from django.db import models


class Tournament(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Round(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='rounds')
    name = models.CharField(max_length=50)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = [('tournament', 'name')]

    def __str__(self):
        return f'{self.tournament.name} — {self.name}'


class Team(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=10)
    fifa_code = models.CharField(max_length=3, blank=True)
    group_letter = models.CharField(max_length=1, blank=True, db_index=True)
    flag_image = models.ImageField(upload_to='flags/', blank=True)
    fifa_ranking = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['group_letter', 'name']

    def __str__(self):
        return self.name


class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Goalkeeper'),
        ('CB', 'Centre Back'),
        ('LB', 'Left Back'),
        ('RB', 'Right Back'),
        ('CDM', 'Defensive Midfielder'),
        ('CM', 'Central Midfielder'),
        ('LM', 'Left Midfielder'),
        ('RM', 'Right Midfielder'),
        ('CAM', 'Attacking Midfielder'),
        ('LW', 'Left Winger'),
        ('RW', 'Right Winger'),
        ('ST', 'Striker'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    jersey_number = models.PositiveIntegerField()
    position = models.CharField(max_length=5, choices=POSITION_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['team', 'jersey_number']
        unique_together = [('team', 'jersey_number')]

    def __str__(self):
        return f'{self.first_name} {self.last_name} (#{self.jersey_number})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class Stadium(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'stadiums'

    def __str__(self):
        return f'{self.name}, {self.city}'


class PastWorldCupWinner(models.Model):
    year = models.PositiveIntegerField(unique=True)
    country = models.CharField(max_length=100)
    image = models.ImageField(upload_to='winners/', blank=True)

    class Meta:
        ordering = ['-year']

    def __str__(self):
        return f'{self.year} — {self.country}'
