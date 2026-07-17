import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import KnowledgeBases from "./pages/KnowledgeBases";
import DocumentUpload from "./pages/DocumentUpload";
import Chat from "./pages/Chat";
import Conversations from "./pages/Conversations";
import Users from "./pages/Users";

export default function App() {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-surface">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-[3px] border-slate-200 border-t-accent-600 rounded-full animate-spin" />
          <span className="text-sm text-slate-400">加载中...</span>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/knowledge-bases" element={<KnowledgeBases />} />
        <Route path="/knowledge-bases/:kbId/upload" element={<DocumentUpload />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/chat/:kbId" element={<Chat />} />
        <Route path="/chat/:kbId/:convId" element={<Chat />} />
        <Route path="/conversations" element={<Conversations />} />
        <Route path="/users" element={<Users />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
