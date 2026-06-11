import json
import logging

from apps.matches.models import MatchQuestion

logger = logging.getLogger(__name__)


def validate_answers(questions, answers):
    """
    Return a dict of question_id -> answer for valid entries only.
    question_id keys in answers may be str or int.
    """
    question_map = {question.pk: question for question in questions}
    validated = {}

    for raw_question_id, raw_answer in (answers or {}).items():
        try:
            question_id = int(raw_question_id)
        except (TypeError, ValueError):
            continue

        question = question_map.get(question_id)
        if question is None:
            continue

        answer = str(raw_answer).strip()
        options = [str(option) for option in (question.options or [])]
        if options and answer not in options:
            logger.warning(
                'AI answer %r not in options for question %s (%s)',
                answer,
                question_id,
                question.question_template.code if question.question_template else 'unknown',
            )
            continue

        validated[question_id] = answer

    return validated


def missing_question_ids(questions, validated_answers):
    question_ids = {question.pk for question in questions}
    return sorted(question_ids - set(validated_answers.keys()))
