import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { LogIn, Loader2, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    navigate("/dashboard", { replace: true });
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username || !password) {
      setError("请输入用户名和密码");
      return;
    }
    setLoading(true);
    try {
      await login({ username, password });
      navigate("/dashboard", { replace: true });
    } catch {
      setError("用户名或密码错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-surface p-4">
      <div className="w-full max-w-5xl grid lg:grid-cols-2 bg-white rounded-[2rem] shadow-sm border border-slate-200/50 overflow-hidden">
        {/* Left: Brand */}
        <div className="hidden lg:flex flex-col justify-between p-10 bg-slate-900 relative overflow-hidden">
          {/* Decorative grid */}
          <div className="absolute inset-0 opacity-[0.03]">
            <div className="w-full h-full" style={{
              backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
              backgroundSize: "48px 48px",
            }} />
          </div>

          {/* Gradient orb */}
          <div className="absolute top-[-20%] right-[-20%] w-96 h-96 rounded-full bg-accent-500/20 blur-[120px]" />

          <div className="relative z-10">
            <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur flex items-center justify-center mb-8">
              <span className="text-white font-display font-bold text-lg">R</span>
            </div>
            <h2 className="font-display text-3xl font-bold text-white mb-3 leading-tight">
              企业级知识库
              <br />
              <span className="text-accent-400">RAG 平台</span>
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed max-w-xs">
              基于 DeepSeek + LangChain 的智能文档检索与问答系统，
              支持多源文档接入与带引用的精准回答。
            </p>
          </div>

          <div className="relative z-10 text-slate-500 text-xs">
            <p>&copy; 2026 Enterprise RAG Platform</p>
          </div>
        </div>

        {/* Right: Login form */}
        <div className="p-8 sm:p-12 flex items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="w-full max-w-sm mx-auto"
          >
            {/* Mobile logo */}
            <div className="lg:hidden flex items-center gap-3 mb-10">
              <div className="w-10 h-10 rounded-xl bg-accent-600 flex items-center justify-center">
                <span className="text-white font-display font-bold">R</span>
              </div>
              <span className="font-display font-semibold text-slate-900">
                知识库 RAG
              </span>
            </div>

            <h1 className="font-display text-2xl font-bold text-slate-900 mb-1">
              欢迎回来
            </h1>
            <p className="text-sm text-slate-500 mb-8">
              登录以继续使用知识库管理平台
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Username */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  用户名
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  autoComplete="username"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50
                    text-slate-900 placeholder:text-slate-400 text-sm
                    focus:outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-100
                    transition-all duration-200"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  密码
                </label>
                <div className="relative">
                  <input
                    type={showPwd ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="请输入密码"
                    autoComplete="current-password"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50
                      text-slate-900 placeholder:text-slate-400 text-sm pr-11
                      focus:outline-none focus:border-accent-400 focus:ring-2 focus:ring-accent-100
                      transition-all duration-200"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd(!showPwd)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPwd ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Error */}
              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2"
                >
                  {error}
                </motion.p>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                  bg-slate-900 text-white text-sm font-medium
                  hover:bg-slate-800 active:scale-[0.98]
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all duration-200"
              >
                {loading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <LogIn size={18} />
                )}
                {loading ? "登录中..." : "登录"}
              </button>
            </form>

            {/* Default accounts hint */}
            <div className="mt-8 p-4 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-xs font-medium text-slate-500 mb-2">默认测试账号</p>
              <div className="space-y-1 text-xs text-slate-400">
                <p>admin / admin123456（管理员）</p>
                <p>maintainer / maintainer123（维护者）</p>
                <p>user / user123456（普通用户）</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
