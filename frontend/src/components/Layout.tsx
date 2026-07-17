import { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  BookOpen,
  MessageSquare,
  Upload,
  History,
  Users,
  Menu,
  X,
  LogOut,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "仪表盘" },
  { to: "/knowledge-bases", icon: BookOpen, label: "知识库" },
  { to: "/chat", icon: MessageSquare, label: "智能问答" },
  { to: "/conversations", icon: History, label: "对话历史" },
  { to: "/users", icon: Users, label: "用户管理", adminOnly: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const filteredNav = navItems.filter(
    (item) => !item.adminOnly || user?.role === "admin"
  );

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-[100dvh] flex bg-surface">
      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 bg-white border-r border-slate-200/60
          flex flex-col transition-transform duration-300
          ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-accent-600 flex items-center justify-center">
            <span className="text-white font-display font-bold text-sm">R</span>
          </div>
          <div>
            <h1 className="text-sm font-display font-semibold text-slate-900">
              知识库 RAG
            </h1>
            <p className="text-[10px] text-slate-400">Enterprise Platform</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {filteredNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
                transition-all duration-200 group
                ${
                  isActive
                    ? "bg-accent-50 text-accent-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
              <ChevronRight
                size={14}
                className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity"
              />
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-slate-100 p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-accent-100 flex items-center justify-center">
              <span className="text-accent-700 font-display font-semibold text-sm">
                {user?.full_name?.[0] || user?.username?.[0] || "U"}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">
                {user?.full_name || user?.username}
              </p>
              <p className="text-[11px] text-slate-400 capitalize">
                {user?.role === "admin"
                  ? "管理员"
                  : user?.role === "maintainer"
                  ? "维护者"
                  : "用户"}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="退出登录"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar (mobile) */}
        <header className="lg:hidden h-14 flex items-center gap-3 px-4 bg-white border-b border-slate-100">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 -ml-2 rounded-lg text-slate-600 hover:bg-slate-50"
          >
            <Menu size={20} />
          </button>
          <span className="font-display font-semibold text-sm text-slate-900">
            知识库 RAG
          </span>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
