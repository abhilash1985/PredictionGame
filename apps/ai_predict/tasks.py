from celery import shared_task

from apps.ai_predict.services import AiPredictService


@shared_task
def run_ai_predictions():
    return AiPredictService.run_scheduled_predictions()
