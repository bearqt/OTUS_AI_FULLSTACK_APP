const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function jsonHeaders(extra = {}) {
  return { "Content-Type": "application/json", ...extra };
}

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function apiFetch(path, options = {}, auth = null) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = {
    ...(options.body ? jsonHeaders() : {}),
    ...(options.headers || {}),
  };

  if (auth?.accessToken) {
    headers.Authorization = `Bearer ${auth.accessToken}`;
  }

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && auth?.refreshToken && typeof auth.refresh === "function" && !options.__retried) {
    const refreshed = await auth.refresh();
    if (refreshed) {
      return apiFetch(path, { ...options, __retried: true }, auth);
    }
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      (payload && typeof payload === "object" && (payload.detail || payload.error || payload.message)) ||
      `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }

  return payload;
}

export const endpoints = {
  login: "/auth/login/",
  register: "/auth/register/",
  refresh: "/auth/refresh/",
  me: "/auth/me/",
  boards: "/boards/",
  boardDetail: (id) => `/boards/${id}/`,
  boardMembers: (id) => `/boards/${id}/members/`,
  boardRemoveMember: (id) => `/boards/${id}/members/remove/`,
  boardActivity: (id) => `/boards/${id}/activity/`,
  columns: "/columns/",
  reorderColumns: "/columns/reorder/",
  labels: "/labels/",
  cards: "/cards/",
  card: (id) => `/cards/${id}/`,
  moveCard: (id) => `/cards/${id}/move/`,
  comments: "/comments/",
  comment: (id) => `/comments/${id}/`,
};
