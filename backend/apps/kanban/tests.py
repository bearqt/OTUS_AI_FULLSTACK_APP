from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ActivityLog, Board, BoardColumn, BoardMembership, Card, CardComment, Label


User = get_user_model()


class KanbanApiTests(APITestCase):
  def setUp(self):
    self.user1 = User.objects.create_user(username="u1", email="u1@example.com", password="password123")
    self.user2 = User.objects.create_user(username="u2", email="u2@example.com", password="password123")
    self.user3 = User.objects.create_user(username="u3", email="u3@example.com", password="password123")

    self.board = Board.objects.create(title="Board A", description="", created_by=self.user1)
    self.other_board = Board.objects.create(title="Board B", description="", created_by=self.user2)
    BoardMembership.objects.create(board=self.board, user=self.user1, role=BoardMembership.Role.OWNER)
    BoardMembership.objects.create(board=self.board, user=self.user2, role=BoardMembership.Role.MEMBER)
    BoardMembership.objects.create(board=self.other_board, user=self.user2, role=BoardMembership.Role.OWNER)

    self.col1 = BoardColumn.objects.create(board=self.board, title="To Do", position=0)
    self.col2 = BoardColumn.objects.create(board=self.board, title="Done", position=1)
    self.other_col = BoardColumn.objects.create(board=self.other_board, title="X", position=0)

    self.label1 = Label.objects.create(board=self.board, name="bug", color="#f00")
    self.label2 = Label.objects.create(board=self.board, name="docs", color="#0f0")
    self.foreign_label = Label.objects.create(board=self.other_board, name="ops", color="#00f")

    self.card1 = Card.objects.create(column=self.col1, title="Task 1", created_by=self.user1, position=0, priority=Card.Priority.HIGH)
    self.card1.labels.add(self.label1)
    self.card2 = Card.objects.create(column=self.col1, title="Task 2", created_by=self.user1, position=1, due_at=None, priority=Card.Priority.LOW)
    self.card3 = Card.objects.create(column=self.col2, title="Task 3", created_by=self.user1, position=0, assignee=self.user2, priority=Card.Priority.MEDIUM)

    login = self.client.post(reverse("auth-login"), {"username": "u1", "password": "password123"}, format="json")
    self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

  def test_board_list_returns_only_member_boards(self):
    response = self.client.get(reverse("board-list"))
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    items = response.data["results"]
    ids = {item["id"] for item in items}
    self.assertIn(self.board.id, ids)
    self.assertNotIn(self.other_board.id, ids)
    board_item = next(item for item in items if item["id"] == self.board.id)
    self.assertEqual(board_item["members_count"], 2)

  def test_create_card_rejects_assignee_not_board_member(self):
    payload = {
      "column": self.col1.id,
      "title": "Task invalid assignee",
      "priority": "medium",
      "assignee_id": self.user3.id,
    }
    response = self.client.post(reverse("card-list"), payload, format="json")
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("assignee_id", response.data)

  def test_create_card_rejects_foreign_label(self):
    payload = {
      "column": self.col1.id,
      "title": "Task invalid label",
      "priority": "medium",
      "label_ids": [self.foreign_label.id],
    }
    response = self.client.post(reverse("card-list"), payload, format="json")
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("label_ids", response.data)

  def test_card_filter_by_priority(self):
    response = self.client.get(reverse("card-list"), {"board": self.board.id, "priority": "high"})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    titles = [item["title"] for item in response.data["results"]]
    self.assertEqual(titles, ["Task 1"])

  def test_card_filter_by_label(self):
    response = self.client.get(reverse("card-list"), {"board": self.board.id, "labels": f"{self.label1.id}"})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data["results"]), 1)
    self.assertEqual(response.data["results"][0]["id"], self.card1.id)

  def test_card_filter_by_assignee_and_has_deadline(self):
    self.card3.due_at = None
    self.card3.save(update_fields=["due_at"])
    self.card2.assignee = self.user2
    self.card2.due_at = None
    self.card2.save(update_fields=["assignee", "due_at"])
    self.card1.assignee = self.user2
    self.card1.due_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
    self.card1.save(update_fields=["assignee", "due_at"])
    response = self.client.get(
      reverse("card-list"),
      {"board": self.board.id, "assignee": self.user2.id, "has_deadline": True},
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual([c["id"] for c in response.data["results"]], [self.card1.id])

  def test_move_card_between_columns(self):
    response = self.client.post(
      reverse("card-move", args=[self.card2.id]),
      {"target_column_id": self.col2.id, "target_position": 0},
      format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.card2.refresh_from_db()
    self.assertEqual(self.card2.column_id, self.col2.id)
    self.assertEqual(self.card2.position, 0)
    self.assertTrue(ActivityLog.objects.filter(action=ActivityLog.Action.CARD_MOVED).exists())

  def test_create_comment_logs_activity(self):
    response = self.client.post(reverse("comment-list"), {"card": self.card1.id, "body": "Looks good"}, format="json")
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertTrue(CardComment.objects.filter(card=self.card1).exists())
    self.assertTrue(ActivityLog.objects.filter(action=ActivityLog.Action.COMMENT_CREATED, comment_id=response.data["id"]).exists())

  def test_non_author_cannot_edit_comment(self):
    comment = CardComment.objects.create(card=self.card1, author=self.user2, body="u2 comment")
    response = self.client.patch(reverse("comment-detail", args=[comment.id]), {"body": "edited"}, format="json")
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

  def test_board_members_add_member(self):
    response = self.client.post(
      reverse("board-members", args=[self.board.id]),
      {"user_id": self.user3.id, "role": BoardMembership.Role.MEMBER},
      format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertTrue(BoardMembership.objects.filter(board=self.board, user=self.user3).exists())

  def test_seed_command_creates_required_counts(self):
    call_command("seed_data")
    self.assertEqual(Board.objects.count(), 4)  # 2 existing + 2 seed boards in isolated test DB
    self.assertGreaterEqual(BoardColumn.objects.count(), 4)
    self.assertGreaterEqual(Card.objects.count(), 20)
    self.assertGreaterEqual(CardComment.objects.count(), 10)
