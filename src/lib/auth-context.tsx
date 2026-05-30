import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { auth, setAuthToken } from "@/api/client";

type User = {
  id: string;
  email: string;
  full_name: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    if (storedToken) {
      setAuthToken(storedToken);
      setTokenState(storedToken);
      auth.me()
        .then((user) => setUser(user))
        .catch(() => {
          localStorage.removeItem("auth_token");
          setAuthToken(null);
          setTokenState(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const res = await auth.login({ email, password });
    localStorage.setItem("auth_token", res.access_token);
    setAuthToken(res.access_token);
    setTokenState(res.access_token);
    const userData = await auth.me();
    setUser(userData);
  };

  const register = async (email: string, password: string, full_name: string) => {
    const res = await auth.register({ email, password, full_name });
    localStorage.setItem("auth_token", res.access_token);
    setAuthToken(res.access_token);
    setTokenState(res.access_token);
    const userData = await auth.me();
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setAuthToken(null);
    setTokenState(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
