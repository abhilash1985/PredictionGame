from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.profile_service import ensure_user_profile
from apps.matches.forms import AdminMatchPredictionForm, MatchPredictionForm, admin_match_choices, admin_user_choices
from apps.matches.models import Match, MatchQuestion, QuestionTemplate
from apps.matches.question_builder import (
    existing_question_rows,
    post_question_indices,
    question_row_from_post,
    save_match_questions,
    template_defaults_for_match,
)
from apps.matches.services.scoring import ScoringService
from apps.tournaments.models import Player


def _active_tournament_matches():
    from apps.tournaments.context_processors import get_active_tournament

    tournament = get_active_tournament()
    if not tournament:
        return Match.objects.none()
    return (
        Match.objects.filter(tournament=tournament)
        .select_related('team_home', 'team_away', 'stadium', 'round')
        .prefetch_related('questions')
        .order_by('kickoff_at', 'match_number')
    )


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
def admin_score_answers_view(request):
    matches = _active_tournament_matches()
    match_id = request.GET.get('match_id') or request.POST.get('match_id')
    match = None
    if match_id:
        match = get_object_or_404(matches, pk=match_id)

    if request.method == 'POST' and match:
        answers = {}
        for question in match.questions.all():
            answer = request.POST.get(f'answer_{question.id}', '').strip()
            if answer:
                answers[str(question.id)] = answer
        scored_count = ScoringService.set_correct_answers(match, answers)
        messages.success(
            request,
            f'Correct answers saved. Scored {scored_count} prediction(s).',
        )
        return redirect(f'{reverse("admin_score_answers")}?match_id={match.pk}')

    return render(request, 'matches/admin_score_answers.html', {
        'matches': matches,
        'match': match,
        'match_choices': admin_match_choices(matches),
        'selected_match_id': int(match_id) if match_id else '',
    })


@staff_member_required
def admin_update_prediction_view(request):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    matches = _active_tournament_matches()
    user_id = request.GET.get('user_id') or request.POST.get('user_id')
    match_id = request.GET.get('match_id') or request.POST.get('match_id')
    target_user = None
    match = None
    form = None

    if user_id:
        target_user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    if match_id:
        match = get_object_or_404(matches, pk=match_id)

    if request.method == 'POST' and target_user and match:
        form = AdminMatchPredictionForm(request.POST, match=match, user=target_user)
        if form.is_valid():
            prediction = form.save()
            if match.questions.exclude(correct_answer__isnull=True).exclude(correct_answer='').exists():
                ScoringService.score_match_prediction(prediction)
            messages.success(request, f'Prediction updated for {target_user.display_name}.')
            return redirect(
                f'{reverse("admin_update_prediction")}?user_id={target_user.pk}&match_id={match.pk}'
            )
    elif target_user and match:
        form = AdminMatchPredictionForm(match=match, user=target_user)

    question_rows = []
    if target_user and match:
        existing_answers = {}
        prediction = match.predictions.filter(user=target_user).first()
        if prediction:
            for answer in prediction.answers.select_related('match_question'):
                existing_answers[answer.match_question_id] = answer.user_answer
        for question in match.questions.all():
            selected_value = existing_answers.get(question.id, '')
            if request.method == 'POST':
                selected_value = request.POST.get(f'question_{question.id}', selected_value)
            question_rows.append({
                'question': question,
                'selected_value': selected_value,
            })

    return render(request, 'matches/admin_update_prediction.html', {
        'matches': matches,
        'match': match,
        'target_user': target_user,
        'form': form,
        'user_choices': admin_user_choices(),
        'match_choices': admin_match_choices(matches),
        'selected_user_id': int(user_id) if user_id else '',
        'selected_match_id': int(match_id) if match_id else '',
        'question_rows': question_rows,
    })


@staff_member_required
def admin_manage_match_questions_view(request):
    matches = _active_tournament_matches()
    match_id = request.GET.get('match_id') or request.POST.get('match_id')
    match = None
    question_rows = []
    question_templates = QuestionTemplate.objects.filter(is_active=True).order_by('category', 'code')
    template_defaults = {}

    if match_id:
        match = get_object_or_404(
            matches.select_related('team_home', 'team_away'),
            pk=match_id,
        )
        template_defaults = template_defaults_for_match(match)

    if request.method == 'POST' and match:
        parsed_rows = []
        for index in post_question_indices(request):
            row = question_row_from_post(request, index)
            if row:
                row['index'] = index
                parsed_rows.append(row)
        try:
            saved_count = save_match_questions(match, parsed_rows)
            messages.success(request, f'Saved {saved_count} prediction question(s) for this match.')
            return redirect(f'{reverse("admin_manage_match_questions")}?match_id={match.pk}')
        except (QuestionTemplate.DoesNotExist, MatchQuestion.DoesNotExist):
            messages.error(request, 'Could not save questions. Check your selections and try again.')
            question_rows = parsed_rows
    elif match:
        question_rows = existing_question_rows(match)
        for index, row in enumerate(question_rows):
            row['index'] = index

    if match and not question_rows:
        question_rows = [{
            'index': 0,
            'id': '',
            'template_id': '',
            'question_text': '',
            'points': '',
            'options': '',
            'delete': False,
        }]

    return render(request, 'matches/admin_manage_questions.html', {
        'matches': matches,
        'match': match,
        'match_choices': admin_match_choices(matches),
        'selected_match_id': int(match_id) if match_id else '',
        'question_templates': question_templates,
        'question_rows': question_rows,
        'template_defaults': template_defaults,
        'blank_row': {
            'index': '__INDEX__',
            'id': '',
            'template_id': '',
            'question_text': '',
            'points': '',
            'options': '',
            'delete': False,
        },
    })


@staff_member_required
def admin_predict_for_user_view(request, user_id, pk):
    return redirect(f'{reverse("admin_update_prediction")}?user_id={user_id}&match_id={pk}')


@staff_member_required
def admin_score_match_view(request, pk):
    return redirect(f'{reverse("admin_score_answers")}?match_id={pk}')
