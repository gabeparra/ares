from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_add_aiselfmemory'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('fact_type', models.CharField(choices=[
                    ('identity', 'Identity'),
                    ('professional', 'Professional'),
                    ('personal', 'Personal'),
                    ('context', 'Context'),
                ], max_length=32)),
                ('fact_key', models.CharField(max_length=128)),
                ('fact_value', models.TextField()),
                ('source', models.CharField(choices=[
                    ('conversation', 'Conversation'),
                    ('api', 'API'),
                    ('telegram', 'Telegram'),
                ], default='api', max_length=32)),
                ('confidence', models.FloatField(default=1.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['user_id', 'fact_type', 'fact_key'],
                'unique_together': {('user_id', 'fact_type', 'fact_key')},
            },
        ),
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('preference_key', models.CharField(max_length=128)),
                ('preference_value', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['user_id', 'preference_key'],
                'unique_together': {('user_id', 'preference_key')},
            },
        ),
        migrations.CreateModel(
            name='ConversationSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('summary', models.TextField()),
                ('topics', models.JSONField(default=list)),
                ('key_facts', models.JSONField(default=list)),
                ('message_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='summary', to='api.chatsession')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='userfact',
            index=models.Index(fields=['user_id'], name='api_userfac_user_id_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='userfact',
            index=models.Index(fields=['fact_type'], name='api_userfac_fact_ty_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='userpreference',
            index=models.Index(fields=['user_id'], name='api_userpre_user_id_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='conversationsummary',
            index=models.Index(fields=['user_id'], name='api_convers_user_id_j0k1l2_idx'),
        ),
    ]

