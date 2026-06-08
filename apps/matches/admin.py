from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.matches.models import (
    GameSettings,
    Match,
    MatchPrediction,
    MatchQuestion,
    QuestionPrediction,
    QuestionTemplate,
)


class MatchQuestionInline(admin.TabularInline):
    model = MatchQuestion
    extra = 0
    fields = ['question_text', 'options', 'points', 'correct_answer', 'sort_order']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['match_number', 'team_home', 'team_away', 'kickoff_at', 'status', 'stadium']
    list_filter = ['tournament', 'status', 'round']
    search_fields = ['team_home__name', 'team_away__name']
    inlines = [MatchQuestionInline]
    readonly_fields = ['score_link']

    def score_link(self, obj):
        if not obj.pk:
            return '-'
        url = reverse('admin_score_answers') + f'?match_id={obj.pk}'
        return format_html('<a class="button" href="{}">Enter answers & score</a>', url)

    score_link.short_description = 'Scoring'


@admin.register(QuestionTemplate)
class QuestionTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'category', 'default_points', 'question_type', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'question_text']


@admin.register(MatchQuestion)
class MatchQuestionAdmin(admin.ModelAdmin):
    list_display = ['match', 'question_text', 'points', 'correct_answer']
    list_filter = ['match__tournament']
    search_fields = ['question_text']


class QuestionPredictionInline(admin.TabularInline):
    model = QuestionPrediction
    extra = 0


@admin.register(MatchPrediction)
class MatchPredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'match', 'total_points', 'point_booster_used', 'is_ai_generated', 'submitted_at']
    list_filter = ['point_booster_used', 'is_ai_generated', 'match__tournament']
    search_fields = ['user__email', 'user__profile__display_name']
    inlines = [QuestionPredictionInline]


@admin.register(QuestionPrediction)
class QuestionPredictionAdmin(admin.ModelAdmin):
    list_display = ['match_prediction', 'match_question', 'user_answer', 'points_awarded']
    search_fields = ['user_answer']


@admin.register(GameSettings)
class GameSettingsAdmin(admin.ModelAdmin):
    list_display = ['point_booster_limit', 'ai_predict_hours_before', 'tournament_active']

    def has_add_permission(self, request):
        return not GameSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
