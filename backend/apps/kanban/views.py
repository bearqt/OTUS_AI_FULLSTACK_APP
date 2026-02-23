from django.db.models import Count, Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .filters import CardFilterSet
from .models import ActivityLog, Board, BoardColumn, BoardMembership, Card, CardComment, Label
from .serializers import (
  ActivityLogSerializer,
  BoardColumnSerializer,
  BoardDetailSerializer,
  BoardMembershipSerializer,
  BoardSerializer,
  CardCommentSerializer,
  CardMoveSerializer,
  CardSerializer,
  LabelSerializer,
  ReorderColumnsSerializer,
)
from .services import log_activity, normalize_board_columns, normalize_column_cards, place_card, place_column


def _ensure_board_member(board: Board, user):
  if not BoardMembership.objects.filter(board=board, user=user).exists():
    raise PermissionDenied("You are not a member of this board.")


def _board_for_card(card: Card):
  return card.column.board


@extend_schema_view(
  list=extend_schema(tags=["Boards"]),
  retrieve=extend_schema(tags=["Boards"]),
  create=extend_schema(tags=["Boards"]),
  update=extend_schema(tags=["Boards"]),
  partial_update=extend_schema(tags=["Boards"]),
  destroy=extend_schema(tags=["Boards"]),
)
class BoardViewSet(viewsets.ModelViewSet):
  permission_classes = [permissions.IsAuthenticated]
  search_fields = ["title", "description"]
  ordering_fields = ["created_at", "updated_at", "title"]

  def get_queryset(self):
    member_board_ids = BoardMembership.objects.filter(user=self.request.user).values("board_id")
    qs = (
      Board.objects.filter(id__in=member_board_ids)
      .select_related("created_by")
      .prefetch_related(
        Prefetch("columns", queryset=BoardColumn.objects.order_by("position", "id").prefetch_related("cards__labels", "cards__assignee", "cards__created_by")),
        "labels",
        "memberships__user",
      )
      .annotate(members_count=Count("memberships", distinct=True))
      .distinct()
      .order_by("id")
    )
    return qs

  def get_serializer_class(self):
    if self.action == "retrieve":
      return BoardDetailSerializer
    return BoardSerializer

  def perform_create(self, serializer):
    board = serializer.save(created_by=self.request.user)
    BoardMembership.objects.create(board=board, user=self.request.user, role=BoardMembership.Role.OWNER)
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.BOARD_CREATED, details={"title": board.title})

  def perform_update(self, serializer):
    board = serializer.save()
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.BOARD_UPDATED, details={"title": board.title})

  def perform_destroy(self, instance):
    # Board-level activity logs are removed with the board, so persist delete metadata elsewhere if needed.
    instance.delete()

  @extend_schema(tags=["Boards"], request=BoardMembershipSerializer, responses={200: BoardMembershipSerializer(many=True)})
  @action(detail=True, methods=["get", "post"], url_path="members")
  def members(self, request, pk=None):
    board = self.get_object()
    if request.method.lower() == "get":
      memberships = board.memberships.select_related("user").all().order_by("id")
      return Response(BoardMembershipSerializer(memberships, many=True).data)

    serializer = BoardMembershipSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    role = serializer.validated_data["role"]
    membership, created = BoardMembership.objects.get_or_create(
      board=board, user=user, defaults={"role": role}
    )
    if not created:
      membership.role = role
      membership.save(update_fields=["role"])
    log_activity(
      board=board,
      actor=request.user,
      action=ActivityLog.Action.MEMBER_ADDED,
      details={"user_id": user.id, "role": membership.role},
    )
    memberships = board.memberships.select_related("user").all().order_by("id")
    return Response(BoardMembershipSerializer(memberships, many=True).data)

  @extend_schema(tags=["Boards"], request=None, responses={200: None})
  @action(detail=True, methods=["post"], url_path="members/remove")
  def remove_member(self, request, pk=None):
    board = self.get_object()
    user_id = request.data.get("user_id")
    if not user_id:
      raise ValidationError({"user_id": "user_id is required"})
    membership = board.memberships.filter(user_id=user_id).first()
    if not membership:
      raise ValidationError({"user_id": "Membership not found"})
    if membership.role == BoardMembership.Role.OWNER and board.memberships.filter(role=BoardMembership.Role.OWNER).count() <= 1:
      raise ValidationError({"user_id": "Cannot remove the last board owner."})
    membership.delete()
    log_activity(board=board, actor=request.user, action=ActivityLog.Action.MEMBER_REMOVED, details={"user_id": int(user_id)})
    return Response(status=status.HTTP_204_NO_CONTENT)

  @extend_schema(tags=["Boards"], responses={200: ActivityLogSerializer(many=True)})
  @action(detail=True, methods=["get"], url_path="activity")
  def activity(self, request, pk=None):
    board = self.get_object()
    queryset = board.activity_logs.select_related("actor_user").all().order_by("-created_at", "-id")
    page = self.paginate_queryset(queryset)
    serializer = ActivityLogSerializer(page or queryset, many=True)
    if page is not None:
      return self.get_paginated_response(serializer.data)
    return Response(serializer.data)


@extend_schema_view(
  list=extend_schema(tags=["Columns"]),
  retrieve=extend_schema(tags=["Columns"]),
  create=extend_schema(tags=["Columns"]),
  update=extend_schema(tags=["Columns"]),
  partial_update=extend_schema(tags=["Columns"]),
  destroy=extend_schema(tags=["Columns"]),
)
class BoardColumnViewSet(viewsets.ModelViewSet):
  serializer_class = BoardColumnSerializer
  permission_classes = [permissions.IsAuthenticated]
  ordering_fields = ["position", "created_at", "updated_at"]

  def get_queryset(self):
    queryset = BoardColumn.objects.filter(board__memberships__user=self.request.user).select_related("board").distinct()
    board_id = self.request.query_params.get("board")
    if board_id:
      queryset = queryset.filter(board_id=board_id)
    return queryset.order_by("position", "id")

  def perform_create(self, serializer):
    board = serializer.validated_data["board"]
    _ensure_board_member(board, self.request.user)
    column = serializer.save()
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.COLUMN_CREATED, column=column, details={"title": column.title})

  def perform_update(self, serializer):
    column = serializer.save()
    log_activity(
      board=column.board,
      actor=self.request.user,
      action=ActivityLog.Action.COLUMN_UPDATED,
      column=column,
      details={"title": column.title, "position": column.position},
    )

  def perform_destroy(self, instance):
    board = instance.board
    title = instance.title
    instance.delete()
    normalize_board_columns(board)
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.COLUMN_DELETED, details={"title": title})

  @extend_schema(tags=["Columns"], request=ReorderColumnsSerializer, responses={200: BoardColumnSerializer(many=True)})
  @action(detail=False, methods=["post"], url_path="reorder")
  def reorder(self, request):
    serializer = ReorderColumnsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    board = serializer.validated_data["board"]
    ordered_ids = serializer.validated_data["ordered_ids"]
    _ensure_board_member(board, request.user)

    columns = list(board.columns.all())
    current_ids = {col.id for col in columns}
    if set(ordered_ids) != current_ids:
      raise ValidationError({"ordered_ids": "ordered_ids must contain all and only board column IDs."})
    mapping = {col.id: col for col in columns}
    reordered = [mapping[col_id] for col_id in ordered_ids]
    for idx, col in enumerate(reordered):
      col.position = idx
    BoardColumn.objects.bulk_update(reordered, ["position"])
    log_activity(board=board, actor=request.user, action=ActivityLog.Action.COLUMN_REORDERED, details={"ordered_ids": ordered_ids})
    return Response(BoardColumnSerializer(reordered, many=True).data)


@extend_schema_view(
  list=extend_schema(tags=["Labels"]),
  retrieve=extend_schema(tags=["Labels"]),
  create=extend_schema(tags=["Labels"]),
  update=extend_schema(tags=["Labels"]),
  partial_update=extend_schema(tags=["Labels"]),
  destroy=extend_schema(tags=["Labels"]),
)
class LabelViewSet(viewsets.ModelViewSet):
  serializer_class = LabelSerializer
  permission_classes = [permissions.IsAuthenticated]
  search_fields = ["name"]
  ordering_fields = ["created_at", "updated_at", "name"]

  def get_queryset(self):
    queryset = Label.objects.filter(board__memberships__user=self.request.user).select_related("board").distinct()
    board_id = self.request.query_params.get("board")
    if board_id:
      queryset = queryset.filter(board_id=board_id)
    return queryset

  def perform_create(self, serializer):
    board = serializer.validated_data["board"]
    _ensure_board_member(board, self.request.user)
    label = serializer.save()
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.LABEL_CREATED, details={"label_id": label.id, "name": label.name})

  def perform_update(self, serializer):
    label = serializer.save()
    log_activity(board=label.board, actor=self.request.user, action=ActivityLog.Action.LABEL_UPDATED, details={"label_id": label.id, "name": label.name})

  def perform_destroy(self, instance):
    board = instance.board
    label_id = instance.id
    name = instance.name
    instance.delete()
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.LABEL_DELETED, details={"label_id": label_id, "name": name})


@extend_schema_view(
  list=extend_schema(tags=["Cards"]),
  retrieve=extend_schema(tags=["Cards"]),
  create=extend_schema(tags=["Cards"]),
  update=extend_schema(tags=["Cards"]),
  partial_update=extend_schema(tags=["Cards"]),
  destroy=extend_schema(tags=["Cards"]),
)
class CardViewSet(viewsets.ModelViewSet):
  serializer_class = CardSerializer
  permission_classes = [permissions.IsAuthenticated]
  filterset_class = CardFilterSet
  search_fields = ["title", "description_markdown"]
  ordering_fields = ["created_at", "updated_at", "due_at", "position", "priority", "title"]

  def get_queryset(self):
    return (
      Card.objects.filter(column__board__memberships__user=self.request.user)
      .select_related("column", "column__board", "assignee", "created_by")
      .prefetch_related("labels")
      .distinct()
      .order_by("position", "id")
    )

  def perform_create(self, serializer):
    card = serializer.save(created_by=self.request.user)
    log_activity(
      board=card.board,
      actor=self.request.user,
      action=ActivityLog.Action.CARD_CREATED,
      card=card,
      column=card.column,
      details={"title": card.title, "position": card.position},
    )

  def perform_update(self, serializer):
    instance = serializer.instance
    old_column_id = instance.column_id
    old_position = instance.position
    old_assignee_id = instance.assignee_id
    old_label_ids = set(instance.labels.values_list("id", flat=True))

    card = serializer.save()
    new_label_ids = set(card.labels.values_list("id", flat=True))

    log_activity(
      board=card.board,
      actor=self.request.user,
      action=ActivityLog.Action.CARD_UPDATED,
      card=card,
      column=card.column,
      details={"title": card.title},
    )

    if card.column_id != old_column_id or card.position != old_position:
      log_activity(
        board=card.board,
        actor=self.request.user,
        action=ActivityLog.Action.CARD_MOVED,
        card=card,
        column=card.column,
        details={
          "old_column_id": old_column_id,
          "new_column_id": card.column_id,
          "old_position": old_position,
          "new_position": card.position,
        },
      )

    if old_assignee_id != card.assignee_id:
      log_activity(
        board=card.board,
        actor=self.request.user,
        action=ActivityLog.Action.ASSIGNEE_CHANGED,
        card=card,
        column=card.column,
        details={"old_assignee_id": old_assignee_id, "new_assignee_id": card.assignee_id},
      )

    added_labels = sorted(new_label_ids - old_label_ids)
    removed_labels = sorted(old_label_ids - new_label_ids)
    for label_id in added_labels:
      log_activity(board=card.board, actor=self.request.user, action=ActivityLog.Action.LABEL_ATTACHED, card=card, column=card.column, details={"label_id": label_id})
    for label_id in removed_labels:
      log_activity(board=card.board, actor=self.request.user, action=ActivityLog.Action.LABEL_DETACHED, card=card, column=card.column, details={"label_id": label_id})

  def perform_destroy(self, instance):
    board = instance.board
    details = {"card_id": instance.id, "title": instance.title, "column_id": instance.column_id}
    instance.delete()
    normalize_column_cards(BoardColumn.objects.get(pk=details["column_id"]))
    log_activity(board=board, actor=self.request.user, action=ActivityLog.Action.CARD_DELETED, details=details)

  @extend_schema(tags=["Cards"], request=CardMoveSerializer, responses={200: CardSerializer})
  @action(detail=True, methods=["post"], url_path="move")
  def move(self, request, pk=None):
    card = self.get_object()
    serializer = CardMoveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target_column = serializer.validated_data["target_column"]
    _ensure_board_member(target_column.board, request.user)
    if target_column.board_id != card.board.id:
      raise ValidationError({"target_column_id": "Target column must belong to the same board."})
    result = place_card(card, target_column=target_column, target_position=serializer.validated_data["target_position"])
    card.refresh_from_db()
    log_activity(
      board=card.board,
      actor=request.user,
      action=ActivityLog.Action.CARD_MOVED,
      card=card,
      column=card.column,
      details=result.__dict__,
    )
    return Response(CardSerializer(card, context=self.get_serializer_context()).data)


@extend_schema_view(
  list=extend_schema(tags=["Comments"]),
  retrieve=extend_schema(tags=["Comments"]),
  create=extend_schema(tags=["Comments"]),
  update=extend_schema(tags=["Comments"]),
  partial_update=extend_schema(tags=["Comments"]),
  destroy=extend_schema(tags=["Comments"]),
)
class CardCommentViewSet(viewsets.ModelViewSet):
  serializer_class = CardCommentSerializer
  permission_classes = [permissions.IsAuthenticated]
  ordering_fields = ["created_at", "updated_at"]

  def get_queryset(self):
    queryset = CardComment.objects.filter(card__column__board__memberships__user=self.request.user).select_related(
      "card", "card__column", "author"
    )
    card_id = self.request.query_params.get("card")
    if card_id:
      queryset = queryset.filter(card_id=card_id)
    return queryset.distinct().order_by("created_at", "id")

  def perform_create(self, serializer):
    comment = serializer.save(author=self.request.user)
    log_activity(
      board=comment.card.column.board,
      actor=self.request.user,
      action=ActivityLog.Action.COMMENT_CREATED,
      card=comment.card,
      column=comment.card.column,
      comment=comment,
      details={"comment_id": comment.id},
    )

  def perform_update(self, serializer):
    if serializer.instance.author_id != self.request.user.id:
      raise PermissionDenied("Only the comment author can edit the comment.")
    comment = serializer.save()
    log_activity(
      board=comment.card.column.board,
      actor=self.request.user,
      action=ActivityLog.Action.COMMENT_UPDATED,
      card=comment.card,
      column=comment.card.column,
      comment=comment,
      details={"comment_id": comment.id},
    )

  def perform_destroy(self, instance):
    if instance.author_id != self.request.user.id:
      raise PermissionDenied("Only the comment author can delete the comment.")
    board = instance.card.column.board
    card = instance.card
    column = instance.card.column
    comment_id = instance.id
    instance.delete()
    log_activity(
      board=board,
      actor=self.request.user,
      action=ActivityLog.Action.COMMENT_DELETED,
      card=card,
      column=column,
      details={"comment_id": comment_id},
    )


@extend_schema_view(
  list=extend_schema(tags=["Activity Logs"]),
  retrieve=extend_schema(tags=["Activity Logs"]),
)
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
  serializer_class = ActivityLogSerializer
  permission_classes = [permissions.IsAuthenticated]
  ordering_fields = ["created_at"]

  def get_queryset(self):
    queryset = ActivityLog.objects.filter(board__memberships__user=self.request.user).select_related("actor_user", "board").distinct()
    board_id = self.request.query_params.get("board")
    if board_id:
      queryset = queryset.filter(board_id=board_id)
    return queryset.order_by("-created_at", "-id")


router = DefaultRouter()
router.register("boards", BoardViewSet, basename="board")
router.register("columns", BoardColumnViewSet, basename="column")
router.register("labels", LabelViewSet, basename="label")
router.register("cards", CardViewSet, basename="card")
router.register("comments", CardCommentViewSet, basename="comment")
router.register("activity-logs", ActivityLogViewSet, basename="activity-log")
