from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    abstract = True


class Board(TimestampedModel):
  title = models.CharField(max_length=255)
  description = models.TextField(blank=True)
  created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_boards")

  class Meta:
    ordering = ["id"]

  def __str__(self):
    return self.title


class BoardMembership(models.Model):
  class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    MEMBER = "member", "Member"

  board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="memberships")
  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="board_memberships")
  role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
  joined_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ["id"]
    constraints = [
      models.UniqueConstraint(fields=["board", "user"], name="uniq_board_user_membership"),
    ]

  def __str__(self):
    return f"{self.user} @ {self.board} ({self.role})"


class BoardColumn(TimestampedModel):
  board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
  title = models.CharField(max_length=120)
  position = models.PositiveIntegerField(default=0)

  class Meta:
    ordering = ["position", "id"]
    indexes = [
      models.Index(fields=["board", "position"]),
    ]

  def __str__(self):
    return f"{self.board.title}: {self.title}"


class Label(TimestampedModel):
  board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="labels")
  name = models.CharField(max_length=64)
  color = models.CharField(max_length=16, default="#64748B")

  class Meta:
    ordering = ["id"]
    constraints = [
      models.UniqueConstraint(fields=["board", "name"], name="uniq_label_name_per_board"),
    ]

  def __str__(self):
    return self.name


class Card(TimestampedModel):
  class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"

  column = models.ForeignKey(BoardColumn, on_delete=models.CASCADE, related_name="cards")
  title = models.CharField(max_length=255)
  description_markdown = models.TextField(blank=True)
  priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
  due_at = models.DateTimeField(null=True, blank=True)
  assignee = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="assigned_cards",
  )
  created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_cards")
  position = models.PositiveIntegerField(default=0)
  labels = models.ManyToManyField("Label", through="CardLabel", related_name="cards", blank=True)

  class Meta:
    ordering = ["position", "id"]
    indexes = [
      models.Index(fields=["column", "position"]),
      models.Index(fields=["priority"]),
      models.Index(fields=["due_at"]),
      models.Index(fields=["assignee"]),
    ]

  @property
  def board(self):
    return self.column.board

  def __str__(self):
    return self.title


class CardLabel(models.Model):
  card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="card_labels")
  label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="label_cards")
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ["id"]
    constraints = [
      models.UniqueConstraint(fields=["card", "label"], name="uniq_card_label"),
    ]


class CardComment(TimestampedModel):
  card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="comments")
  author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="card_comments")
  body = models.TextField()

  class Meta:
    ordering = ["created_at", "id"]
    indexes = [models.Index(fields=["card", "created_at"])]

  def __str__(self):
    return f"Comment #{self.pk} on card {self.card_id}"


class ActivityLog(models.Model):
  class Action(models.TextChoices):
    BOARD_CREATED = "board_created", "Board created"
    BOARD_UPDATED = "board_updated", "Board updated"
    BOARD_DELETED = "board_deleted", "Board deleted"
    MEMBER_ADDED = "member_added", "Member added"
    MEMBER_REMOVED = "member_removed", "Member removed"
    COLUMN_CREATED = "column_created", "Column created"
    COLUMN_UPDATED = "column_updated", "Column updated"
    COLUMN_DELETED = "column_deleted", "Column deleted"
    COLUMN_REORDERED = "column_reordered", "Column reordered"
    CARD_CREATED = "card_created", "Card created"
    CARD_UPDATED = "card_updated", "Card updated"
    CARD_MOVED = "card_moved", "Card moved"
    CARD_DELETED = "card_deleted", "Card deleted"
    ASSIGNEE_CHANGED = "assignee_changed", "Assignee changed"
    LABEL_CREATED = "label_created", "Label created"
    LABEL_UPDATED = "label_updated", "Label updated"
    LABEL_DELETED = "label_deleted", "Label deleted"
    LABEL_ATTACHED = "label_attached", "Label attached"
    LABEL_DETACHED = "label_detached", "Label detached"
    COMMENT_CREATED = "comment_created", "Comment created"
    COMMENT_UPDATED = "comment_updated", "Comment updated"
    COMMENT_DELETED = "comment_deleted", "Comment deleted"

  board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="activity_logs")
  actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="activity_logs")
  action = models.CharField(max_length=32, choices=Action.choices)
  card = models.ForeignKey(Card, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
  column = models.ForeignKey(BoardColumn, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
  comment = models.ForeignKey(CardComment, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
  details = models.JSONField(default=dict, blank=True)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ["-created_at", "-id"]
    indexes = [
      models.Index(fields=["board", "created_at"]),
      models.Index(fields=["actor_user"]),
      models.Index(fields=["action"]),
    ]
