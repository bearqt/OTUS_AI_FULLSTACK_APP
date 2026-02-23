import * as Dialog from "@radix-ui/react-dialog";
import * as Select from "@radix-ui/react-select";
import * as Tabs from "@radix-ui/react-tabs";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, useParams } from "react-router-dom";

import { endpoints } from "../lib/api";
import { useAuth } from "../lib/auth";

const priorities = ["low", "medium", "high", "urgent"];

function formatDateTime(value) {
  if (!value) return "No deadline";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Invalid date" : date.toLocaleString();
}

function toDateTimeLocal(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  const yyyy = d.getFullYear();
  const mm = pad(d.getMonth() + 1);
  const dd = pad(d.getDate());
  const hh = pad(d.getHours());
  const min = pad(d.getMinutes());
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
}

function fromDateTimeLocal(value) {
  return value ? new Date(value).toISOString() : null;
}

function initials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function SelectField({ value, onValueChange, placeholder, options }) {
  const EMPTY_SENTINEL = "__empty__";
  const normalizedValue = value === "" || value == null ? EMPTY_SENTINEL : String(value);
  return (
    <Select.Root
      value={normalizedValue}
      onValueChange={(next) => onValueChange(next === EMPTY_SENTINEL ? "" : next)}
    >
      <Select.Trigger className="select-trigger" aria-label={placeholder}>
        <Select.Value placeholder={placeholder} />
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="select-content" position="popper">
          <Select.Viewport>
            {options.map((option) => (
              <Select.Item
                key={String(option.value || EMPTY_SENTINEL)}
                value={option.value === "" ? EMPTY_SENTINEL : String(option.value)}
                className="select-item"
              >
                <Select.ItemText>{option.label}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

function CardDialog({
  open,
  onOpenChange,
  board,
  selectedCard,
  selectedCardComments,
  onSave,
  onDelete,
  onReloadComments,
  onAddComment,
}) {
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [commentBody, setCommentBody] = useState("");

  useEffect(() => {
    if (!selectedCard) {
      setForm(null);
      setErrors({});
      return;
    }
    setForm({
      id: selectedCard.id || null,
      column: selectedCard.column ? String(selectedCard.column) : String(board?.columns?.[0]?.id ?? ""),
      title: selectedCard.title || "",
      description_markdown: selectedCard.description_markdown || "",
      priority: selectedCard.priority || "medium",
      due_at: toDateTimeLocal(selectedCard.due_at),
      assignee_id: selectedCard.assignee?.id ? String(selectedCard.assignee.id) : "",
      label_ids: (selectedCard.labels || []).map((l) => l.id),
    });
    setCommentBody("");
    setErrors({});
  }, [selectedCard, board]);

  if (!board || !form) return null;

  const assigneeOptions = [{ value: "", label: "Unassigned" }].concat(
    (board.members || []).map((m) => ({
      value: m.user.id,
      label: m.user.display_name || m.user.username,
    })),
  );

  const columnOptions = (board.columns || []).map((c) => ({ value: c.id, label: c.title }));

  function validate() {
    const next = {};
    if (!form.title.trim()) next.title = "Title is required";
    if (!form.column) next.column = "Column is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(event) {
    event.preventDefault();
    if (!validate()) return;
    await onSave({
      id: form.id,
      column: Number(form.column),
      title: form.title.trim(),
      description_markdown: form.description_markdown,
      priority: form.priority,
      due_at: form.due_at ? fromDateTimeLocal(form.due_at) : null,
      assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
      label_ids: form.label_ids,
    });
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-header">
            <Dialog.Title>{form.id ? "Edit card" : "Create card"}</Dialog.Title>
            <Dialog.Description className="sr-only">
              {form.id
                ? "Edit card details, labels, assignee, deadline and comments."
                : "Create a new card and fill in task details."}
            </Dialog.Description>
            <Dialog.Close className="icon-btn" aria-label="Close">
              ×
            </Dialog.Close>
          </div>

          <Tabs.Root defaultValue="details" className="tabs-root">
            <Tabs.List className="tabs-list">
              <Tabs.Trigger value="details" className="tabs-trigger">
                Details
              </Tabs.Trigger>
              <Tabs.Trigger value="comments" className="tabs-trigger">
                Comments
              </Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content value="details" className="tabs-content">
              <form className="grid-form" onSubmit={submit}>
                <label>
                  Title
                  <input value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))} />
                  {errors.title ? <span className="field-error">{errors.title}</span> : null}
                </label>

                <div className="two-col">
                  <label>
                    Column
                    <SelectField
                      value={form.column}
                      onValueChange={(value) => setForm((p) => ({ ...p, column: value }))}
                      placeholder="Select column"
                      options={columnOptions}
                    />
                    {errors.column ? <span className="field-error">{errors.column}</span> : null}
                  </label>
                  <label>
                    Priority
                    <SelectField
                      value={form.priority}
                      onValueChange={(value) => setForm((p) => ({ ...p, priority: value }))}
                      placeholder="Priority"
                      options={priorities.map((p) => ({ value: p, label: p }))}
                    />
                  </label>
                </div>

                <div className="two-col">
                  <label>
                    Assignee
                    <SelectField
                      value={form.assignee_id}
                      onValueChange={(value) => setForm((p) => ({ ...p, assignee_id: value }))}
                      placeholder="Assignee"
                      options={assigneeOptions}
                    />
                  </label>
                  <label>
                    Deadline
                    <input
                      type="datetime-local"
                      value={form.due_at}
                      onChange={(e) => setForm((p) => ({ ...p, due_at: e.target.value }))}
                    />
                  </label>
                </div>

                <label>
                  Description (Markdown)
                  <textarea
                    rows={6}
                    value={form.description_markdown}
                    onChange={(e) => setForm((p) => ({ ...p, description_markdown: e.target.value }))}
                    placeholder="Use markdown for task details"
                  />
                </label>

                <fieldset className="labels-fieldset">
                  <legend>Labels</legend>
                  <div className="chips-wrap">
                    {board.labels.map((label) => {
                      const active = form.label_ids.includes(label.id);
                      return (
                        <button
                          type="button"
                          key={label.id}
                          className={`chip chip-label ${active ? "chip-active" : ""}`}
                          style={{ "--chip-color": label.color }}
                          onClick={() =>
                            setForm((p) => ({
                              ...p,
                              label_ids: active ? p.label_ids.filter((id) => id !== label.id) : [...p.label_ids, label.id],
                            }))
                          }
                        >
                          {label.name}
                        </button>
                      );
                    })}
                  </div>
                </fieldset>

                <div className="markdown-preview">
                  <p className="eyebrow">Preview</p>
                  <ReactMarkdown>{form.description_markdown || "_No description_"}</ReactMarkdown>
                </div>

                <div className="dialog-actions">
                  {form.id ? (
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() => onDelete(form.id)}
                    >
                      Delete
                    </button>
                  ) : (
                    <span />
                  )}
                  <button className="btn btn-primary" type="submit">
                    {form.id ? "Save changes" : "Create card"}
                  </button>
                </div>
              </form>
            </Tabs.Content>

            <Tabs.Content value="comments" className="tabs-content">
              {!form.id ? (
                <p className="muted">Create the card first, then add comments.</p>
              ) : (
                <>
                  <div className="comment-form">
                    <textarea
                      rows={3}
                      value={commentBody}
                      onChange={(e) => setCommentBody(e.target.value)}
                      placeholder="Add comment"
                    />
                    <div className="comment-form-actions">
                      <button className="btn" type="button" onClick={() => onReloadComments(form.id)}>
                        Refresh
                      </button>
                      <button
                        className="btn btn-primary"
                        type="button"
                        disabled={!commentBody.trim()}
                        onClick={async () => {
                          await onAddComment(form.id, commentBody.trim());
                          setCommentBody("");
                        }}
                      >
                        Add Comment
                      </button>
                    </div>
                  </div>
                  <div className="comments-list">
                    {selectedCardComments.length === 0 ? <p className="muted">No comments yet.</p> : null}
                    {selectedCardComments.map((comment) => (
                      <article key={comment.id} className="comment-item">
                        <div className="avatar">{initials(comment.author?.display_name || comment.author?.username)}</div>
                        <div>
                          <div className="comment-meta">
                            <strong>{comment.author?.display_name || comment.author?.username}</strong>
                            <span>{formatDateTime(comment.created_at)}</span>
                          </div>
                          <p>{comment.body}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              )}
            </Tabs.Content>
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default function BoardPage() {
  const { boardId } = useParams();
  const auth = useAuth();
  const [board, setBoard] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    priority: "",
    labelId: "",
    assigneeId: "",
    hasDeadline: "all",
    search: "",
  });
  const deferredSearch = useDeferredValue(filters.search);
  const [columnForm, setColumnForm] = useState("");
  const [labelForm, setLabelForm] = useState({ name: "", color: "#0EA5E9" });
  const [dragState, setDragState] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCard, setSelectedCard] = useState(null);
  const [selectedCardComments, setSelectedCardComments] = useState([]);
  const [activeTab, setActiveTab] = useState("board");

  async function loadBoard() {
    setLoading(true);
    setError("");
    try {
      const [boardData, activityData] = await Promise.all([
        auth.authFetch(endpoints.boardDetail(boardId)),
        auth.authFetch(endpoints.boardActivity(boardId)),
      ]);
      startTransition(() => {
        setBoard(boardData);
        setActivity(activityData.results || activityData);
      });
    } catch (e) {
      setError(e.message || "Failed to load board");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBoard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardId]);

  const filteredColumns = useMemo(() => {
    if (!board) return [];
    const searchText = deferredSearch.trim().toLowerCase();
    return board.columns.map((column) => ({
      ...column,
      cards: (column.cards || []).filter((card) => {
        if (filters.priority && card.priority !== filters.priority) return false;
        if (filters.labelId && !(card.labels || []).some((l) => String(l.id) === filters.labelId)) return false;
        if (filters.assigneeId && String(card.assignee?.id || "") !== filters.assigneeId) return false;
        if (filters.hasDeadline === "yes" && !card.due_at) return false;
        if (filters.hasDeadline === "no" && card.due_at) return false;
        if (searchText && !`${card.title} ${card.description_markdown || ""}`.toLowerCase().includes(searchText)) return false;
        return true;
      }),
    }));
  }, [board, filters, deferredSearch]);

  const memberOptions = useMemo(() => {
    if (!board) return [];
    return (board.members || []).map((m) => ({
      value: String(m.user.id),
      label: m.user.display_name || m.user.username,
    }));
  }, [board]);

  async function reloadComments(cardId) {
    const data = await auth.authFetch(`${endpoints.comments}?card=${cardId}`);
    setSelectedCardComments(data.results || data);
  }

  async function openNewCardDialog(column) {
    setSelectedCard({
      column: column.id,
      title: "",
      description_markdown: "",
      priority: "medium",
      due_at: null,
      assignee: null,
      labels: [],
    });
    setSelectedCardComments([]);
    setDialogOpen(true);
  }

  async function openExistingCardDialog(cardId) {
    const card = await auth.authFetch(endpoints.card(cardId));
    setSelectedCard(card);
    await reloadComments(cardId);
    setDialogOpen(true);
  }

  async function saveCard(payload) {
    try {
      const { id, ...body } = payload;
      const isEdit = Boolean(id);
      const path = isEdit ? endpoints.card(id) : endpoints.cards;
      const method = isEdit ? "PATCH" : "POST";
      await auth.authFetch(path, { method, body: JSON.stringify(body) });
      setDialogOpen(false);
      await loadBoard();
    } catch (e) {
      alert(e.message || "Failed to save card");
    }
  }

  async function deleteCard(cardId) {
    if (!confirm("Delete this card?")) return;
    await auth.authFetch(endpoints.card(cardId), { method: "DELETE" });
    setDialogOpen(false);
    setSelectedCard(null);
    setSelectedCardComments([]);
    await loadBoard();
  }

  async function addComment(cardId, body) {
    await auth.authFetch(endpoints.comments, {
      method: "POST",
      body: JSON.stringify({ card: cardId, body }),
    });
    await reloadComments(cardId);
    await loadBoard();
  }

  async function createColumn(event) {
    event.preventDefault();
    if (!columnForm.trim() || !board) return;
    await auth.authFetch(endpoints.columns, {
      method: "POST",
      body: JSON.stringify({ board: board.id, title: columnForm.trim() }),
    });
    setColumnForm("");
    await loadBoard();
  }

  async function createLabel(event) {
    event.preventDefault();
    if (!labelForm.name.trim() || !board) return;
    await auth.authFetch(endpoints.labels, {
      method: "POST",
      body: JSON.stringify({ board: board.id, name: labelForm.name.trim(), color: labelForm.color }),
    });
    setLabelForm({ name: "", color: labelForm.color });
    await loadBoard();
  }

  async function onDropCard(targetColumnId, targetPosition) {
    if (!dragState) return;
    const { cardId } = dragState;
    setDragState(null);
    await auth.authFetch(endpoints.moveCard(cardId), {
      method: "POST",
      body: JSON.stringify({
        target_column_id: targetColumnId,
        target_position: targetPosition,
      }),
    });
    await loadBoard();
  }

  if (loading) {
    return <div className="loading-screen">Loading board...</div>;
  }

  if (error || !board) {
    return (
      <div className="page-shell">
        <Link to="/boards" className="btn">
          ← Back to boards
        </Link>
        <div className="panel form-alert">{error || "Board not found"}</div>
      </div>
    );
  }

  const allCardsCount = board.columns.reduce((acc, c) => acc + (c.cards?.length || 0), 0);

  return (
    <div className="page-shell board-page">
      <header className="topbar board-header">
        <div>
          <Link to="/boards" className="back-link">
            ← Boards
          </Link>
          <h1>{board.title}</h1>
          <p className="muted">{board.description || "No description"}</p>
        </div>
        <div className="topbar-actions">
          <button className="btn" onClick={() => loadBoard()}>
            Refresh
          </button>
          <button className="btn" onClick={auth.logout}>
            Logout
          </button>
        </div>
      </header>

      <section className="board-stats panel">
        <span className="chip">Columns: {board.columns.length}</span>
        <span className="chip">Cards: {allCardsCount}</span>
        <span className="chip">Members: {board.members.length}</span>
        <span className="chip">Labels: {board.labels.length}</span>
      </section>

      <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="tabs-root page-tabs">
        <Tabs.List className="tabs-list">
          <Tabs.Trigger value="board" className="tabs-trigger">
            Board
          </Tabs.Trigger>
          <Tabs.Trigger value="activity" className="tabs-trigger">
            Activity Log
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="board" className="tabs-content">
          <section className="board-layout">
            <aside className="board-sidebar">
              <div className="panel">
                <h3>Filters</h3>
                <div className="stack-sm">
                  <label>
                    Search
                    <input
                      value={filters.search}
                      onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                      placeholder="Title / description"
                    />
                  </label>
                  <label>
                    Priority
                    <SelectField
                      value={filters.priority}
                      onValueChange={(v) => setFilters((f) => ({ ...f, priority: v }))}
                      placeholder="Any priority"
                      options={[{ value: "", label: "Any" }, ...priorities.map((p) => ({ value: p, label: p }))]}
                    />
                  </label>
                  <label>
                    Label
                    <SelectField
                      value={filters.labelId}
                      onValueChange={(v) => setFilters((f) => ({ ...f, labelId: v }))}
                      placeholder="Any label"
                      options={[{ value: "", label: "Any" }, ...board.labels.map((l) => ({ value: l.id, label: l.name }))]}
                    />
                  </label>
                  <label>
                    Assignee
                    <SelectField
                      value={filters.assigneeId}
                      onValueChange={(v) => setFilters((f) => ({ ...f, assigneeId: v }))}
                      placeholder="Any assignee"
                      options={[{ value: "", label: "Any" }, ...memberOptions]}
                    />
                  </label>
                  <label>
                    Deadline
                    <select
                      value={filters.hasDeadline}
                      onChange={(e) => setFilters((f) => ({ ...f, hasDeadline: e.target.value }))}
                    >
                      <option value="all">Any</option>
                      <option value="yes">With deadline</option>
                      <option value="no">Without deadline</option>
                    </select>
                  </label>
                  <button
                    className="btn"
                    onClick={() =>
                      setFilters({ priority: "", labelId: "", assigneeId: "", hasDeadline: "all", search: "" })
                    }
                  >
                    Reset filters
                  </button>
                </div>
              </div>

              <div className="panel">
                <h3>Add column</h3>
                <form className="stack-sm" onSubmit={createColumn}>
                  <input
                    value={columnForm}
                    onChange={(e) => setColumnForm(e.target.value)}
                    placeholder="Column name"
                  />
                  <button className="btn btn-primary" disabled={!columnForm.trim()}>
                    Create column
                  </button>
                </form>
              </div>

              <div className="panel">
                <h3>Add label</h3>
                <form className="stack-sm" onSubmit={createLabel}>
                  <input
                    value={labelForm.name}
                    onChange={(e) => setLabelForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="Label name"
                  />
                  <div className="two-col">
                    <input
                      type="color"
                      value={labelForm.color}
                      onChange={(e) => setLabelForm((f) => ({ ...f, color: e.target.value }))}
                    />
                    <button className="btn btn-primary" disabled={!labelForm.name.trim()}>
                      Create
                    </button>
                  </div>
                </form>
              </div>

              <div className="panel">
                <h3>Members</h3>
                <div className="member-list">
                  {board.members.map((m) => (
                    <div key={m.id} className="member-row">
                      <div className="avatar">{initials(m.user.display_name || m.user.username)}</div>
                      <div>
                        <strong>{m.user.display_name || m.user.username}</strong>
                        <p className="muted tiny">{m.role}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </aside>

            <section className="kanban-scroll">
              <div className="kanban-columns">
                {filteredColumns.map((column) => (
                  <section
                    key={column.id}
                    className="column-panel"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      onDropCard(column.id, column.cards.length);
                    }}
                  >
                    <header className="column-header">
                      <div>
                        <h3>{column.title}</h3>
                        <span className="muted tiny">{column.cards.length} visible cards</span>
                      </div>
                      <button className="btn btn-small" onClick={() => openNewCardDialog(column)}>
                        + Card
                      </button>
                    </header>

                    <div className="column-card-list">
                      {column.cards.map((card, index) => (
                        <div key={card.id}>
                          <div
                            className={`drop-slot ${dragState ? "active" : ""}`}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={(e) => {
                              e.preventDefault();
                              onDropCard(column.id, index);
                            }}
                          />
                          <article
                            className="task-card"
                            draggable
                            onDragStart={() => setDragState({ cardId: card.id, fromColumnId: column.id })}
                            onDragEnd={() => setDragState(null)}
                            onDoubleClick={() => openExistingCardDialog(card.id)}
                            onClick={() => openExistingCardDialog(card.id)}
                          >
                            <div className="task-card-top">
                              <span className={`priority-badge priority-${card.priority}`}>{card.priority}</span>
                              {card.assignee ? (
                                <span className="assignee-mini">{initials(card.assignee.display_name || card.assignee.username)}</span>
                              ) : null}
                            </div>
                            <h4>{card.title}</h4>
                            <p className="muted tiny clamp-2">{card.description_markdown || "No description"}</p>
                            <div className="chips-wrap">
                              {(card.labels || []).map((label) => (
                                <span
                                  key={label.id}
                                  className="chip chip-label"
                                  style={{ "--chip-color": label.color }}
                                >
                                  {label.name}
                                </span>
                              ))}
                            </div>
                            <div className="task-card-footer">
                              <span>{formatDateTime(card.due_at)}</span>
                            </div>
                          </article>
                        </div>
                      ))}
                      <div
                        className={`drop-slot drop-slot-end ${dragState ? "active" : ""}`}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => {
                          e.preventDefault();
                          onDropCard(column.id, column.cards.length);
                        }}
                      />
                    </div>
                  </section>
                ))}
              </div>
            </section>
          </section>
        </Tabs.Content>

        <Tabs.Content value="activity" className="tabs-content">
          <section className="panel">
            <h3>Board activity log</h3>
            <div className="activity-list">
              {activity.length === 0 ? <p className="muted">No activity yet.</p> : null}
              {activity.map((item) => (
                <div key={item.id} className="activity-row">
                  <div className="avatar">{initials(item.actor_user?.display_name || item.actor_user?.username)}</div>
                  <div>
                    <strong>{item.actor_user?.display_name || item.actor_user?.username}</strong>{" "}
                    <span>{item.action}</span>
                    <p className="muted tiny">{formatDateTime(item.created_at)}</p>
                    {item.details && Object.keys(item.details).length > 0 ? (
                      <pre className="activity-details">{JSON.stringify(item.details, null, 2)}</pre>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </Tabs.Content>
      </Tabs.Root>

      <CardDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        board={board}
        selectedCard={selectedCard}
        selectedCardComments={selectedCardComments}
        onSave={saveCard}
        onDelete={deleteCard}
        onReloadComments={reloadComments}
        onAddComment={addComment}
      />
    </div>
  );
}
