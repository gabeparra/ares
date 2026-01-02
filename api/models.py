from django.db import models
from encrypted_model_fields.fields import EncryptedTextField, EncryptedCharField


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


class MemorySpot(models.Model):
    """
    Extracted memory spots from conversations.
    
    These are key insights, facts, or learnings extracted from conversations
    using AI analysis. They can be automatically integrated into the memory system.
    """
    
    TYPE_USER_FACT = "user_fact"
    TYPE_USER_PREFERENCE = "user_preference"
    TYPE_AI_SELF_MEMORY = "ai_self_memory"
    TYPE_CAPABILITY = "capability"
    TYPE_GENERAL = "general"
    
    TYPE_CHOICES = [
        (TYPE_USER_FACT, "User Fact"),
        (TYPE_USER_PREFERENCE, "User Preference"),
        (TYPE_AI_SELF_MEMORY, "AI Self Memory"),
        (TYPE_CAPABILITY, "Capability"),
        (TYPE_GENERAL, "General"),
    ]
    
    STATUS_EXTRACTED = "extracted"
    STATUS_REVIEWED = "reviewed"
    STATUS_APPLIED = "applied"
    STATUS_REJECTED = "rejected"
    
    STATUS_CHOICES = [
        (STATUS_EXTRACTED, "Extracted"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_REJECTED, "Rejected"),
    ]
    
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="memory_spots", null=True, blank=True
    )
    user_id = models.CharField(max_length=128, default="default")
    memory_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    content = models.TextField()  # The extracted memory content
    metadata = models.JSONField(default=dict)  # Additional structured data
    confidence = models.FloatField(default=0.5)  # 0.0 to 1.0
    importance = models.IntegerField(default=5)  # 1-10 scale
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_EXTRACTED)
    source_conversation = models.TextField(blank=True)  # Excerpt from conversation
    extracted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-extracted_at"]
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["memory_type", "status"]),
            models.Index(fields=["session"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.memory_type}: {self.content[:50]}..."


class AICapability(models.Model):
    """
    Tracks AI capabilities and improvements over time.
    
    Records what the AI can do, how well it performs, and tracks
    improvements in various domains.
    """
    
    DOMAIN_GENERAL = "general"
    DOMAIN_CODING = "coding"
    DOMAIN_REASONING = "reasoning"
    DOMAIN_CREATIVE = "creative"
    DOMAIN_ANALYSIS = "analysis"
    DOMAIN_MEMORY = "memory"
    DOMAIN_TOOLS = "tools"
    
    DOMAIN_CHOICES = [
        (DOMAIN_GENERAL, "General"),
        (DOMAIN_CODING, "Coding"),
        (DOMAIN_REASONING, "Reasoning"),
        (DOMAIN_CREATIVE, "Creative"),
        (DOMAIN_ANALYSIS, "Analysis"),
        (DOMAIN_MEMORY, "Memory"),
        (DOMAIN_TOOLS, "Tools"),
    ]
    
    capability_name = models.CharField(max_length=128)
    domain = models.CharField(max_length=32, choices=DOMAIN_CHOICES, default=DOMAIN_GENERAL)
    description = models.TextField()
    proficiency_level = models.IntegerField(default=1)  # 1-10 scale
    evidence = models.JSONField(default=list)  # Examples/proof of capability
    last_demonstrated = models.DateTimeField(null=True, blank=True)
    improvement_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["capability_name", "domain"]
        ordering = ["domain", "-proficiency_level", "capability_name"]
        indexes = [
            models.Index(fields=["domain", "proficiency_level"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.domain}:{self.capability_name} (Level {self.proficiency_level})"


class CodeSnapshot(models.Model):
    """
    Snapshot of a code file at a specific point in time.
    
    Stores the full content of code files to track changes over time
    and provide context to the AI about the codebase.
    """
    
    file_path = models.CharField(max_length=512)  # Relative path from workspace root
    file_name = models.CharField(max_length=255)
    file_extension = models.CharField(max_length=32, blank=True)
    content = models.TextField()  # Full file content
    line_count = models.IntegerField(default=0)
    language = models.CharField(max_length=64, blank=True)  # Detected language (python, javascript, etc.)
    sha256_hash = models.CharField(max_length=64)  # Hash of content for change detection
    indexed_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(null=True, blank=True)  # File modification time
    
    class Meta:
        unique_together = ["file_path", "sha256_hash"]
        ordering = ["-indexed_at"]
        indexes = [
            models.Index(fields=["file_path"]),
            models.Index(fields=["file_extension"]),
            models.Index(fields=["language"]),
            models.Index(fields=["indexed_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.file_path} (snapshot {self.id})"


class CodeChange(models.Model):
    """
    Tracks changes to code files over time.
    
    Records when code was modified, what changed, and by whom (AI or user).
    """
    
    CHANGE_TYPE_CREATED = "created"
    CHANGE_TYPE_MODIFIED = "modified"
    CHANGE_TYPE_DELETED = "deleted"
    CHANGE_TYPE_AI_REVISION = "ai_revision"
    
    CHANGE_TYPE_CHOICES = [
        (CHANGE_TYPE_CREATED, "Created"),
        (CHANGE_TYPE_MODIFIED, "Modified"),
        (CHANGE_TYPE_DELETED, "Deleted"),
        (CHANGE_TYPE_AI_REVISION, "AI Revision"),
    ]
    
    SOURCE_USER = "user"
    SOURCE_AI = "ai"
    SOURCE_SYSTEM = "system"
    
    SOURCE_CHOICES = [
        (SOURCE_USER, "User"),
        (SOURCE_AI, "AI"),
        (SOURCE_SYSTEM, "System"),
    ]
    
    file_path = models.CharField(max_length=512)
    change_type = models.CharField(max_length=32, choices=CHANGE_TYPE_CHOICES)
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default=SOURCE_USER)
    
    # Snapshot references
    old_snapshot = models.ForeignKey(
        CodeSnapshot, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="changes_from"
    )
    new_snapshot = models.ForeignKey(
        CodeSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="changes_to"
    )
    
    # Change metadata
    diff_summary = models.TextField(blank=True)  # AI-generated summary of changes
    change_reason = models.TextField(blank=True)  # Why the change was made
    model_used = models.CharField(max_length=128, blank=True)  # Model that made the change (if AI)
    session_id = models.CharField(max_length=128, blank=True)  # Chat session that triggered change
    
    # Statistics
    lines_added = models.IntegerField(default=0)
    lines_removed = models.IntegerField(default=0)
    lines_changed = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["file_path", "created_at"]),
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["change_type"]),
            models.Index(fields=["session_id"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.file_path} - {self.change_type} ({self.source})"


class CodeMemory(models.Model):
    """
    Extracted memories about the codebase structure and patterns.
    
    Stores AI-generated insights about the codebase that can be used
    to provide better context in future conversations.
    """
    
    CATEGORY_ARCHITECTURE = "architecture"
    CATEGORY_PATTERNS = "patterns"
    CATEGORY_DEPENDENCIES = "dependencies"
    CATEGORY_FEATURES = "features"
    CATEGORY_STRUCTURE = "structure"
    CATEGORY_IMPROVEMENTS = "improvements"
    
    CATEGORY_CHOICES = [
        (CATEGORY_ARCHITECTURE, "Architecture"),
        (CATEGORY_PATTERNS, "Patterns"),
        (CATEGORY_DEPENDENCIES, "Dependencies"),
        (CATEGORY_FEATURES, "Features"),
        (CATEGORY_STRUCTURE, "Structure"),
        (CATEGORY_IMPROVEMENTS, "Improvements"),
    ]
    
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    memory_key = models.CharField(max_length=255)  # Unique identifier for this memory
    memory_value = models.TextField()  # The actual memory content
    related_files = models.JSONField(default=list)  # List of file paths related to this memory
    importance = models.IntegerField(default=5)  # 1-10 scale
    confidence = models.FloatField(default=0.5)  # 0.0 to 1.0
    
    # Metadata
    extracted_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(null=True, blank=True)  # When this memory was last verified
    verification_count = models.IntegerField(default=0)  # How many times this was verified
    
    class Meta:
        unique_together = ["category", "memory_key"]
        ordering = ["-importance", "-extracted_at"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["importance"]),
            models.Index(fields=["extracted_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.category}:{self.memory_key}"


class GoogleCalendarCredential(models.Model):
    """
    Stores Google Calendar OAuth credentials for users.

    Each user can have one set of credentials that allows ARES
    to read their calendar and perform scheduled tasks.

    SECURITY: Sensitive fields (token, refresh_token, client_secret) are encrypted at rest.
    """

    user_id = models.CharField(max_length=128, default="default")
    token = EncryptedTextField()  # SECURITY: Encrypted OAuth token (JSON)
    refresh_token = EncryptedTextField(blank=True)  # SECURITY: Encrypted refresh token
    token_uri = models.CharField(max_length=255, default="https://oauth2.googleapis.com/token")
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = EncryptedCharField(max_length=255, blank=True)  # SECURITY: Encrypted client secret
    scopes = models.JSONField(default=list)  # List of granted scopes
    calendar_id = models.CharField(max_length=255, default="primary")  # Which calendar to use
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ["user_id"]
        indexes = [
            models.Index(fields=["user_id", "enabled"]),
        ]
    
    def __str__(self) -> str:
        return f"GoogleCalendarCredential:{self.user_id}"


class ScheduledTask(models.Model):
    """
    Scheduled tasks that ARES should perform based on calendar events.
    
    Tasks are created from calendar events with specific keywords or patterns.
    For example, an event titled "ARES: Good Morning" will trigger a good morning message.
    """
    
    TASK_GOOD_MORNING = "good_morning"
    TASK_REMINDER = "reminder"
    TASK_CUSTOM = "custom"
    
    TASK_TYPE_CHOICES = [
        (TASK_GOOD_MORNING, "Good Morning Message"),
        (TASK_REMINDER, "Reminder"),
        (TASK_CUSTOM, "Custom Task"),
    ]
    
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    
    user_id = models.CharField(max_length=128, default="default")
    task_type = models.CharField(max_length=32, choices=TASK_TYPE_CHOICES)
    calendar_event_id = models.CharField(max_length=255, blank=True)  # Google Calendar event ID
    calendar_event_title = models.CharField(max_length=255)
    scheduled_time = models.DateTimeField()  # When the task should be executed
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
    task_data = models.JSONField(default=dict)  # Additional task-specific data
    executed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["scheduled_time"]
        indexes = [
            models.Index(fields=["user_id", "status", "scheduled_time"]),
            models.Index(fields=["scheduled_time", "status"]),
            models.Index(fields=["calendar_event_id"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.task_type} for {self.user_id} at {self.scheduled_time}"


