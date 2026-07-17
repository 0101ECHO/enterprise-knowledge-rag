import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BookOpen,
  FileText,
  MessageSquare,
  TrendingUp,
  ArrowRight,
  Plus,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import type { KnowledgeBase, Conversation } from "../types";

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  delay,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: delay * 0.1 }}
      className="bg-white rounded-2xl border border-slate-200/50 p-5 flex items-center gap-4
        hover:border-accent-200 hover:shadow-sm transition-all duration-300"
    >
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-display font-bold text-slate-900">{value}</p>
        <p className="text-[13px] text-slate-500 mt-0.5">{label}</p>
      </div>
    </motion.div>
  );
}

function QuickAction({
  icon: Icon,
  label,
  desc,
  to,
  delay,
}: {
  icon: React.ElementType;
  label: string;
  desc: string;
  to: string;
  delay: number;
}) {
  const navigate = useNavigate();
  return (
    <motion.button
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: delay * 0.1 }}
      onClick={() => navigate(to)}
      className="flex items-center gap-4 p-4 rounded-2xl bg-white border border-slate-200/50
        text-left hover:border-accent-200 hover:shadow-sm transition-all duration-300 group"
    >
      <div className="w-10 h-10 rounded-xl bg-accent-50 flex items-center justify-center text-accent-600">
        <Icon size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
      </div>
      <ArrowRight size={16} className="text-slate-300 group-hover:text-accent-500 transition-colors" />
    </motion.button>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [kbRes, convRes] = await Promise.allSettled([
          api.get("/knowledge-bases?page=1&size=10"),
          api.get("/chat/conversations?page=1&size=10"),
        ]);
        if (kbRes.status === "fulfilled") {
          setKbs(kbRes.value.data.knowledge_bases || []);
        }
        if (convRes.status === "fulfilled") {
          setConversations(convRes.value.data || []);
        }
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const totalDocs = kbs.reduce((sum, kb) => sum + (kb.document_count || 0), 0);
  const totalChunks = kbs.reduce((sum, kb) => sum + (kb.chunk_count || 0), 0);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="font-display text-2xl font-bold text-slate-900">
          欢迎回来{user?.full_name ? `，${user.full_name}` : ""}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          这是您的知识库平台概览
        </p>
      </motion.div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={BookOpen}
          label="知识库"
          value={kbs.length}
          color="bg-blue-50 text-blue-600"
          delay={0}
        />
        <StatCard
          icon={FileText}
          label="文档总数"
          value={totalDocs}
          color="bg-emerald-50 text-emerald-600"
          delay={1}
        />
        <StatCard
          icon={TrendingUp}
          label="分块总数"
          value={totalChunks}
          color="bg-amber-50 text-amber-600"
          delay={2}
        />
        <StatCard
          icon={MessageSquare}
          label="对话数"
          value={conversations.length}
          color="bg-purple-50 text-purple-600"
          delay={3}
        />
      </div>

      {/* Quick actions + Recent */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick actions */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-display text-lg font-semibold text-slate-900">
            快捷操作
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            <QuickAction
              icon={Plus}
              label="创建知识库"
              desc="建立新的知识库并导入文档"
              to="/knowledge-bases"
              delay={4}
            />
            <QuickAction
              icon={MessageSquare}
              label="开始问答"
              desc="基于知识库进行智能检索问答"
              to="/chat"
              delay={5}
            />
            <QuickAction
              icon={FileText}
              label="上传文档"
              desc="上传 PDF、Word、网页等多种格式"
              to="/knowledge-bases"
              delay={6}
            />
            <QuickAction
              icon={BookOpen}
              label="浏览知识库"
              desc="查看和管理所有知识库内容"
              to="/knowledge-bases"
              delay={7}
            />
          </div>
        </div>

        {/* Recent KBs */}
        <div className="space-y-4">
          <h2 className="font-display text-lg font-semibold text-slate-900">
            最近知识库
          </h2>
          <div className="bg-white rounded-2xl border border-slate-200/50 divide-y divide-slate-50">
            {kbs.length === 0 ? (
              <div className="p-6 text-center text-sm text-slate-400">
                暂无知识库，
                <button
                  onClick={() => navigate("/knowledge-bases")}
                  className="text-accent-600 hover:underline ml-1"
                >
                  创建第一个
                </button>
              </div>
            ) : (
              kbs.slice(0, 5).map((kb) => (
                <button
                  key={kb.id}
                  onClick={() => navigate(`/chat/${kb.id}`)}
                  className="w-full flex items-center gap-3 p-4 text-left hover:bg-slate-50 transition-colors first:rounded-t-2xl last:rounded-b-2xl"
                >
                  <div className="w-8 h-8 rounded-lg bg-accent-50 flex items-center justify-center flex-shrink-0">
                    <BookOpen size={14} className="text-accent-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {kb.name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {kb.document_count} 文档 · {kb.chunk_count} 分块
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
