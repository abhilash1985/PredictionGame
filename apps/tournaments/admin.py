from django.contrib import admin

from apps.tournaments.models import PastWorldCupWinner, Player, Round, Stadium, Team, Tournament


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active']


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['name', 'tournament', 'sort_order']
    list_filter = ['tournament']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'group_letter', 'fifa_code', 'fifa_ranking']
    list_filter = ['group_letter']
    search_fields = ['name', 'short_name', 'fifa_code']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'team', 'jersey_number', 'position', 'is_active']
    list_filter = ['team', 'position', 'is_active']
    search_fields = ['first_name', 'last_name']


@admin.register(Stadium)
class StadiumAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country']
    search_fields = ['name', 'city']


@admin.register(PastWorldCupWinner)
class PastWorldCupWinnerAdmin(admin.ModelAdmin):
    list_display = ['year', 'country']
