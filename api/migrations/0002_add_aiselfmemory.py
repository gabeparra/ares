from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AISelfMemory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[
                    ('identity', 'Identity'),
                    ('milestone', 'Milestone'),
                    ('observation', 'Observation'),
                    ('preference', 'Preference'),
                    ('relationship', 'Relationship'),
                ], max_length=32)),
                ('memory_key', models.CharField(max_length=128)),
                ('memory_value', models.TextField()),
                ('importance', models.IntegerField(default=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-importance', '-updated_at'],
                'unique_together': {('category', 'memory_key')},
            },
        ),
        migrations.AddIndex(
            model_name='aiselfmemory',
            index=models.Index(fields=['category'], name='api_aiselfm_categor_5a7c8f_idx'),
        ),
        migrations.AddIndex(
            model_name='aiselfmemory',
            index=models.Index(fields=['importance'], name='api_aiselfm_importa_8b4e2a_idx'),
        ),
    ]

