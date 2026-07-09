import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { setAuthToken } from "@/api/client";
import { auth as authApi } from "@/api/client";

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
  signInWithGoogle: () => Promise<void>;
  logout: () => void;
  sendPasswordReset: (email: string) => Promise<void>;
  sendVerification: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function saveToken(token: string) {
  localStorage.setItem("auth_token", token);
  setAuthToken(token);
}

function clearToken() {
  localStorage.removeItem("auth_token");
  setAuthToken(null);
}

export function getFirebaseErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message || "Authentication failed. Please try again.";
  return "An unexpected error occurred";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("auth_token");
    if (!stored) {
      setIsLoading(false);
      return;
    }
    setAuthToken(stored);
    setTokenState(stored);
    authApi.me()
      .then((userData) => setUser(userData))
      .catch(() => clearToken())
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(email, password);
      saveToken(res.access_token);
      setTokenState(res.access_token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, full_name: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.register(email, password, full_name);
      saveToken(res.access_token);
      setTokenState(res.access_token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearToken();
    setTokenState(null);
    setUser(null);
  };

  // Stubs kept so existing call sites don't break
  const signInWithGoogle = async () => {
    throw new Error("Google sign-in unavailable — use email/password");
  };
  const sendPasswordReset = async (_email: string) => {
    throw new Error("Password reset unavailable in local auth mode");
  };
  const sendVerification = async () => {};

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        signInWithGoogle,
        logout,
        sendPasswordReset,
        sendVerification,
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
