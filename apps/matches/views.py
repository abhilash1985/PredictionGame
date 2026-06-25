from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count
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
from apps.matches.prediction_lookup import predicted_match_ids
from apps.matches.scorecard_service import MatchScorecardService
from apps.matches.services.scoring import ScoringService
from apps.tournaments.models import Player

VALID_PREDICT_RETURN_SOURCES = frozenset({'dashboard', 'matches'})
VALID_SCORECARD_RETURN_SOURCES = frozenset({'dashboard_stats', 'dashboard', 'matches'})


def _predict_return_source(request):
    raw = request.POST.get('from') if request.method == 'POST' else request.GET.get('from')
    if raw in VALID_PREDICT_RETURN_SOURCES:
        return raw
    return 'matches'


def _predict_redirect_after_save(from_source):
    if from_source == 'dashboard':
        return f"{reverse('dashboard')}?tab=matches"
    return reverse('match_list')


def _scorecard_return_source(request):
    raw = request.GET.get('from')
    if raw in VALID_SCORECARD_RETURN_SOURCES:
        return raw
    return 'matches'


def _scorecard_back_url(from_source, match_pk=None):
    if from_source == 'dashboard_stats':
        return f"{reverse('dashboard')}?tab=stats"
    if from_source == 'dashboard':
        if match_pk:
            return f"{reverse('dashboard')}?tab=verdict&verdict_match={match_pk}"
        return f"{reverse('dashboard')}?tab=verdict"
    return reverse('match_list')


def _scorecard_back_label(from_source):
    if from_source in {'dashboard_stats', 'dashboard'}:
        return 'Back to Dashboard'
    return 'Back to Matches'


def _active_tournament_matches():
    from apps.tournaments.context_processors import get_active_tournament

    tournament = get_active_tournament()
    if not tournament:
        return Match.objects.none()
    return (
        Match.objects.filter(tournament=tournament)
        .select_related('team_home', 'team_away', 'stadium', 'round')
        .prefetch_related('questions')
        .order_by('match_number')
    )


def _match_squad_player_names(match):
    players = list(
        Player.objects.filter(team__in=[match.team_home_id, match.team_away_id], is_active=True)
        .select_related('team')
        .order_by('team', 'jersey_number')
    )
    return [player.full_name for player in players]


def _save_knockout_result(match, post_data):
    if match.is_group_stage:
        return

    won_in = post_data.get('won_in', Match.WonIn.FT)
    valid_won_in = {choice for choice, _label in Match.WonIn.choices}
    if won_in not in valid_won_in:
        won_in = Match.WonIn.FT

    match.won_in = won_in
    update_fields = ['won_in']

    if won_in == Match.WonIn.PEN:
        home_penalty = post_data.get('home_penalty_score', '').strip()
        away_penalty = post_data.get('away_penalty_score', '').strip()
        if home_penalty.isdigit():
            match.home_penalty_score = int(home_penalty)
        if away_penalty.isdigit():
            match.away_penalty_score = int(away_penalty)
        update_fields.extend(['home_penalty_score', 'away_penalty_score'])
    else:
        match.home_penalty_score = None
        match.away_penalty_score = None
        update_fields.extend(['home_penalty_score', 'away_penalty_score'])

    match.save(update_fields=update_fields)


@login_required
def match_list_view(request):
    from apps.tournaments.context_processors import get_active_tournament

    tournament = get_active_tournament()
    matches = Match.objects.none()
    if tournament:
        matches = (
            Match.objects.filter(tournament=tournament)
            .select_related('team_home', 'team_away', 'stadium', 'round')
            .prefetch_related('questions__question_template')
            .annotate(prediction_count=Count('predictions'))
            .order_by('match_number')
        )
    return render(request, 'matches/list.html', {
        'matches': matches,
        'tournament': tournament,
        'predicted_match_ids': predicted_match_ids(request.user, matches),
        'show_predict': True,
    })


@login_required
def match_scorecard_view(request, pk):
    match = get_object_or_404(
        Match.objects.select_related('team_home', 'team_away', 'stadium', 'round')
        .prefetch_related('questions__question_template'),
        pk=pk,
    )
    return_source = _scorecard_return_source(request)
    back_url = _scorecard_back_url(return_source, match_pk=match.pk)
    verdict_context = MatchScorecardService.context_for_match(match, request.user)
    if not verdict_context['has_predictions']:
        messages.info(request, 'No predictions submitted for this match yet.')
        return redirect(back_url)

    if not verdict_context['rows']:
        messages.info(request, 'You have not predicted this match yet.')
        return redirect(back_url)

    return render(request, 'matches/scorecard.html', {
        'match': match,
        'back_url': back_url,
        'back_label': _scorecard_back_label(return_source),
        **verdict_context,
    })


@login_required
def match_squad_view(request, pk):
    match = get_object_or_404(
        Match.objects.select_related('team_home', 'team_away', 'stadium', 'round'),
        pk=pk,
    )
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
        Match.objects.prefetch_related('questions__question_template').select_related(
            'team_home', 'team_away', 'stadium', 'round',
        ),
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
            return redirect(_predict_redirect_after_save(_predict_return_source(request)))
    else:
        form = MatchPredictionForm(match=match, user=request.user)

    return_source = _predict_return_source(request)

    question_fields = []
    total_points = 0
    for question in match.questions.all():
        field_name = f'question_{question.id}'
        if field_name not in form.fields:
            continue
        template = question.question_template
        template_code = template.code if template else ''
        is_bonus = bool(template and template.category == QuestionTemplate.Category.BONUS)
        if template_code == 'PLAYER_OF_MATCH':
            layout = 'grid'
        elif template_code in ('HOME_GOALS', 'AWAY_GOALS'):
            layout = 'numeric'
            columns = 7
        elif template_code == 'TOTAL_YELLOW_CARDS':
            layout = 'numeric'
            columns = 4
        elif template_code == 'MATCH_WINNER':
            layout = 'winner'
            columns = None
        else:
            layout = 'row'
            columns = None
        question_fields.append({
            'field': form[field_name],
            'layout': layout,
            'columns': columns,
            'points': question.points,
            'is_bonus': is_bonus,
        })
        total_points += question.points

    profile = ensure_user_profile(request.user)
    return render(request, 'matches/predict.html', {
        'match': match,
        'form': form,
        'question_fields': question_fields,
        'total_points': total_points,
        'booster_field': form['point_booster'] if 'point_booster' in form.fields else None,
        'boosters_remaining': profile.point_boosters_remaining,
        'booster_allowed': match.is_group_stage,
        'return_source': return_source,
        'cancel_url': _predict_redirect_after_save(return_source),
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
        _save_knockout_result(match, request.POST)
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
        'won_in_choices': Match.WonIn.choices,
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
    existing_prediction = None
    boosters_remaining = 0
    booster_allowed = False
    booster_field = None
    if target_user and match:
        existing_answers = {}
        existing_prediction = match.predictions.filter(user=target_user).first()
        profile = ensure_user_profile(target_user)
        boosters_remaining = profile.point_boosters_remaining
        booster_allowed = match.is_group_stage
        if prediction := existing_prediction:
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
        if form and 'point_booster' in form.fields:
            booster_field = form['point_booster']

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
        'existing_prediction': existing_prediction,
        'boosters_remaining': boosters_remaining,
        'booster_allowed': booster_allowed,
        'booster_field': booster_field,
    })


@staff_member_required
def admin_manage_match_questions_view(request):
    matches = _active_tournament_matches()
    match_id = request.GET.get('match_id') or request.POST.get('match_id')
    match = None
    question_rows = []
    question_templates = QuestionTemplate.objects.filter(is_active=True).order_by('category', 'code')
    template_defaults = {}
    squad_players = []

    if match_id:
        match = get_object_or_404(
            matches.select_related('team_home', 'team_away'),
            pk=match_id,
        )
        template_defaults = template_defaults_for_match(match)
        squad_players = _match_squad_player_names(match)

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
        'squad_players': squad_players,
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
