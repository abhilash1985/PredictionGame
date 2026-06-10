from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.profile_service import ensure_user_profile
from apps.matches.models import MatchPrediction, QuestionPrediction


class MatchPredictionForm(forms.Form):
    point_booster = forms.BooleanField(required=False, label='Use Point Booster (2× points)')

    def __init__(self, *args, match=None, user=None, **kwargs):
        if match is None or user is None:
            raise TypeError('MatchPredictionForm requires match and user keyword arguments.')

        self.match = match
        self.user = user
        super().__init__(*args, **kwargs)

        existing = MatchPrediction.objects.filter(user=user, match=match).first()
        if existing and existing.point_booster_used:
            self.fields['point_booster'].initial = True

        for question in match.questions.all():
            field_name = f'question_{question.id}'
            if question.options:
                self.fields[field_name] = forms.ChoiceField(
                    label=question.question_text,
                    choices=[(opt, opt) for opt in question.options],
                    required=True,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                )
            else:
                self.fields[field_name] = forms.CharField(
                    label=question.question_text,
                    max_length=255,
                    required=True,
                    widget=forms.TextInput(attrs={'class': 'form-control'}),
                )

            if existing:
                answer = existing.answers.filter(match_question=question).first()
                if answer:
                    self.fields[field_name].initial = answer.user_answer

        profile = ensure_user_profile(user)
        booster_allowed = match.is_group_stage
        if not booster_allowed:
            del self.fields['point_booster']
        elif profile.point_boosters_remaining <= 0 and not (existing and existing.point_booster_used):
            del self.fields['point_booster']

    def clean(self):
        cleaned = super().clean()
        if not self.match.is_prediction_open:
            raise ValidationError('Predictions are closed — this match has already started.')
        use_booster = cleaned.get('point_booster', False)
        if use_booster and not self.match.is_group_stage:
            raise ValidationError('Point boosters are only available for group stage matches.')
        return cleaned

    def save(self):
        use_booster = self.cleaned_data.get('point_booster', False)
        if use_booster and not self.match.is_group_stage:
            raise ValidationError('Point boosters are only available for group stage matches.')
        prediction, created = MatchPrediction.objects.get_or_create(
            user=self.user,
            match=self.match,
        )

        if use_booster and not prediction.point_booster_used:
            profile = ensure_user_profile(self.user)
            if profile.point_boosters_remaining <= 0:
                raise ValidationError('No point boosters remaining.')
            profile.point_boosters_remaining -= 1
            profile.save(update_fields=['point_boosters_remaining'])
            prediction.point_booster_used = True

        for question in self.match.questions.all():
            field_name = f'question_{question.id}'
            answer_value = self.cleaned_data.get(field_name, '')
            QuestionPrediction.objects.update_or_create(
                match_prediction=prediction,
                match_question=question,
                defaults={'user_answer': answer_value},
            )

        prediction.is_ai_generated = False
        prediction.save()
        return prediction


class AdminMatchPredictionForm(MatchPredictionForm):
    """Staff form to create or update a user's prediction regardless of kickoff."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.match.is_group_stage:
            self.fields.pop('point_booster', None)
            return

        existing = MatchPrediction.objects.filter(user=self.user, match=self.match).first()
        if 'point_booster' not in self.fields:
            self.fields['point_booster'] = forms.BooleanField(
                required=False,
                label='Use Point Booster (2× points)',
                initial=bool(existing and existing.point_booster_used),
            )

    def clean(self):
        cleaned = forms.Form.clean(self)
        use_booster = cleaned.get('point_booster', False)
        if use_booster and not self.match.is_group_stage:
            raise ValidationError('Point boosters are only available for group stage matches.')
        return cleaned

    def save(self):
        use_booster = self.cleaned_data.get('point_booster', False)
        if use_booster and not self.match.is_group_stage:
            raise ValidationError('Point boosters are only available for group stage matches.')

        prediction, _created = MatchPrediction.objects.get_or_create(
            user=self.user,
            match=self.match,
        )

        if use_booster and not prediction.point_booster_used:
            profile = ensure_user_profile(self.user)
            if profile.point_boosters_remaining > 0:
                profile.point_boosters_remaining -= 1
                profile.save(update_fields=['point_boosters_remaining'])
            prediction.point_booster_used = True
        elif not use_booster and prediction.point_booster_used:
            profile = ensure_user_profile(self.user)
            profile.point_boosters_remaining += 1
            profile.save(update_fields=['point_boosters_remaining'])
            prediction.point_booster_used = False

        for question in self.match.questions.all():
            field_name = f'question_{question.id}'
            answer_value = self.cleaned_data.get(field_name, '')
            QuestionPrediction.objects.update_or_create(
                match_prediction=prediction,
                match_question=question,
                defaults={'user_answer': answer_value},
            )

        prediction.is_ai_generated = False
        prediction.save()
        return prediction


def admin_user_choices():
    User = get_user_model()
    choices = [('', '— Select user —')]
    for user in User.objects.select_related('profile').filter(
        is_active=True,
        profile__isnull=False,
    ).order_by('profile__display_name', 'email'):
        choices.append((user.pk, user.display_name))
    return choices


def admin_match_choices(matches):
    choices = [('', '— Select match —')]
    for match in matches:
        label = f'Match {match.match_number}: {match.team_home.short_name} vs {match.team_away.short_name}'
        choices.append((match.pk, label))
    return choices
