from dataclasses import dataclass

from django.db import transaction

from .models import ActivityLog, Board, BoardColumn, Card


def log_activity(*, board: Board, actor, action: str, card=None, column=None, comment=None, details=None):
  return ActivityLog.objects.create(
    board=board,
    actor_user=actor,
    action=action,
    card=card,
    column=column,
    comment=comment,
    details=details or {},
  )


def _normalize_positions(queryset, *, attr="position"):
  items = list(queryset.order_by(attr, "id"))
  changed = []
  for idx, item in enumerate(items):
    if getattr(item, attr) != idx:
      setattr(item, attr, idx)
      changed.append(item)
  if changed:
    type(changed[0]).objects.bulk_update(changed, [attr])
  return items


def normalize_board_columns(board: Board):
  return _normalize_positions(board.columns.all(), attr="position")


def normalize_column_cards(column: BoardColumn):
  return _normalize_positions(column.cards.all(), attr="position")


@dataclass
class MoveResult:
  old_column_id: int
  new_column_id: int
  old_position: int
  new_position: int


@transaction.atomic
def place_column(column: BoardColumn, target_position: int):
  siblings = list(column.board.columns.exclude(pk=column.pk).order_by("position", "id"))
  target_position = max(0, min(target_position, len(siblings)))
  reordered = []
  inserted = False
  for idx in range(len(siblings) + 1):
    if idx == target_position and not inserted:
      reordered.append(column)
      inserted = True
    if idx < len(siblings):
      reordered.append(siblings[idx])
  for idx, item in enumerate(reordered):
    item.position = idx
  BoardColumn.objects.bulk_update(reordered, ["position"])
  return reordered


@transaction.atomic
def place_card(card: Card, *, target_column: BoardColumn, target_position: int) -> MoveResult:
  old_column_id = card.column_id
  old_position = card.position
  if old_column_id == target_column.id:
    siblings = list(target_column.cards.exclude(pk=card.pk).order_by("position", "id"))
  else:
    siblings = list(target_column.cards.order_by("position", "id"))
  target_position = max(0, min(target_position, len(siblings)))

  reordered_target = []
  inserted = False
  for idx in range(len(siblings) + 1):
    if idx == target_position and not inserted:
      reordered_target.append(card)
      inserted = True
    if idx < len(siblings):
      reordered_target.append(siblings[idx])

  card.column = target_column
  for idx, item in enumerate(reordered_target):
    item.position = idx
  Card.objects.bulk_update(reordered_target, ["column", "position"])

  if old_column_id != target_column.id:
    old_column = BoardColumn.objects.get(pk=old_column_id)
    normalize_column_cards(old_column)

  return MoveResult(
    old_column_id=old_column_id,
    new_column_id=target_column.id,
    old_position=old_position,
    new_position=target_position,
  )
