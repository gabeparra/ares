from django.db import models


class ChatSession(models.Model):
    """
    Chat session metadata.

    session_id is generated client-side (see React) and used as the primary key.
    """

    session_id = models.CharField(max_length=128, primary_key=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    pinned = models.BooleanField(default=False)
    model = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["pinned", "updated_at"])]

    def __str__(self) -> str:
        return self.session_id


class ConversationMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_ERROR = "error"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
        (ROLE_SYSTEM, "System"),
        (ROLE_ERROR, "Error"),
    ]

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.session.session_id}:{self.role}@{self.created_at.isoformat()}"


class AppSetting(models.Model):
    """
    Simple key/value settings persisted in the Django DB.
    """

    key = models.CharField(max_length=128, unique=True)
    value = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.key


class AISelfMemory(models.Model):
    """
    AI self-knowledge storage for ARES identity and memory.
    
    Categories:
    - identity: Core facts (name, birth_date, creator, purpose)
    - milestone: Important events with timestamps
    - observation: Things the AI notices about itself
    - preference: Emergent preferences/tendencies
    - relationship: Facts about relationship with users
    """
    
    CATEGORY_IDENTITY = "identity"
    CATEGORY_MILESTONE = "milestone"
    CATEGORY_OBSERVATION = "observation"
    CATEGORY_PREFERENCE = "preference"
    CATEGORY_RELATIONSHIP = "relationship"
    
    CATEGORY_CHOICES = [
        (CATEGORY_IDENTITY, "Identity"),
        (CATEGORY_MILESTONE, "Milestone"),
        (CATEGORY_OBSERVATION, "Observation"),
        (CATEGORY_PREFERENCE, "Preference"),
        (CATEGORY_RELATIONSHIP, "Relationship"),
    ]
    
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    memory_key = models.CharField(max_length=128)
    memory_value = models.TextField()
    importance = models.IntegerField(default=5)  # 1-10 scale
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["category", "memory_key"]
        ordering = ["-importance", "-updated_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["importance"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.category}:{self.memory_key}"


class UserFact(models.Model):
    """
    User facts learned from conversations.
    
    Stores information about users like name, job, interests, etc.
    These facts are injected into context to personalize responses.
    
    Fact types:
    - identity: Name, age, location
    - professional: Job, company, skills
    - personal: Hobbies, interests, preferences
    - context: Situational facts (current project, etc.)
    """
    
    TYPE_IDENTITY = "identity"
    TYPE_PROFESSIONAL = "professional"
    TYPE_PERSONAL = "personal"
    TYPE_CONTEXT = "context"
    
    TYPE_CHOICES = [
        (TYPE_IDENTITY, "Identity"),
        (TYPE_PROFESSIONAL, "Professional"),
        (TYPE_PERSONAL, "Personal"),
        (TYPE_CONTEXT, "Context"),
    ]
    
    SOURCE_CONVERSATION = "conversation"
    SOURCE_API = "api"
    SOURCE_TELEGRAM = "telegram"
    
    SOURCE_CHOICES = [
        (SOURCE_CONVERSATION, "Conversation"),
        (SOURCE_API, "API"),
        (SOURCE_TELEGRAM, "Telegram"),
    ]
    
    user_id = models.CharField(max_length=128, default="default")
    fact_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    fact_key = models.CharField(max_length=128)
    fact_value = models.TextField()
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default=SOURCE_API)
    confidence = models.FloatField(default=1.0)  # 0.0 to 1.0
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["user_id", "fact_type", "fact_key"]
        ordering = ["user_id", "fact_type", "fact_key"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["fact_type"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.user_id}:{self.fact_type}.{self.fact_key}"


class UserPreference(models.Model):
    """
    User preferences and settings.
    
    Stores user-specific settings like communication style,
    notification preferences, etc.
    """
    
    user_id = models.CharField(max_length=128, default="default")
    preference_key = models.CharField(max_length=128)
    preference_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["user_id", "preference_key"]
        ordering = ["user_id", "preference_key"]
        indexes = [
            models.Index(fields=["user_id"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.user_id}:{self.preference_key}"


class ConversationSummary(models.Model):
    """
    Summaries of past conversations.
    
    Used for long-term memory - summarizes key points from
    conversations to be used in future context.
    """
    
    session = models.OneToOneField(
        ChatSession, on_delete=models.CASCADE, related_name="summary"
    )
    user_id = models.CharField(max_length=128, default="default")
    summary = models.TextField()
    topics = models.JSONField(default=list)  # List of topic strings
    key_facts = models.JSONField(default=list)  # Facts extracted from conversation
    message_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"]),
        ]
    
    def __str__(self) -> str:
        return f"Summary:{self.session.session_id}"


