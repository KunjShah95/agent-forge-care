import { initializeApp, getApps } from "firebase/app";
import { getAnalytics, setAnalyticsCollectionEnabled, isSupported, logEvent } from "firebase/analytics";
import { getAuth, connectAuthEmulator } from "firebase/auth";

// GDPR / Privacy Consent Management
// Analytics are NOT initialized by default. Consent must be given first.
const CONSENT_KEY = "analytics_consent_granted";

export function hasAnalyticsConsent(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(CONSENT_KEY) === "true";
}

export function grantAnalyticsConsent(): void {
  localStorage.setItem(CONSENT_KEY, "true");
  initAnalytics();
}

export function revokeAnalyticsConsent(): void {
  localStorage.removeItem(CONSENT_KEY);
  if (analyticsInstance) {
    setAnalyticsCollectionEnabled(analyticsInstance, false);
  }
}

export function clearAllStoredData(): void {
  // GDPR right to erasure — clear all local data
  localStorage.removeItem("auth_token");
  localStorage.removeItem(CONSENT_KEY);
  // Analytics data cannot be erased client-side; user must delete through Google
}

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

const requiredFirebaseKeys = [
  "apiKey",
  "authDomain",
  "projectId",
  "storageBucket",
  "messagingSenderId",
  "appId",
] as const;

const missingFirebaseKeys = requiredFirebaseKeys.filter(
  (key) => !firebaseConfig[key],
);

export const isFirebaseConfigured = missingFirebaseKeys.length === 0;
export const firebaseConfigError = isFirebaseConfigured
  ? null
  : `Missing Firebase env vars: ${missingFirebaseKeys.join(", ")}`;

// Only initialize Firebase if fully configured — prevents noise from bad/missing API keys
const app = isFirebaseConfigured
  ? getApps().length === 0
    ? initializeApp(firebaseConfig)
    : getApps()[0]
  : null;

export const auth = app ? getAuth(app) : ({} as ReturnType<typeof getAuth>);

// Analytics is lazily initialized only after user consent
let analyticsInstance: ReturnType<typeof getAnalytics> | null = null;

/**
 * Get the analytics instance if consent has been granted and analytics is supported.
 * Returns null if not yet initialized. Consumers should check for null before using.
 */
export function getAnalyticsInstance(): ReturnType<typeof getAnalytics> | null {
  return analyticsInstance;
}

export async function initAnalytics(): Promise<void> {
  if (typeof window === "undefined") return;
  if (analyticsInstance) return;
  if (!import.meta.env.VITE_FIREBASE_MEASUREMENT_ID) return;
  
  try {
    if (!app) return;
    const supported = await isSupported();
    if (!supported) return;
    analyticsInstance = getAnalytics(app);
  } catch {
    // Analytics not available in this environment
  }
}

/**
 * Log an analytics event if analytics is initialized and consent has been granted.
 * Safe to call even if analytics is not initialized — it will be a no-op.
 */
export function logAnalyticsEvent(eventName: string, eventParams?: Record<string, unknown>): void {
  if (!analyticsInstance) return;
  try {
    logEvent(analyticsInstance, eventName, eventParams);
  } catch {
    // Analytics event logging failed silently
  }
}

// Auto-init analytics only if consent was previously granted
if (hasAnalyticsConsent()) {
  initAnalytics();
}

if (app && import.meta.env.VITE_FIREBASE_EMULATOR_HOST) {
  connectAuthEmulator(auth, import.meta.env.VITE_FIREBASE_EMULATOR_HOST);
}
