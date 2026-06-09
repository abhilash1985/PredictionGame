def predicted_match_ids(user, matches=None):
    if not user.is_authenticated:
        return set()

    from apps.matches.models import MatchPrediction

    qs = MatchPrediction.objects.filter(user=user)
    if matches is not None:
        match_ids = [match.pk for match in matches]
        qs = qs.filter(match_id__in=match_ids)
    return set(qs.values_list('match_id', flat=True))
