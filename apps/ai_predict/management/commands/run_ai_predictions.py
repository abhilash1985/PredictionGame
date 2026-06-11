from django.core.management.base import BaseCommand

from apps.ai_predict.services import AiPredictService


class Command(BaseCommand):
    help = 'Create AI predictions for enabled users within the pre-kickoff window.'

    def handle(self, *args, **options):
        created = AiPredictService.run_scheduled_predictions()
        self.stdout.write(self.style.SUCCESS(f'Created {created} AI prediction(s).'))
