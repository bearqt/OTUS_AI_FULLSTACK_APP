import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { endpoints } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function BoardsPage() {
  const auth = useAuth();
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", description: "" });
  const [creating, setCreating] = useState(false);

  async function loadBoards() {
    setLoading(true);
    setError("");
    try {
      const data = await auth.authFetch(endpoints.boards);
      setBoards(data.results || data);
    } catch (e) {
      setError(e.message || "Failed to load boards");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBoards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createBoard(event) {
    event.preventDefault();
    if (!form.title.trim()) return;
    setCreating(true);
    try {
      await auth.authFetch(endpoints.boards, {
        method: "POST",
        body: JSON.stringify({
          title: form.title.trim(),
          description: form.description.trim(),
        }),
      });
      setForm({ title: "", description: "" });
      await loadBoards();
    } catch (e) {
      setError(e.message || "Create board failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">MiniTrello</p>
          <h1>Your boards</h1>
          <p className="muted">Manage training projects with columns, cards, comments and activity logs.</p>
        </div>
        <div className="topbar-actions">
          <span className="chip">{auth.user?.display_name || auth.user?.username}</span>
          <button className="btn" onClick={auth.logout}>
            Logout
          </button>
        </div>
      </header>

      <section className="panel create-board-panel">
        <h2>Create board</h2>
        <form className="grid-form" onSubmit={createBoard}>
          <label>
            Title
            <input
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="Sprint Planning"
            />
          </label>
          <label>
            Description
            <input
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Optional short description"
            />
          </label>
          <button className="btn btn-primary" disabled={creating || !form.title.trim()}>
            {creating ? "Creating..." : "Create Board"}
          </button>
        </form>
      </section>

      <section className="boards-grid">
        {loading ? <div className="panel">Loading boards...</div> : null}
        {error ? <div className="panel form-alert">{error}</div> : null}
        {!loading &&
          boards.map((board) => (
            <Link className="board-tile" key={board.id} to={`/boards/${board.id}`}>
              <div className="board-tile-header">
                <h3>{board.title}</h3>
                <span className="chip">{board.my_role || "member"}</span>
              </div>
              <p>{board.description || "No description"}</p>
              <div className="board-tile-footer">
                <span>{board.members_count ?? 0} members</span>
                <span>Open</span>
              </div>
            </Link>
          ))}
      </section>
    </div>
  );
}
