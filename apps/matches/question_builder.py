from apps.matches.data.question_bank import (
    default_options_for_code,
    render_question_text,
    template_by_code,
)
from apps.matches.models import MatchQuestion, QuestionTemplate


def default_options_for_template(template, match):
    options = default_options_for_code(template.code, match)
    if options:
        return options

    code = template.code
    if code == 'MATCH_WINNER':
        return [match.team_home.name, match.team_away.name, 'Draw', 'No Results']
    if code in ('HOME_GOALS', 'AWAY_GOALS'):
        return [str(number) for number in range(0, 6)] + ['5+']
    if code == 'TOTAL_YELLOW_CARDS':
        return [str(number) for number in range(0, 8)]
    if code == 'PLAYER_OF_MATCH':
        players = list(match.team_home.players.filter(is_active=True)) + list(
            match.team_away.players.filter(is_active=True)
        )
        return [player.full_name for player in players]
    return []


def template_defaults_for_match(match):
    defaults = {}
    for template in QuestionTemplate.objects.filter(is_active=True).order_by('category', 'code'):
        entry = template_by_code().get(template.code)
        question_text = render_question_text(entry, match) if entry else template.render_text(match)
        defaults[str(template.pk)] = {
            'code': template.code,
            'label': template.code.replace('_', ' ').title(),
            'question_text': question_text,
            'points': template.default_points,
            'options': '\n'.join(default_options_for_template(template, match)),
        }
    return defaults


def parse_options_text(text):
    return [line.strip() for line in (text or '').splitlines() if line.strip()]


def question_row_from_post(request, index):
    template_id = request.POST.get(f'template_id_{index}', '').strip()
    if not template_id:
        return None
    return {
        'id': request.POST.get(f'question_id_{index}', '').strip(),
        'delete': request.POST.get(f'delete_{index}') == '1',
        'template_id': template_id,
        'question_text': request.POST.get(f'question_text_{index}', '').strip(),
        'points': request.POST.get(f'points_{index}', '').strip(),
        'options': request.POST.get(f'options_{index}', ''),
    }


def post_question_indices(request):
    indices = []
    for key in request.POST:
        if key.startswith('template_id_'):
            indices.append(key.removeprefix('template_id_'))
    return sorted(indices, key=lambda value: int(value) if value.isdigit() else value)


def save_match_questions(match, rows):
    saved = 0
    for sort_order, row in enumerate(rows):
        if row['delete']:
            if row['id']:
                MatchQuestion.objects.filter(pk=row['id'], match=match).delete()
            continue

        template = QuestionTemplate.objects.get(pk=row['template_id'])
        options = parse_options_text(row['options'])
        if not options:
            options = default_options_for_template(template, match)

        entry = template_by_code().get(template.code)
        question_text = row['question_text'] or (
            render_question_text(entry, match) if entry else template.render_text(match)
        )
        points = template.default_points
        if row['points'].isdigit():
            points = int(row['points'])

        if row['id']:
            question = MatchQuestion.objects.get(pk=row['id'], match=match)
            question.question_template = template
            question.question_text = question_text
            question.options = options
            question.points = points
            question.sort_order = sort_order
            question.save()
        else:
            MatchQuestion.objects.create(
                match=match,
                question_template=template,
                question_text=question_text,
                options=options,
                points=points,
                sort_order=sort_order,
            )
        saved += 1
    return saved


def existing_question_rows(match):
    rows = []
    for question in match.questions.select_related('question_template').all():
        rows.append({
            'id': question.pk,
            'template_id': question.question_template_id or '',
            'question_text': question.question_text,
            'points': question.points,
            'options': '\n'.join(question.options or []),
        })
    return rows
