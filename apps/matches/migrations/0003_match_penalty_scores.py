from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0002_gamesettings_ai_predict_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='home_penalty_score',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='away_penalty_score',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='match',
            options={'ordering': ['match_number']},
        ),
    ]
