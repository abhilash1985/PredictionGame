from django.core.management.base import BaseCommand, CommandError

from apps.ai_predict.services import AiPredictService


class Command(BaseCommand):
    help = (
        'Create AI predictions for enabled users. '
        'Default: matches kicking off within GameSettings.ai_predict_hours_before. '
        'Use --upcoming-matches for manual runs on the next N fixtures.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--upcoming-matches',
            type=int,
            metavar='N',
            help='Manual mode: predict for the next N upcoming scheduled matches (ignores hours-before window).',
        )

    def handle(self, *args, **options):
        upcoming_match_limit = options.get('upcoming_matches')
        if upcoming_match_limit is not None and upcoming_match_limit < 1:
            raise CommandError('--upcoming-matches must be a positive integer.')

        if upcoming_match_limit:
            self.stdout.write(
                self.style.NOTICE(f'Mode: next {upcoming_match_limit} upcoming match(es).'),
            )
        self.stdout.write(
            'Running AI predictions (one Gemini call per enabled user per match when configured). '
            'This may take several minutes — watch logs for progress.',
        )

        created = AiPredictService.run_scheduled_predictions(
            upcoming_match_limit=upcoming_match_limit,
        )
        self.stdout.write(self.style.SUCCESS(f'Created {created} AI prediction(s).'))
