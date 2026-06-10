import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  sendPasswordResetEmail,
  sendEmailVerification,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { firebaseConfigError, isFirebaseConfigured } from "@/lib/firebase";
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
  sendPasswordReset: (email: string) => Promise<void>;
  sendVerification: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function clearAuthState() {
  localStorage.removeItem("auth_token");
  setAuthToken(null);
}

export function getFirebaseErrorMessage(error: unknown): string {
  if (!isFirebaseConfigured) {
    return firebaseConfigError || "Firebase is not configured for this environment";
  }

  if (error instanceof Error) {
    const msg = (error.message || "").trim();

    if (!msg) {
      return "Sign-in failed. Please try again or disable browser extensions that may interfere with the login page.";
    }

    if (msg.toLowerCase().includes("token required")) {
      return "A browser extension or sign-in session interrupted the flow. Try disabling extensions, then sign in again.";
    }

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
      const cleaned = msg.replace("Firebase: ", "").replace(/\(auth\/[^)]+\)/g, "").trim();
      return messages[code] || cleaned || "Sign-in failed. Please try again.";
    }
    return msg || "Sign-in failed. Please try again.";
  }
  return "An unexpected error occurred";
}

function assertFirebaseConfigured() {
  if (!isFirebaseConfigured) {
    throw new Error(firebaseConfigError || "Firebase is not configured for this environment");
  }
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

          // Try to load full user profile from backend. If the backend is
          // unavailable, fall back to a minimal user object derived from
          // the Firebase user so the frontend remains usable.
          try {
            const userData = await authApi.me();
            setUser(userData);
          } catch (err) {
            // Backend unavailable or returned error — fallback to minimal user
            setUser({ id: firebaseUser.uid, email: firebaseUser.email || "", full_name: firebaseUser.displayName || "" });
          }
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
    assertFirebaseConfigured();
    isHandlingAuth.current = true;
    setIsLoading(true);
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      const idToken = await cred.user.getIdToken();
      localStorage.setItem("auth_token", idToken);
      setAuthToken(idToken);
      setTokenState(idToken);
      try {
        const userData = await authApi.me();
        setUser(userData);
      } catch {
        // If backend /auth/me fails, still treat the user as authenticated
        // using Firebase-provided identity to avoid redirect loops.
        setUser({ id: cred.user.uid, email: cred.user.email || "", full_name: cred.user.displayName || "" });
      }
    } finally {
      setIsLoading(false);
      isHandlingAuth.current = false;
    }
  };

  const register = async (email: string, password: string, full_name: string) => {
    assertFirebaseConfigured();
    isHandlingAuth.current = true;
    setIsLoading(true);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      try {
        await sendEmailVerification(cred.user);
      } catch (e) {
        console.error("Error sending verification email:", e);
      }
      const idToken = await cred.user.getIdToken();
      localStorage.setItem("auth_token", idToken);
      setAuthToken(idToken);
      setTokenState(idToken);
      try {
        const userData = await authApi.me();
        try {
          await profile.update({ full_name });
        } catch {
          // Profile endpoint may not exist yet; full_name will be captured during onboarding
        }
        setUser({ ...userData, full_name: full_name || userData.full_name });
      } catch {
        // Backend may not be available — fall back to Firebase-derived user
        setUser({ id: cred.user.uid, email: cred.user.email || "", full_name });
      }
    } finally {
      setIsLoading(false);
      isHandlingAuth.current = false;
    }
  };

  const sendPasswordReset = async (email: string) => {
    assertFirebaseConfigured();
    await sendPasswordResetEmail(auth, email);
  };

  const sendVerification = async () => {
    assertFirebaseConfigured();
    if (auth.currentUser) {
      await sendEmailVerification(auth.currentUser);
    }
  };

  const signInWithGoogle = async () => {
    assertFirebaseConfigured();
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
      try {
        const userData = await authApi.me();
        setUser(userData);
      } catch {
        setUser({ id: cred.user.uid, email: cred.user.email || "", full_name: cred.user.displayName || "" });
      }
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
