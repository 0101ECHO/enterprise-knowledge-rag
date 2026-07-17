import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import api from "../api/client";
import type { User, LoginRequest, LoginResponse } from "../types";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (req: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  isLoading: true,
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("access_token")
  );
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async (t: string) => {
    try {
      const res = await api.get("/users/me");
      setUser(res.data);
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchUser(token).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [token, fetchUser]);

  const login = async (req: LoginRequest) => {
    const res = await api.post<LoginResponse>("/auth/login", req);
    const { access_token, refresh_token } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    setToken(access_token);
    await fetchUser(access_token);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
