from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.profile_service import ensure_user_profile
from apps.matches.forms import MatchPredictionForm
from apps.matches.models import Match
from apps.matches.services.scoring import ScoringService
from apps.tournaments.models import Player


@login_required
def match_list_view(request):
    from apps.tournaments.context_processors import get_active_tournament

    tournament = get_active_tournament()
    matches = Match.objects.none()
    if tournament:
        matches = (
            Match.objects.filter(tournament=tournament, round__name__startswith='Group ')
            .select_related('team_home', 'team_away', 'stadium', 'round')
            .order_by('kickoff_at')
        )
    return render(request, 'matches/list.html', {'matches': matches})


@login_required
def match_squad_view(request, pk):
    match = get_object_or_404(Match.objects.select_related('team_home', 'team_away'), pk=pk)
    home_players = Player.objects.filter(team=match.team_home, is_active=True).order_by('jersey_number')
    away_players = Player.objects.filter(team=match.team_away, is_active=True).order_by('jersey_number')
    return render(request, 'matches/squad.html', {
        'match': match,
        'home_players': home_players,
        'away_players': away_players,
    })


@login_required
def predict_view(request, pk):
    match = get_object_or_404(
        Match.objects.prefetch_related('questions').select_related('team_home', 'team_away'),
        pk=pk,
    )
    if not match.is_prediction_open:
        messages.error(request, 'Predictions are closed for this match.')
        return redirect('match_list')

    if request.method == 'POST':
        form = MatchPredictionForm(request.POST, match=match, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your prediction has been saved.')
            return redirect('match_list')
    else:
        form = MatchPredictionForm(match=match, user=request.user)

    profile = ensure_user_profile(request.user)
    return render(request, 'matches/predict.html', {
        'match': match,
        'form': form,
        'boosters_remaining': profile.point_boosters_remaining,
        'booster_allowed': match.is_group_stage,
    })


@staff_member_required
def admin_predict_for_user_view(request, user_id, pk):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    match = get_object_or_404(Match.objects.prefetch_related('questions'), pk=pk)

    if request.method == 'POST':
        form = MatchPredictionForm(request.POST, match=match, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Prediction saved for {user.display_name}.')
            return redirect('admin:matches_matchprediction_changelist')
    else:
        form = MatchPredictionForm(match=match, user=user)

    return render(request, 'matches/admin_predict.html', {
        'form': form,
        'match': match,
        'target_user': user,
    })


@staff_member_required
def admin_score_match_view(request, pk):
    match = get_object_or_404(Match.objects.prefetch_related('questions'), pk=pk)
    if request.method == 'POST':
        answers = {}
        for question in match.questions.all():
            answers[str(question.id)] = request.POST.get(f'answer_{question.id}', '')
        ScoringService.set_correct_answers(match, answers)
        messages.success(request, 'Answers saved and predictions scored.')
        return redirect('admin:matches_match_change', match.pk)

    return render(request, 'matches/admin_score.html', {'match': match})
