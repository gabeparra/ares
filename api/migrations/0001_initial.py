from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AppSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128, unique=True)),
                ("value", models.TextField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="ChatSession",
            fields=[
                ("session_id", models.CharField(max_length=128, primary_key=True, serialize=False)),
                ("title", models.CharField(blank=True, max_length=255, null=True)),
                ("pinned", models.BooleanField(default=False)),
                ("model", models.CharField(blank=True, max_length=128, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="ConversationMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant"), ("system", "System"), ("error", "Error")], max_length=32)),
                ("message", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="api.chatsession")),
            ],
        ),
        migrations.AddIndex(
            model_name="chatsession",
            index=models.Index(fields=["pinned", "updated_at"], name="api_chatses_pinned_7b1e4a_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationmessage",
            index=models.Index(fields=["session", "created_at"], name="api_convers_session_1b74bb_idx"),
        ),
    ]


