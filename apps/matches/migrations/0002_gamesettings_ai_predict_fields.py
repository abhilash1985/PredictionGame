from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamesettings',
            name='ai_predict_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='gamesettings',
            name='ai_predict_model',
            field=models.CharField(default='gemini-2.5-flash', max_length=100),
        ),
        migrations.AddField(
            model_name='gamesettings',
            name='ai_predict_max_users_per_run',
            field=models.PositiveIntegerField(default=500),
        ),
    ]
