from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.kanban.models import Board, BoardColumn, BoardMembership, Card, CardComment, Label
from apps.kanban.services import place_card, place_column


User = get_user_model()


class Command(BaseCommand):
  help = "Create seed data for MiniTrello (2 users, 2 boards, 4 columns, 20 cards, 10 comments)."

  @transaction.atomic
  def handle(self, *args, **options):
    self.stdout.write("Seeding MiniTrello data...")

    user1, _ = User.objects.get_or_create(
      username="alex",
      defaults={"email": "alex@example.com", "full_name": "Alex Demo"},
    )
    if not user1.has_usable_password():
      user1.set_password("password123")
      user1.save(update_fields=["password"])
    elif not user1.check_password("password123"):
      user1.set_password("password123")
      user1.save(update_fields=["password"])

    user2, _ = User.objects.get_or_create(
      username="maria",
      defaults={"email": "maria@example.com", "full_name": "Maria Demo"},
    )
    if not user2.has_usable_password():
      user2.set_password("password123")
      user2.save(update_fields=["password"])
    elif not user2.check_password("password123"):
      user2.set_password("password123")
      user2.save(update_fields=["password"])

    board_specs = [
      ("Course Board", "Training project board", user1),
      ("Team Board", "Shared planning board", user2),
    ]
    boards = []
    for title, description, creator in board_specs:
      board, created = Board.objects.get_or_create(
        title=title,
        defaults={"description": description, "created_by": creator},
      )
      if created:
        boards.append(board)
      else:
        boards.append(board)
        if board.created_by_id != creator.id or board.description != description:
          board.created_by = creator
          board.description = description
          board.save(update_fields=["created_by", "description", "updated_at"])

    for board in boards:
      BoardMembership.objects.get_or_create(board=board, user=user1, defaults={"role": BoardMembership.Role.OWNER if board.created_by_id == user1.id else BoardMembership.Role.MEMBER})
      BoardMembership.objects.get_or_create(board=board, user=user2, defaults={"role": BoardMembership.Role.OWNER if board.created_by_id == user2.id else BoardMembership.Role.MEMBER})

    columns_by_board = {
      boards[0]: ["To Do", "In Progress"],
      boards[1]: ["Done", "Ideas"],
    }

    all_columns = []
    for board, titles in columns_by_board.items():
      for idx, title in enumerate(titles):
        column, _ = BoardColumn.objects.get_or_create(board=board, title=title, defaults={"position": idx})
        if column.position != idx:
          column.position = idx
          column.save(update_fields=["position"])
        place_column(column, idx)
        all_columns.append(column)

    label_palette = [
      ("frontend", "#0EA5E9"),
      ("backend", "#F97316"),
      ("bug", "#EF4444"),
      ("docs", "#10B981"),
    ]
    board_labels = {}
    for board in boards:
      labels = []
      palette_slice = label_palette[:2] if board == boards[0] else label_palette[2:]
      for name, color in palette_slice:
        label, _ = Label.objects.get_or_create(board=board, name=name, defaults={"color": color})
        if label.color != color:
          label.color = color
          label.save(update_fields=["color"])
        labels.append(label)
      board_labels[board.id] = labels

    # Create exactly 20 cards across 4 columns (5 per column) when missing.
    existing_cards = Card.objects.count()
    if existing_cards < 20:
      to_create = 20 - existing_cards
      now = timezone.now()
      for i in range(to_create):
        column = all_columns[i % len(all_columns)]
        assignee = user1 if i % 2 == 0 else user2
        card = Card.objects.create(
          column=column,
          title=f"Seed task {Card.objects.count() + 1}",
          description_markdown=f"Seed description for task {i + 1}\n\n- Markdown supported",
          priority=[Card.Priority.LOW, Card.Priority.MEDIUM, Card.Priority.HIGH, Card.Priority.URGENT][i % 4],
          due_at=now + timedelta(days=(i % 7) + 1) if i % 3 != 0 else None,
          assignee=assignee,
          created_by=column.board.created_by,
          position=0,
        )
        place_card(card, target_column=column, target_position=column.cards.exclude(pk=card.pk).count())
        labels = board_labels[column.board_id]
        if labels:
          card.labels.add(labels[i % len(labels)])

    # Create exactly 10 comments when missing (on first 10 cards)
    cards = list(Card.objects.order_by("id")[:10])
    existing_comments = CardComment.objects.count()
    if existing_comments < 10:
      for i in range(10 - existing_comments):
        card = cards[i % len(cards)]
        author = user1 if i % 2 == 0 else user2
        CardComment.objects.create(card=card, author=author, body=f"Seed comment {CardComment.objects.count() + 1}")

    self.stdout.write(
      self.style.SUCCESS(
        f"Seed completed: users={User.objects.count()} boards={Board.objects.count()} columns={BoardColumn.objects.count()} cards={Card.objects.count()} comments={CardComment.objects.count()}"
      )
    )
