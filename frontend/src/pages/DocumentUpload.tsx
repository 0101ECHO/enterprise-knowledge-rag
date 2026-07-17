import { useEffect, useState, useRef, type DragEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Upload, FileText, File, CheckCircle2, XCircle,
  Loader2, ArrowLeft, Clock, Trash2, Eye,
} from "lucide-react";
import api from "../api/client";
import type { Document } from "../types";

export default function DocumentUpload() {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [kbName, setKbName] = useState("");

  useEffect(() => {
    if (kbId) {
      api.get(`/knowledge-bases/${kbId}`).then((r) => setKbName(r.data.name)).catch(() => {});
      fetchDocs();
    }
  }, [kbId]);

  async function fetchDocs() {
    try {
      const res = await api.get(`/documents?kb_id=${kbId}&page=1&size=50`);
      setDocs(res.data.documents || []);
    } catch {
      // ignore
    }
  }

  async function uploadFiles(files: FileList | File[]) {
    if (!kbId) return;
    setUploading(true);
    const fileArr = Array.from(files);

    for (const file of fileArr) {
      const form = new FormData();
      form.append("file", file);
      try {
        await api.post(`/documents/upload/${kbId}`, form);
      } catch {
        // continue
      }
    }
    setUploading(false);
    // Poll for status updates
    setTimeout(fetchDocs, 2000);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  }

  const statusIcon = {
    pending: Clock,
    processing: Loader2,
    completed: CheckCircle2,
    failed: XCircle,
  };
  const statusColor = {
    pending: "text-amber-500",
    processing: "text-blue-500",
    completed: "text-emerald-500",
    failed: "text-red-500",
  };
  const statusLabel = {
    pending: "等待处理",
    processing: "处理中",
    completed: "已完成",
    failed: "失败",
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate("/knowledge-bases")}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 mb-3 transition-colors"
        >
          <ArrowLeft size={16} />
          返回知识库列表
        </button>
        <h1 className="font-display text-2xl font-bold text-slate-900">
          {kbName || "上传文档"}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          支持 PDF、Word、Markdown、HTML、TXT、图片等格式
        </p>
      </div>

      {/* Drop zone */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200
          ${dragOver
            ? "border-accent-400 bg-accent-50/50"
            : "border-slate-200 hover:border-accent-300 hover:bg-slate-50/50"}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && uploadFiles(e.target.files)}
          accept=".pdf,.docx,.doc,.md,.txt,.html,.htm,.png,.jpg,.jpeg,.bmp,.tiff"
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 size={40} className="text-accent-500 animate-spin" />
            <p className="text-sm text-slate-600 font-medium">上传中...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-accent-50 flex items-center justify-center">
              <Upload size={24} className="text-accent-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">
                拖放文件到此处上传
              </p>
              <p className="text-xs text-slate-400 mt-1">或点击选择文件</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Document list */}
      <div className="mt-8">
        <h2 className="font-display text-lg font-semibold text-slate-900 mb-4">
          已上传文档
        </h2>
        {docs.length === 0 ? (
          <div className="text-center py-12 text-sm text-slate-400">
            暂无文档，请上传文件
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200/50 divide-y divide-slate-50 overflow-hidden">
            {docs.map((doc) => {
              const Icon = statusIcon[doc.status] || File;
              const colorClass = statusColor[doc.status] || "text-slate-400";
              return (
                <div
                  key={doc.id}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50/50 transition-colors"
                >
                  <div className="w-9 h-9 rounded-xl bg-slate-50 flex items-center justify-center flex-shrink-0">
                    <FileText size={16} className="text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {doc.title || doc.file_name}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {(doc.file_size / 1024).toFixed(0)} KB · {doc.file_type.toUpperCase()}
                      {doc.chunk_count > 0 && ` · ${doc.chunk_count} 分块`}
                    </p>
                    {doc.processing_error && (
                      <p className="text-[11px] text-red-400 mt-0.5 truncate">
                        {doc.processing_error}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Icon size={14} className={`${colorClass} ${doc.status === "processing" ? "animate-spin" : ""}`} />
                    <span className={`text-[11px] font-medium ${colorClass}`}>
                      {statusLabel[doc.status]}
                    </span>
                    <button
                      onClick={async (e) => { e.stopPropagation(); if (!confirm("确定删除此文档？")) return;
                        try { await api.delete(`/documents/${doc.id}`); fetchDocs(); } catch { alert("删除失败"); } }}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="删除文档"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
