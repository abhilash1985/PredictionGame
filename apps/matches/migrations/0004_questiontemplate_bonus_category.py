from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0003_match_penalty_scores'),
    ]

    operations = [
        migrations.AlterField(
            model_name='questiontemplate',
            name='category',
            field=models.CharField(
                choices=[
                    ('winner', 'Winner'),
                    ('goals', 'Goals'),
                    ('player', 'Player'),
                    ('stats', 'Stats'),
                    ('bonus', 'Bonus'),
                    ('random', 'Random'),
                ],
                default='random',
                max_length=20,
            ),
        ),
    ]
