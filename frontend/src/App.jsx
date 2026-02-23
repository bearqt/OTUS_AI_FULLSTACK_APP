import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./lib/auth";
import AuthPage from "./pages/AuthPage";
import BoardPage from "./pages/BoardPage";
import BoardsPage from "./pages/BoardsPage";

function ProtectedRoute({ children }) {
  const auth = useAuth();
  if (!auth.ready) return <div className="loading-screen">Loading...</div>;
  if (!auth.isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnlyRoute({ mode }) {
  const auth = useAuth();
  if (!auth.ready) return <div className="loading-screen">Loading...</div>;
  if (auth.isAuthenticated) return <Navigate to="/boards" replace />;
  return <AuthPage mode={mode} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/boards" replace />} />
      <Route path="/login" element={<PublicOnlyRoute mode="login" />} />
      <Route path="/register" element={<PublicOnlyRoute mode="register" />} />
      <Route
        path="/boards"
        element={
          <ProtectedRoute>
            <BoardsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/boards/:boardId"
        element={
          <ProtectedRoute>
            <BoardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
