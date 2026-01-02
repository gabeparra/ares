from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0003_add_user_memory'),
    ]

    operations = [
        migrations.CreateModel(
            name='MemorySpot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('memory_type', models.CharField(choices=[
                    ('user_fact', 'User Fact'),
                    ('user_preference', 'User Preference'),
                    ('ai_self_memory', 'AI Self Memory'),
                    ('capability', 'Capability'),
                    ('general', 'General'),
                ], max_length=32)),
                ('content', models.TextField()),
                ('metadata', models.JSONField(default=dict)),
                ('confidence', models.FloatField(default=0.5)),
                ('importance', models.IntegerField(default=5)),
                ('status', models.CharField(choices=[
                    ('extracted', 'Extracted'),
                    ('reviewed', 'Reviewed'),
                    ('applied', 'Applied'),
                    ('rejected', 'Rejected'),
                ], default='extracted', max_length=32)),
                ('source_conversation', models.TextField(blank=True)),
                ('extracted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='memory_spots', to='api.chatsession')),
            ],
            options={
                'ordering': ['-extracted_at'],
            },
        ),
        migrations.CreateModel(
            name='AICapability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('capability_name', models.CharField(max_length=128)),
                ('domain', models.CharField(choices=[
                    ('general', 'General'),
                    ('coding', 'Coding'),
                    ('reasoning', 'Reasoning'),
                    ('creative', 'Creative'),
                    ('analysis', 'Analysis'),
                    ('memory', 'Memory'),
                    ('tools', 'Tools'),
                ], default='general', max_length=32)),
                ('description', models.TextField()),
                ('proficiency_level', models.IntegerField(default=1)),
                ('evidence', models.JSONField(default=list)),
                ('last_demonstrated', models.DateTimeField(blank=True, null=True)),
                ('improvement_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['domain', '-proficiency_level', 'capability_name'],
                'unique_together': {('capability_name', 'domain')},
            },
        ),
        migrations.AddIndex(
            model_name='memoryspot',
            index=models.Index(fields=['user_id', 'status'], name='api_memorys_user_id_status_idx'),
        ),
        migrations.AddIndex(
            model_name='memoryspot',
            index=models.Index(fields=['memory_type', 'status'], name='api_memorys_memory_t_status_idx'),
        ),
        migrations.AddIndex(
            model_name='memoryspot',
            index=models.Index(fields=['session'], name='api_memorys_session_idx'),
        ),
        migrations.AddIndex(
            model_name='aicapability',
            index=models.Index(fields=['domain', 'proficiency_level'], name='api_aicapab_domain_prof_idx'),
        ),
    ]

