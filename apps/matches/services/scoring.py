from django.db import transaction

from apps.matches.models import MatchPrediction, QuestionPrediction


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
        return ScoringService.score_match(match)
