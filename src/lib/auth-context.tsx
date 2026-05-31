import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { setAuthToken } from "@/api/client";
import { auth as authApi, profile } from "@/api/client";

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
};

const AuthContext = createContext<AuthContextValue | null>(null);

function clearAuthState() {
  localStorage.removeItem("auth_token");
  setAuthToken(null);
}

export function getFirebaseErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    const msg = error.message;
    const match = msg.match(/\(auth\/([^)]+)\)/);
    if (match) {
      const code = match[1];
      const messages: Record<string, string> = {
        "user-not-found": "No account found with this email",
        "wrong-password": "Incorrect password",
        "invalid-credential": "Invalid email or password",
        "invalid-email": "Invalid email address",
        "email-already-in-use": "An account with this email already exists",
        "weak-password": "Password is too weak (min 6 characters)",
        "too-many-requests": "Too many attempts. Please try again later",
        "network-request-failed": "Network error. Please check your connection",
        "cancelled-popup-request": "Google sign-in was canceled before it completed",
        "popup-closed-by-user": "Google sign-in was closed before it completed",
        "popup-blocked": "Your browser blocked the Google sign-in popup",
        "account-exists-with-different-credential":
          "An account already exists with a different sign-in method",
      };
      return messages[code] || msg.replace("Firebase: ", "").replace(/\(auth\/[^)]+\)/g, "").trim();
    }
    return msg;
  }
  return "An unexpected error occurred";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isHandlingAuth = useRef(false);
  const isGoogleSignInInProgress = useRef(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (isHandlingAuth.current) return;

      if (firebaseUser) {
        try {
          const idToken = await firebaseUser.getIdToken();
          localStorage.setItem("auth_token", idToken);
          setAuthToken(idToken);
          setTokenState(idToken);
          const userData = await authApi.me();
          setUser(userData);
        } catch {
          clearAuthState();
          setTokenState(null);
          setUser(null);
        }
      } else {
        clearAuthState();
        setTokenState(null);
        setUser(null);
      }
      setIsLoading(false);
    });
    return unsubscribe;
  }, []);

  const login = async (email: string, password: string) => {
    isHandlingAuth.current = true;
    setIsLoading(true);
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      const idToken = await cred.user.getIdToken();
      localStorage.setItem("auth_token", idToken);
      setAuthToken(idToken);
      setTokenState(idToken);
      const userData = await authApi.me();
      setUser(userData);
    } finally {
      setIsLoading(false);
      isHandlingAuth.current = false;
    }
  };

  const register = async (email: string, password: string, full_name: string) => {
    isHandlingAuth.current = true;
    setIsLoading(true);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      const idToken = await cred.user.getIdToken();
      localStorage.setItem("auth_token", idToken);
      setAuthToken(idToken);
      setTokenState(idToken);
      const userData = await authApi.me();
      try {
        await profile.update({ full_name });
      } catch {
        // Profile endpoint may not exist yet; full_name will be captured during onboarding
      }
      setUser({ ...userData, full_name: full_name || userData.full_name });
    } finally {
      setIsLoading(false);
      isHandlingAuth.current = false;
    }
  };

  const signInWithGoogle = async () => {
    if (isGoogleSignInInProgress.current) {
      return;
    }

    isGoogleSignInInProgress.current = true;
    isHandlingAuth.current = true;
    setIsLoading(true);
    try {
      const provider = new GoogleAuthProvider();
      const cred = await signInWithPopup(auth, provider);
      const idToken = await cred.user.getIdToken();
      localStorage.setItem("auth_token", idToken);
      setAuthToken(idToken);
      setTokenState(idToken);
      const userData = await authApi.me();
      setUser(userData);
    } catch (error) {
      throw new Error(getFirebaseErrorMessage(error));
    } finally {
      setIsLoading(false);
      isHandlingAuth.current = false;
      isGoogleSignInInProgress.current = false;
    }
  };

  const logout = async () => {
    await signOut(auth);
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
        signInWithGoogle,
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
