import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Ensure a superuser exists for DJANGO_SUPERUSER_EMAIL: create one or promote an existing user.'
    )

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

        if not email:
            self.stdout.write('Skipping bootstrap_admin: set DJANGO_SUPERUSER_EMAIL.')
            return

        User = get_user_model()
        existing_user = User.objects.filter(email__iexact=email).first()

        if existing_user:
            if existing_user.is_superuser and existing_user.is_staff:
                self.stdout.write(self.style.WARNING(f'Superuser already configured for {email}.'))
                return

            existing_user.is_staff = True
            existing_user.is_superuser = True
            if password:
                existing_user.set_password(password)
            existing_user.save()
            self.stdout.write(self.style.SUCCESS(f'Promoted existing user {email} to superuser.'))
            return

        if not password:
            self.stdout.write(
                'Skipping bootstrap_admin: set DJANGO_SUPERUSER_PASSWORD to create a new superuser.',
            )
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Created superuser {email}.'))
