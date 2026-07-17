import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Trash2,
  MessageSquare,
  Upload,
  Loader2,
  BookOpen,
  Search,
  Globe,
  Lock,
  Users2,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import type { KnowledgeBase } from "../types";

export default function KnowledgeBases() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // Create form
  const [kbName, setKbName] = useState("");
  const [kbDesc, setKbDesc] = useState("");
  const [kbVisibility, setKbVisibility] = useState<"public" | "private" | "role_based">("private");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    fetchKBs();
  }, []);

  async function fetchKBs() {
    setLoading(true);
    try {
      const res = await api.get("/knowledge-bases?page=1&size=50");
      setKbs(res.data.knowledge_bases || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!kbName.trim()) {
      setCreateError("请输入知识库名称");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      await api.post("/knowledge-bases", {
        name: kbName.trim(),
        description: kbDesc.trim(),
        visibility: kbVisibility,
      });
      setShowCreate(false);
      setKbName("");
      setKbDesc("");
      setKbVisibility("private");
      fetchKBs();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message || "创建失败";
      setCreateError(msg);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(kbId: string, name: string) {
    if (!confirm(`确定删除知识库「${name}」？此操作不可撤销。`)) return;
    try {
      await api.delete(`/knowledge-bases/${kbId}`);
      setKbs((prev) => prev.filter((k) => k.id !== kbId));
    } catch {
      alert("删除失败");
    }
  }

  const filtered = kbs.filter(
    (kb) =>
      kb.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (kb.description || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const visibilityIcon = {
    public: Globe,
    private: Lock,
    role_based: Users2,
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-900">知识库</h1>
          <p className="text-sm text-slate-500 mt-1">管理所有知识库及其文档</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-medium
            hover:bg-slate-800 active:scale-[0.98] transition-all"
        >
          <Plus size={16} />
          创建知识库
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="搜索知识库..."
          className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white
            text-sm text-slate-900 placeholder:text-slate-400
            focus:outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-100
            transition-all"
        />
      </div>

      {/* KB Grid */}
      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 bg-white rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <BookOpen size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500 text-sm">暂无知识库</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 text-sm text-accent-600 hover:underline"
          >
            创建第一个知识库
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((kb, i) => {
            const VisIcon = visibilityIcon[kb.visibility] || Lock;
            return (
              <motion.div
                key={kb.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="bg-white rounded-2xl border border-slate-200/50 p-5
                  hover:border-accent-200 hover:shadow-sm transition-all duration-300 group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-accent-50 flex items-center justify-center">
                    <BookOpen size={18} className="text-accent-600" />
                  </div>
                  <div className="flex items-center gap-1">
                    {(user?.role === "admin" || user?.role === "maintainer") && (
                      <button
                        onClick={() => handleDelete(kb.id, kb.name)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>

                <h3 className="font-display font-semibold text-slate-900 text-base mb-1">
                  {kb.name}
                </h3>
                {kb.description && (
                  <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                    {kb.description}
                  </p>
                )}

                <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                  <span>{kb.document_count} 文档</span>
                  <span>{kb.chunk_count} 分块</span>
                  <span className="flex items-center gap-1">
                    <VisIcon size={12} />
                    {kb.visibility === "public"
                      ? "公开"
                      : kb.visibility === "role_based"
                      ? "角色可见"
                      : "私有"}
                  </span>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/chat/${kb.id}`)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg
                      bg-accent-50 text-accent-700 text-xs font-medium
                      hover:bg-accent-100 transition-colors"
                  >
                    <MessageSquare size={13} />
                    问答
                  </button>
                  <button
                    onClick={() => navigate(`/knowledge-bases/${kb.id}/upload`)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg
                      bg-slate-50 text-slate-600 text-xs font-medium
                      hover:bg-slate-100 transition-colors"
                  >
                    <Upload size={13} />
                    上传文档
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4"
            onClick={() => setShowCreate(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-display text-lg font-bold text-slate-900">
                  创建知识库
                </h2>
                <button
                  onClick={() => setShowCreate(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    名称 <span className="text-red-400">*</span>
                  </label>
                  <input
                    value={kbName}
                    onChange={(e) => setKbName(e.target.value)}
                    placeholder="例如：产品手册"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm
                      focus:outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    描述
                  </label>
                  <textarea
                    value={kbDesc}
                    onChange={(e) => setKbDesc(e.target.value)}
                    rows={2}
                    placeholder="知识库的简要描述..."
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm resize-none
                      focus:outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    可见性
                  </label>
                  <div className="flex gap-2">
                    {(["private", "public", "role_based"] as const).map((v) => (
                      <button
                        key={v}
                        onClick={() => setKbVisibility(v)}
                        className={`flex-1 py-2 rounded-lg text-xs font-medium border transition-all
                          ${
                            kbVisibility === v
                              ? "border-accent-400 bg-accent-50 text-accent-700"
                              : "border-slate-200 text-slate-500 hover:bg-slate-50"
                          }`}
                      >
                        {v === "private" ? "私有" : v === "public" ? "公开" : "角色可见"}
                      </button>
                    ))}
                  </div>
                </div>

                {createError && (
                  <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">
                    {createError}
                  </p>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowCreate(false)}
                    className="flex-1 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-600
                      hover:bg-slate-50 transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={creating}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-medium
                      hover:bg-slate-800 disabled:opacity-50 transition-all"
                  >
                    {creating && <Loader2 size={16} className="animate-spin" />}
                    {creating ? "创建中..." : "创建"}
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
