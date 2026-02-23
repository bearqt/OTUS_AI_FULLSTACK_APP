import { createContext, startTransition, useContext, useEffect, useState } from "react";

import { apiFetch, endpoints } from "./api";

const STORAGE_KEY = "minitrello_auth";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [tokens, setTokens] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    } catch {
      return null;
    }
  });
  const [user, setUser] = useState(tokens?.user || null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!tokens?.access) {
      setReady(true);
      return;
    }
    let active = true;
    apiFetch(endpoints.me, {}, {
      accessToken: tokens.access,
      refreshToken: tokens.refresh,
      refresh: async () => {
        const ok = await refreshToken();
        return ok;
      },
    })
      .then((me) => {
        if (!active) return;
        startTransition(() => setUser(me));
      })
      .catch(() => {
        if (!active) return;
        logout();
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!tokens) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...tokens, user }));
  }, [tokens, user]);

  async function refreshToken() {
    if (!tokens?.refresh) return false;
    try {
      const result = await apiFetch(endpoints.refresh, {
        method: "POST",
        body: JSON.stringify({ refresh: tokens.refresh }),
      });
      setTokens((prev) => (prev ? { ...prev, access: result.access } : prev));
      return true;
    } catch {
      logout();
      return false;
    }
  }

  async function login(credentials) {
    const result = await apiFetch(endpoints.login, {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    setTokens({ access: result.access, refresh: result.refresh });
    setUser(result.user);
    return result.user;
  }

  async function register(payload) {
    const userResult = await apiFetch(endpoints.register, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await login({ username: payload.username, password: payload.password });
    return userResult;
  }

  function logout() {
    setTokens(null);
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  }

  const value = {
    ready,
    user,
    isAuthenticated: Boolean(tokens?.access && user),
    login,
    register,
    logout,
    authFetch: (path, options) =>
      apiFetch(path, options, {
        accessToken: tokens?.access,
        refreshToken: tokens?.refresh,
        refresh: refreshToken,
      }),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
