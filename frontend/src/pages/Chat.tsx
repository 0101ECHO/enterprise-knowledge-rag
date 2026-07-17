import { useEffect, useState, useRef, type FormEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  Send, Sparkles, Loader2, Plus, PanelRightClose, PanelRight,
  Trash2, Pencil, Check, X, AlertCircle, FileText, ExternalLink,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import type { KnowledgeBase, Conversation, Message, Source } from "../types";

export default function Chat() {
  const { kbId: paramKbId, convId: paramConvId } = useParams<{ kbId?: string; convId?: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState(paramKbId || "");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState(paramConvId || "");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [currentSources, setCurrentSources] = useState<Source[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState("");

  // Rename state
  const [editingConvId, setEditingConvId] = useState("");
  const [editTitle, setEditTitle] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Fetch KBs
  useEffect(() => {
    api.get("/knowledge-bases?page=1&size=50").then((r) => {
      const items: KnowledgeBase[] = r.data.knowledge_bases || [];
      setKbs(items);
      if (!selectedKbId && items.length > 0) setSelectedKbId(items[0].id);
    }).catch(() => {});
  }, []);

  // Sync URL params
  useEffect(() => {
    if (paramKbId && paramKbId !== selectedKbId) setSelectedKbId(paramKbId);
    if (paramConvId && paramConvId !== activeConvId) {
      setActiveConvId(paramConvId);
      loadConversation(paramConvId);
    }
  }, [paramKbId, paramConvId]);

  // Fetch conversations
  useEffect(() => {
    if (!selectedKbId) { setConversations([]); return; }
    api.get(`/chat/conversations`).then((r) => setConversations(r.data || [])).catch(() => {});
  }, [selectedKbId]);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // ---- Actions ----

  function startNewChat() {
    setActiveConvId("");
    setMessages([]);
    setStreamingText("");
    setCurrentSources([]);
    setError("");
    if (paramKbId) navigate(`/chat/${paramKbId}`, { replace: true });
  }

  async function loadConversation(convId: string) {
    setActiveConvId(convId);
    try {
      const res = await api.get(`/chat/conversations/${convId}`);
      setMessages(res.data.messages || []);
      setStreamingText("");
      setCurrentSources([]);
      setError("");
    } catch { startNewChat(); }
  }

  async function handleRename(convId: string) {
    if (!editTitle.trim()) { setEditingConvId(""); return; }
    try {
      await api.patch(`/chat/conversations/${convId}?title=${encodeURIComponent(editTitle.trim())}`);
      setConversations((prev) => prev.map((c) => c.id === convId ? { ...c, title: editTitle.trim() } : c));
    } catch { alert("重命名失败"); }
    setEditingConvId("");
    setEditTitle("");
  }

  async function handleDeleteConv(convId: string) {
    if (!confirm("确定删除此对话？所有消息将被永久删除。")) return;
    try {
      await api.delete(`/chat/conversations/${convId}`);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) startNewChat();
    } catch { alert("删除失败"); }
  }

  async function handleSend(e?: FormEvent) {
    e?.preventDefault();
    if (!input.trim() || !selectedKbId || sending) return;
    setError("");

    const userMsg: Message = {
      id: Date.now().toString(),
      conversation_id: activeConvId || "new",
      role: "user", content: input.trim(), created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);
    setStreamingText("");
    setCurrentSources([]);

    try {
      const res = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          kb_id: selectedKbId,
          question: userMsg.content,
          conversation_id: activeConvId || undefined,
          use_workflow: false,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error((errData as { detail?: string }).detail || `HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("无法读取流响应");
      const decoder = new TextDecoder();
      let buffer = "";
      let newConvId = activeConvId;
      let gotAnswer = false;
      let answer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6).trim();
            if (!raw || raw === "[DONE]") continue;
            try {
              const data = JSON.parse(raw);
              if (currentEvent === "sources") {
                setCurrentSources(data as Source[]);
              } else if (currentEvent === "content" || currentEvent === "token") {
                const text = typeof data === "string" ? data : data.text || data.data || "";
                answer += text;
                setStreamingText(answer);
                gotAnswer = true;
              } else if (currentEvent === "done") {
                if (data.conversation_id) newConvId = data.conversation_id;
              } else if (currentEvent === "error") {
                setError(typeof data === "string" ? data : data.message || "生成错误");
              }
            } catch { /* skip malformed data */ }
          }
        }
      }

      // Flush remaining
      if (buffer.startsWith("data: ")) {
        const raw = buffer.slice(6).trim();
        if (raw && raw !== "[DONE]") {
          try {
            const data = JSON.parse(raw);
            const text = typeof data === "string" ? data : data.text || data.data || "";
            answer += text;
            setStreamingText(answer);
          } catch { /* ignore */ }
        }
      }

      setStreamingText((prev) => {
        if (prev || answer) {
          setMessages((msgs) => [
            ...msgs,
            {
              id: (Date.now() + 1).toString(),
              conversation_id: newConvId || activeConvId,
              role: "assistant",
              content: prev || answer,
              sources: currentSources,
              created_at: new Date().toISOString(),
            },
          ]);
        }
        return "";
      });
      setCurrentSources([]);

      if (newConvId && newConvId !== activeConvId) {
        setActiveConvId(newConvId);
        api.get(`/chat/conversations`).then((r) => setConversations(r.data || [])).catch(() => {});
        navigate(`/chat/${selectedKbId}/${newConvId}`, { replace: true });
      }
    } catch (err: unknown) {
      setError((err as Error).message || "请求失败");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100dvh-4rem)] lg:h-[calc(100dvh)]">
      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }} animate={{ width: 280, opacity: 1 }} exit={{ width: 0, opacity: 0 }}
            className="hidden lg:block border-r border-slate-200/60 bg-white flex-shrink-0 overflow-hidden"
          >
            <div className="w-[280px] h-full flex flex-col">
              <div className="p-4 border-b border-slate-100">
                <button onClick={startNewChat} className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
                  bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 active:scale-[0.98] transition-all">
                  <Plus size={16} />新建对话
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
                {conversations.map((conv) => (
                  <div key={conv.id} className={`group rounded-xl transition-all ${conv.id === activeConvId ? "bg-accent-50" : "hover:bg-slate-50"}`}>
                    {editingConvId === conv.id ? (
                      <div className="flex items-center gap-1 px-2 py-1.5">
                        <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => { if (e.key === "Enter") handleRename(conv.id); if (e.key === "Escape") setEditingConvId(""); }}
                          autoFocus className="flex-1 px-2 py-1 text-sm border rounded-lg focus:outline-none focus:border-accent-400" />
                        <button onClick={() => handleRename(conv.id)} className="p-1 text-emerald-500 hover:bg-emerald-50 rounded"><Check size={14} /></button>
                        <button onClick={() => setEditingConvId("")} className="p-1 text-slate-400 hover:bg-slate-100 rounded"><X size={14} /></button>
                      </div>
                    ) : (
                      <button onClick={() => { loadConversation(conv.id); navigate(`/chat/${selectedKbId}/${conv.id}`, { replace: true }); }}
                        className="w-full text-left px-3 py-2 text-sm flex items-center gap-2">
                        <span className={`flex-1 truncate ${conv.id === activeConvId ? "text-accent-700 font-medium" : "text-slate-600"}`}>
                          {conv.title || "新建对话"}
                        </span>
                        <span className="text-[11px] text-slate-400">{conv.message_count}</span>
                        <span className="hidden group-hover:flex items-center gap-0.5">
                          <button onClick={(e) => { e.stopPropagation(); setEditingConvId(conv.id); setEditTitle(conv.title || ""); }}
                            className="p-0.5 text-slate-400 hover:text-accent-500 rounded" title="重命名"><Pencil size={12} /></button>
                          <button onClick={(e) => { e.stopPropagation(); handleDeleteConv(conv.id); }}
                            className="p-0.5 text-slate-400 hover:text-red-500 rounded" title="删除"><Trash2 size={12} /></button>
                        </span>
                      </button>
                    )}
                  </div>
                ))}
                {conversations.length === 0 && <p className="text-xs text-slate-400 text-center py-8">暂无对话</p>}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <header className="h-14 flex items-center gap-3 px-4 border-b border-slate-100 bg-white flex-shrink-0">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-50 hidden lg:block">
            {sidebarOpen ? <PanelRightClose size={18} /> : <PanelRight size={18} />}
          </button>
          <select value={selectedKbId} onChange={(e) => { setSelectedKbId(e.target.value); startNewChat(); }}
            className="flex-1 max-w-xs py-1.5 px-3 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 focus:outline-none focus:border-accent-400">
            <option value="">选择知识库...</option>
            {kbs.map((kb) => <option key={kb.id} value={kb.id}>{kb.name}</option>)}
          </select>
          <div className="flex-1" />
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          {messages.length === 0 && !streamingText ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl bg-accent-50 flex items-center justify-center mb-4">
                <Sparkles size={28} className="text-accent-500" />
              </div>
              <h2 className="font-display text-lg font-bold text-slate-900 mb-2">智能知识库问答</h2>
              <p className="text-sm text-slate-500 max-w-sm">选择知识库后输入问题，系统将基于文档内容生成精准回答。</p>
              {!selectedKbId && <p className="text-sm text-amber-600 mt-3 flex items-center gap-1.5"><AlertCircle size={14} />请先选择一个知识库</p>}
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : ""}`}>
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-xl bg-accent-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Sparkles size={14} className="text-accent-600" />
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user" ? "bg-slate-900 text-white" : "bg-white border border-slate-200/50 text-slate-800"}`}>
                    {msg.role === "assistant" ? (
                      <div className="markdown-body prose prose-sm"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                    ) : <p>{msg.content}</p>}
                    {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-100">
                        <p className="text-[11px] font-semibold text-slate-500 mb-2">参考来源</p>
                        {msg.sources.map((src, i) => (
                          <div key={i} className="flex items-start gap-2 text-[11px] text-slate-500 bg-slate-50 rounded-lg px-2.5 py-1.5 mb-1">
                            <ExternalLink size={12} className="mt-0.5 flex-shrink-0" />
                            <div>
                              <span className="font-medium text-slate-700">{src.document_title || "来源"}</span>
                              {src.page && <span className="text-slate-400"> · 第{src.page}页</span>}
                              <span className="text-slate-400"> · 相关度 {(src.score * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-xl bg-slate-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-white text-xs font-bold">{(user?.full_name || user?.username || "U")[0]}</span>
                    </div>
                  )}
                </div>
              ))}
              {streamingText && (
                <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-xl bg-accent-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Sparkles size={14} className="text-accent-600" />
                  </div>
                  <div className="max-w-[80%] bg-white border border-slate-200/50 rounded-2xl px-4 py-3 text-sm leading-relaxed text-slate-800">
                    <div className="markdown-body prose prose-sm"><ReactMarkdown>{streamingText}</ReactMarkdown></div>
                    <span className="inline-block w-1.5 h-4 bg-accent-500 animate-pulse rounded-sm ml-0.5 align-middle" />
                  </div>
                </div>
              )}
              {error && (
                <div className="flex justify-center">
                  <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-50 text-red-500 text-sm">
                    <AlertCircle size={14} />{error}
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        <div className="flex-shrink-0 border-t border-slate-100 bg-white px-4 py-3">
          <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-3">
            <input ref={useRef<HTMLInputElement>(null)} value={input} onChange={(e) => setInput(e.target.value)}
              placeholder={selectedKbId ? "输入问题，按 Enter 发送..." : "请先选择知识库"}
              disabled={sending || !selectedKbId}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-900
                placeholder:text-slate-400 focus:outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-100
                disabled:opacity-50 transition-all" />
            <button type="submit" disabled={sending || !input.trim() || !selectedKbId}
              className="px-4 py-2.5 rounded-xl bg-slate-900 text-white hover:bg-slate-800 active:scale-[0.98]
                disabled:opacity-40 transition-all">
              {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
