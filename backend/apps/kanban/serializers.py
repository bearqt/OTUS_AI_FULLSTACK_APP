from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.users.serializers import UserSerializer

from .models import ActivityLog, Board, BoardColumn, BoardMembership, Card, CardComment, Label
from .services import normalize_board_columns, normalize_column_cards, place_card, place_column


User = get_user_model()


class MembershipUserSerializer(UserSerializer):
  class Meta(UserSerializer.Meta):
    fields = ("id", "username", "email", "full_name", "display_name")


class BoardMembershipSerializer(serializers.ModelSerializer):
  user = MembershipUserSerializer(read_only=True)
  user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="user", write_only=True, required=False)

  class Meta:
    model = BoardMembership
    fields = ("id", "board", "user", "user_id", "role", "joined_at")
    read_only_fields = ("id", "joined_at", "board", "user")


class LabelSerializer(serializers.ModelSerializer):
  class Meta:
    model = Label
    fields = ("id", "board", "name", "color", "created_at", "updated_at")
    read_only_fields = ("id", "created_at", "updated_at")

  def validate_name(self, value):
    value = value.strip()
    if not value:
      raise serializers.ValidationError("Label name is required.")
    return value

  def validate_color(self, value):
    value = value.strip()
    if not value:
      raise serializers.ValidationError("Label color is required.")
    return value

  def validate(self, attrs):
    if self.instance is not None and "board" in attrs and attrs["board"].id != self.instance.board_id:
      raise serializers.ValidationError({"board": "Changing board for an existing label is not allowed."})
    return attrs


class CardCompactSerializer(serializers.ModelSerializer):
  assignee = UserSerializer(read_only=True)
  labels = LabelSerializer(many=True, read_only=True)

  class Meta:
    model = Card
    fields = (
      "id",
      "column",
      "title",
      "description_markdown",
      "priority",
      "due_at",
      "assignee",
      "created_by",
      "position",
      "labels",
      "created_at",
      "updated_at",
    )


class BoardColumnSerializer(serializers.ModelSerializer):
  cards = CardCompactSerializer(many=True, read_only=True)

  class Meta:
    model = BoardColumn
    fields = ("id", "board", "title", "position", "cards", "created_at", "updated_at")
    read_only_fields = ("id", "created_at", "updated_at", "cards")

  def validate_title(self, value):
    value = value.strip()
    if not value:
      raise serializers.ValidationError("Column title is required.")
    return value

  def validate(self, attrs):
    if self.instance is not None and "board" in attrs and attrs["board"].id != self.instance.board_id:
      raise serializers.ValidationError({"board": "Changing board for an existing column is not allowed."})
    return attrs

  @transaction.atomic
  def create(self, validated_data):
    requested_position = validated_data.pop("position", None)
    column = BoardColumn.objects.create(position=0, **validated_data)
    target = requested_position if requested_position is not None else column.board.columns.exclude(pk=column.pk).count()
    place_column(column, target)
    return column

  @transaction.atomic
  def update(self, instance, validated_data):
    requested_position = validated_data.pop("position", None)
    for attr, value in validated_data.items():
      setattr(instance, attr, value)
    instance.save()
    if requested_position is not None:
      place_column(instance, requested_position)
    else:
      normalize_board_columns(instance.board)
    return instance


class CardSerializer(serializers.ModelSerializer):
  assignee = UserSerializer(read_only=True)
  assignee_id = serializers.PrimaryKeyRelatedField(
    queryset=User.objects.all(), source="assignee", allow_null=True, required=False, write_only=True
  )
  created_by = UserSerializer(read_only=True)
  labels = LabelSerializer(many=True, read_only=True)
  label_ids = serializers.PrimaryKeyRelatedField(queryset=Label.objects.all(), many=True, write_only=True, required=False)
  board_id = serializers.IntegerField(source="column.board_id", read_only=True)

  class Meta:
    model = Card
    fields = (
      "id",
      "board_id",
      "column",
      "title",
      "description_markdown",
      "priority",
      "due_at",
      "assignee",
      "assignee_id",
      "created_by",
      "position",
      "labels",
      "label_ids",
      "created_at",
      "updated_at",
    )
    read_only_fields = ("id", "created_by", "created_at", "updated_at", "board_id", "labels", "assignee")

  def _target_board(self, attrs):
    column = attrs.get("column") or getattr(self.instance, "column", None)
    if column is None:
      raise serializers.ValidationError({"column": "Column is required."})
    return column.board

  def validate_title(self, value):
    value = value.strip()
    if not value:
      raise serializers.ValidationError("Card title is required.")
    return value

  def validate(self, attrs):
    board = self._target_board(attrs)
    if self.instance is not None and "column" in attrs and attrs["column"].board_id != self.instance.column.board_id:
      raise serializers.ValidationError({"column": "Moving cards across boards is not allowed."})

    assignee = attrs.get("assignee", serializers.empty)
    if assignee is not serializers.empty and assignee is not None:
      exists = BoardMembership.objects.filter(board=board, user=assignee).exists()
      if not exists:
        raise serializers.ValidationError({"assignee_id": "Assignee must be a board member."})

    labels = attrs.get("label_ids", serializers.empty)
    if labels is not serializers.empty:
      invalid_label = next((label for label in labels if label.board_id != board.id), None)
      if invalid_label:
        raise serializers.ValidationError({"label_ids": f"Label {invalid_label.id} does not belong to the selected board."})

    return attrs

  @transaction.atomic
  def create(self, validated_data):
    label_ids = validated_data.pop("label_ids", [])
    requested_position = validated_data.pop("position", None)
    card = Card.objects.create(position=0, **validated_data)
    target_position = requested_position
    if target_position is None:
      target_position = card.column.cards.exclude(pk=card.pk).count()
    place_card(card, target_column=card.column, target_position=target_position)
    if label_ids:
      card.labels.set(label_ids)
    card.refresh_from_db()
    return card

  @transaction.atomic
  def update(self, instance, validated_data):
    label_ids = validated_data.pop("label_ids", serializers.empty)
    requested_position = validated_data.pop("position", None)
    requested_column = validated_data.pop("column", None)

    for attr, value in validated_data.items():
      setattr(instance, attr, value)
    if requested_column is not None:
      instance.column = requested_column
    instance.save()

    if requested_column is not None or requested_position is not None:
      place_card(
        instance,
        target_column=instance.column,
        target_position=requested_position if requested_position is not None else instance.position,
      )
    else:
      normalize_column_cards(instance.column)

    if label_ids is not serializers.empty:
      instance.labels.set(label_ids)
    instance.refresh_from_db()
    return instance


class CardMoveSerializer(serializers.Serializer):
  target_column_id = serializers.PrimaryKeyRelatedField(queryset=BoardColumn.objects.all(), source="target_column")
  target_position = serializers.IntegerField(min_value=0)


class ReorderColumnsSerializer(serializers.Serializer):
  board_id = serializers.PrimaryKeyRelatedField(queryset=Board.objects.all(), source="board")
  ordered_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)


class BoardSerializer(serializers.ModelSerializer):
  created_by = UserSerializer(read_only=True)
  my_role = serializers.SerializerMethodField()
  members_count = serializers.IntegerField(read_only=True)

  class Meta:
    model = Board
    fields = (
      "id",
      "title",
      "description",
      "created_by",
      "my_role",
      "members_count",
      "created_at",
      "updated_at",
    )
    read_only_fields = ("id", "created_by", "my_role", "members_count", "created_at", "updated_at")

  def get_my_role(self, obj):
    request = self.context.get("request")
    if not request or not request.user.is_authenticated:
      return None
    membership = getattr(obj, "_my_membership", None)
    if membership:
      return membership.role
    membership = obj.memberships.filter(user=request.user).first()
    return membership.role if membership else None

  def validate_title(self, value):
    value = value.strip()
    if not value:
      raise serializers.ValidationError("Board title is required.")
    return value


class BoardDetailSerializer(BoardSerializer):
  columns = BoardColumnSerializer(many=True, read_only=True)
  labels = LabelSerializer(many=True, read_only=True)
  members = serializers.SerializerMethodField()

  class Meta(BoardSerializer.Meta):
    fields = BoardSerializer.Meta.fields + ("columns", "labels", "members")

  def get_members(self, obj):
    memberships = obj.memberships.select_related("user").all().order_by("id")
    return BoardMembershipSerializer(memberships, many=True).data


class CardCommentSerializer(serializers.ModelSerializer):
  author = UserSerializer(read_only=True)

  class Meta:
    model = CardComment
    fields = ("id", "card", "author", "body", "created_at", "updated_at")
    read_only_fields = ("id", "author", "created_at", "updated_at")

  def validate_body(self, value):
    value = value.strip()
    if not value:
      raise serializers.ValidationError("Comment body is required.")
    return value

  def validate_card(self, value):
    request = self.context.get("request")
    if request and request.user.is_authenticated:
      is_member = BoardMembership.objects.filter(board=value.column.board, user=request.user).exists()
      if not is_member:
        raise serializers.ValidationError("You are not a member of this board.")
    return value


class ActivityLogSerializer(serializers.ModelSerializer):
  actor_user = UserSerializer(read_only=True)

  class Meta:
    model = ActivityLog
    fields = (
      "id",
      "board",
      "actor_user",
      "action",
      "card",
      "column",
      "comment",
      "details",
      "created_at",
    )
    read_only_fields = fields
