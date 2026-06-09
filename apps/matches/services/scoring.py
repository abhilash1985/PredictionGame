from django.db import transaction

from apps.matches.models import Match, MatchPrediction, QuestionPrediction


class ScoringService:
    @staticmethod
    def score_match_prediction(match_prediction):
        total = 0
        for answer in match_prediction.answers.select_related('match_question'):
            mq = answer.match_question
            if mq.correct_answer is None:
                answer.points_awarded = None
            elif answer.user_answer == mq.correct_answer:
                answer.points_awarded = mq.points
                total += mq.points
            else:
                answer.points_awarded = 0
            answer.save(update_fields=['points_awarded'])

        if match_prediction.point_booster_used:
            total *= 2

        match_prediction.total_points = total
        match_prediction.save(update_fields=['total_points'])
        return total

    @staticmethod
    def score_match(match):
        scored = 0
        for prediction in match.predictions.prefetch_related('answers__match_question'):
            ScoringService.score_match_prediction(prediction)
            scored += 1
        return scored

    @staticmethod
    @transaction.atomic
    def set_correct_answers(match, answers_dict):
        """answers_dict: {match_question_id: correct_answer}"""
        for question in match.questions.all():
            key = str(question.id)
            if key in answers_dict:
                question.correct_answer = answers_dict[key]
                question.save(update_fields=['correct_answer'])
        ScoringService._sync_match_result_from_questions(match)
        return ScoringService.score_match(match)

    @staticmethod
    def _sync_match_result_from_questions(match):
        home_score = None
        away_score = None
        for question in match.questions.select_related('question_template'):
            template = question.question_template
            if not template or not question.correct_answer:
                continue
            try:
                goals = int(question.correct_answer)
            except (TypeError, ValueError):
                continue
            if template.code == 'HOME_GOALS':
                home_score = goals
            elif template.code == 'AWAY_GOALS':
                away_score = goals

        if home_score is None or away_score is None:
            return

        match.home_score = home_score
        match.away_score = away_score
        match.status = Match.Status.FINISHED
        match.save(update_fields=['home_score', 'away_score', 'status'])
