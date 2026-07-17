import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Users as UsersIcon,
  UserPlus,
  Trash2,
  Shield,
  ShieldCheck,
  User,
  X,
  Loader2,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import type { User as UserType } from "../types";

export default function Users() {
  const { user: me } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);

  // Form
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "maintainer" | "user">("user");
  const [newFullName, setNewFullName] = useState("");

  useEffect(() => {
    if (me?.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    fetchUsers();
  }, [me]);

  async function fetchUsers() {
    setLoading(true);
    try {
      const res = await api.get("/users?page=1&size=50");
      setUsers(res.data.users || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!newUsername || !newPassword) {
      setCreateError("用户名和密码为必填项");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      await api.post("/users", {
        username: newUsername,
        email: newEmail || `${newUsername}@example.com`,
        password: newPassword,
        role: newRole,
        full_name: newFullName,
      });
      setShowCreate(false);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      setNewRole("user");
      setNewFullName("");
      fetchUsers();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message || "创建失败";
      setCreateError(msg);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(userId: string) {
    if (userId === me?.id) {
      alert("不能删除自己的账号");
      return;
    }
    if (!confirm("确定删除此用户？")) return;
    try {
      await api.delete(`/users/${userId}`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch {
      alert("删除失败");
    }
  }

  const roleIcon = {
    admin: ShieldCheck,
    maintainer: Shield,
    user: User,
  };

  const roleLabel = {
    admin: "管理员",
    maintainer: "维护者",
    user: "用户",
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1000px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-900">用户管理</h1>
          <p className="text-sm text-slate-500 mt-1">管理系统用户和角色权限</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-medium
            hover:bg-slate-800 active:scale-[0.98] transition-all"
        >
          <UserPlus size={16} />
          创建用户
        </button>
      </div>

      {/* Users list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/50 divide-y divide-slate-50 overflow-hidden">
          {users.map((u, i) => {
            const RoleIcon = roleIcon[u.role] || User;
            return (
              <motion.div
                key={u.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: i * 0.04 }}
                className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50/50 transition-colors group"
              >
                <div className="w-10 h-10 rounded-full bg-accent-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-accent-700 font-display font-semibold text-sm">
                    {(u.full_name || u.username)[0]}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {u.full_name || u.username}
                    </p>
                    {u.id === me?.id && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-accent-50 text-accent-600 font-medium">
                        当前账号
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    {u.username} · {u.email}
                  </p>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <RoleIcon size={14} className="text-slate-400" />
                  <span className="text-[11px] text-slate-500 font-medium">
                    {roleLabel[u.role]}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {u.is_active ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-emerald-50 text-emerald-600 font-medium">
                      活跃
                    </span>
                  ) : (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-400 font-medium">
                      已禁用
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(u.id)}
                    disabled={u.id === me?.id}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50
                      opacity-0 group-hover:opacity-100 disabled:opacity-0 transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </motion.div>
            );
          })}
          {users.length === 0 && (
            <div className="text-center py-12 text-sm text-slate-400">
              暂无用户
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div
          className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4"
          onClick={() => setShowCreate(false)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display text-lg font-bold text-slate-900">
                创建用户
              </h2>
              <button
                onClick={() => setShowCreate(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    用户名 <span className="text-red-400">*</span>
                  </label>
                  <input
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm
                      focus:outline-none focus:border-accent-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    密码 <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm
                      focus:outline-none focus:border-accent-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  邮箱
                </label>
                <input
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm
                    focus:outline-none focus:border-accent-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  姓名
                </label>
                <input
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm
                    focus:outline-none focus:border-accent-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  角色
                </label>
                <div className="flex gap-2">
                  {(["user", "maintainer", "admin"] as const).map((r) => (
                    <button
                      key={r}
                      onClick={() => setNewRole(r)}
                      className={`flex-1 py-2 rounded-lg text-xs font-medium border transition-all
                        ${newRole === r
                          ? "border-accent-400 bg-accent-50 text-accent-700"
                          : "border-slate-200 text-slate-500 hover:bg-slate-50"
                        }`}
                    >
                      {roleLabel[r]}
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
                    hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-medium
                    hover:bg-slate-800 disabled:opacity-50"
                >
                  {creating && <Loader2 size={16} className="animate-spin" />}
                  {creating ? "创建中..." : "创建"}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
