from apps.matches.models import MatchPrediction


class MatchScorecardService:
    @staticmethod
    def build(match):
        questions = list(
            match.questions.select_related('question_template').order_by('sort_order', 'id')
        )
        is_scored = any(question.correct_answer for question in questions)

        predictions = (
            MatchPrediction.objects.filter(match=match)
            .select_related('user', 'user__profile')
            .prefetch_related('answers__match_question')
            .order_by('user__profile__display_name')
        )

        rows = []
        for prediction in predictions:
            detail = MatchScorecardService._prediction_detail(prediction, questions, is_scored)
            rows.append({
                **detail,
                'user_id': prediction.user_id,
                'display_name': prediction.user.display_name,
            })

        return {
            'questions': questions,
            'is_scored': is_scored,
            'rows': rows,
        }

    @staticmethod
    def visible_rows(scorecard_data, viewer, match):
        can_see_all = match.has_started or viewer.is_staff
        all_rows = scorecard_data['rows']

        for row in all_rows:
            row['is_current_user'] = row['user_id'] == viewer.id

        if can_see_all:
            return all_rows, can_see_all

        return [row for row in all_rows if row['is_current_user']], can_see_all

    @staticmethod
    def top_scorer_user_ids(rows):
        if not rows:
            return set()
        max_points = max(row['total_points'] for row in rows)
        if max_points <= 0:
            return set()
        return {row['user_id'] for row in rows if row['total_points'] == max_points}

    @staticmethod
    def context_for_match(match, viewer):
        scorecard_data = MatchScorecardService.build(match)
        rows, can_see_all = MatchScorecardService.visible_rows(scorecard_data, viewer, match)
        top_scorer_ids = MatchScorecardService.top_scorer_user_ids(rows)

        for row in rows:
            row['is_top_scorer'] = row['user_id'] in top_scorer_ids

        return {
            'questions': scorecard_data['questions'],
            'is_scored': scorecard_data['is_scored'],
            'rows': rows,
            'can_see_all': can_see_all,
            'match_started': match.has_started,
            'has_predictions': bool(scorecard_data['rows']),
        }

    @staticmethod
    def _prediction_detail(prediction, questions, is_scored):
        answers_by_question_id = {
            answer.match_question_id: answer for answer in prediction.answers.all()
        }

        answer_rows = []
        base_points = 0
        for question in questions:
            answer = answers_by_question_id.get(question.id)
            user_answer = answer.user_answer if answer else '—'
            points_awarded = answer.points_awarded if answer else None

            if is_scored and question.correct_answer:
                if points_awarded and points_awarded > 0:
                    status = 'correct'
                    base_points += question.points
                elif points_awarded == 0:
                    status = 'wrong'
                else:
                    status = 'pending'
            else:
                status = 'pending'

            answer_rows.append({
                'question': question,
                'user_answer': user_answer,
                'points_awarded': points_awarded,
                'status': status,
            })

        total_points = prediction.total_points
        if prediction.point_booster_used and base_points > 0:
            booster_bonus = total_points - base_points
        else:
            booster_bonus = 0

        return {
            'prediction': prediction,
            'answer_rows': answer_rows,
            'base_points': base_points if is_scored else total_points,
            'booster_bonus': booster_bonus,
            'total_points': total_points,
            'point_booster_used': prediction.point_booster_used,
        }
