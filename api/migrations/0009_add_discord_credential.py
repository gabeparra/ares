# Generated manually for Discord integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_add_user_account_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscordCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default', max_length=128)),
                ('discord_user_id', models.CharField(max_length=128)),
                ('discord_username', models.CharField(max_length=255)),
                ('discord_discriminator', models.CharField(blank=True, max_length=4)),
                ('discord_avatar', models.CharField(blank=True, max_length=255)),
                ('access_token', models.TextField()),
                ('refresh_token', models.TextField(blank=True)),
                ('token_type', models.CharField(default='Bearer', max_length=32)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('scopes', models.JSONField(default=list)),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_sync_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user_id', 'enabled'], name='api_discord_user_id_enabled_idx'),
                    models.Index(fields=['discord_user_id'], name='api_discord_discord_user_id_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='discordcredential',
            unique_together={('user_id', 'discord_user_id')},
        ),
    ]

