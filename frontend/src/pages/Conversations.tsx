import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageSquare, Trash2, ArrowRight, Loader2, History } from "lucide-react";
import api from "../api/client";
import type { Conversation } from "../types";

export default function Conversations() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchAll();
  }, [page]);

  async function fetchAll() {
    setLoading(true);
    try {
      const res = await api.get(`/chat/conversations?page=${page}&size=20`);
      setConversations(res.data || []);
      setTotal(res.data.total || 0);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(convId: string) {
    if (!confirm("确定删除此对话？")) return;
    try {
      await api.delete(`/chat/conversations/${convId}`);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
    } catch {
      alert("删除失败");
    }
  }

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="p-6 lg:p-8 max-w-[1000px] mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-slate-900">对话历史</h1>
        <p className="text-sm text-slate-500 mt-1">查看和管理所有对话记录</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-white rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : conversations.length === 0 ? (
        <div className="text-center py-20">
          <History size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500 text-sm">暂无对话记录</p>
          <button
            onClick={() => navigate("/chat")}
            className="mt-3 text-sm text-accent-600 hover:underline"
          >
            开始第一个对话
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {conversations.map((conv, i) => (
            <motion.div
              key={conv.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.04 }}
              onClick={() => navigate(`/chat/${conv.kb_id || ""}`)}
              className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-slate-200/50
                hover:border-accent-200 hover:shadow-sm cursor-pointer transition-all group"
            >
              <div className="w-10 h-10 rounded-xl bg-accent-50 flex items-center justify-center flex-shrink-0">
                <MessageSquare size={16} className="text-accent-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {conv.title || "新建对话"}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {conv.message_count} 条消息 ·
                  {new Date(conv.created_at).toLocaleDateString("zh-CN")}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(conv.id);
                  }}
                  className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50
                    opacity-0 group-hover:opacity-100 transition-all"
                >
                  <Trash2 size={14} />
                </button>
                <ArrowRight size={14} className="text-slate-300 group-hover:text-accent-500 transition-colors" />
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              onClick={() => setPage(i + 1)}
              className={`w-9 h-9 rounded-lg text-sm font-medium transition-all
                ${page === i + 1
                  ? "bg-slate-900 text-white"
                  : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
