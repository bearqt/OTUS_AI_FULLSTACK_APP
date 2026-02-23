import django_filters
from django.db.models import Q

from .models import Card


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
  pass


class CardFilterSet(django_filters.FilterSet):
  board = django_filters.NumberFilter(method="filter_board")
  labels = NumberInFilter(method="filter_labels")
  assignee = django_filters.NumberFilter(field_name="assignee_id")
  has_deadline = django_filters.BooleanFilter(method="filter_has_deadline")
  priority = django_filters.ChoiceFilter(choices=Card.Priority.choices)
  column = django_filters.NumberFilter(field_name="column_id")

  class Meta:
    model = Card
    fields = ["board", "labels", "assignee", "has_deadline", "priority", "column"]

  def filter_board(self, queryset, name, value):
    return queryset.filter(column__board_id=value)

  def filter_labels(self, queryset, name, value):
    if not value:
      return queryset
    for label_id in value:
      queryset = queryset.filter(labels__id=label_id)
    return queryset.distinct()

  def filter_has_deadline(self, queryset, name, value):
    return queryset.filter(~Q(due_at=None)) if value else queryset.filter(due_at=None)
