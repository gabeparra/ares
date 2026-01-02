# Generated manually for Google Calendar integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_add_code_memory_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleCalendarCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('token', models.TextField()),
                ('refresh_token', models.TextField(blank=True)),
                ('token_uri', models.CharField(default='https://oauth2.googleapis.com/token', max_length=255)),
                ('client_id', models.CharField(blank=True, max_length=255)),
                ('client_secret', models.CharField(blank=True, max_length=255)),
                ('scopes', models.JSONField(default=list)),
                ('calendar_id', models.CharField(default='primary', max_length=255)),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_sync_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user_id', 'enabled'], name='api_googleca_user_id_enabled_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ScheduledTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('task_type', models.CharField(choices=[('good_morning', 'Good Morning Message'), ('reminder', 'Reminder'), ('custom', 'Custom Task')], max_length=32)),
                ('calendar_event_id', models.CharField(blank=True, max_length=255)),
                ('calendar_event_title', models.CharField(max_length=255)),
                ('scheduled_time', models.DateTimeField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=32)),
                ('task_data', models.JSONField(default=dict)),
                ('executed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['scheduled_time'],
                'indexes': [
                    models.Index(fields=['user_id', 'status', 'scheduled_time'], name='api_schedul_user_id_status_scheduled_idx'),
                    models.Index(fields=['scheduled_time', 'status'], name='api_schedul_scheduled_status_idx'),
                    models.Index(fields=['calendar_event_id'], name='api_schedul_calendar_event_id_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='googlecalendarcredential',
            unique_together={('user_id',)},
        ),
    ]

