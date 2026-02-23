from django.contrib import admin

from .models import ActivityLog, Board, BoardColumn, BoardMembership, Card, CardComment, CardLabel, Label


admin.site.register(Board)
admin.site.register(BoardMembership)
admin.site.register(BoardColumn)
admin.site.register(Label)
admin.site.register(Card)
admin.site.register(CardLabel)
admin.site.register(CardComment)
admin.site.register(ActivityLog)
