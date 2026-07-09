import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Must mock before imports
const mockNavigate = vi.fn();
const mockLogin = vi.fn();
const mockSignInWithGoogle = vi.fn();
const mockSendPasswordReset = vi.fn();

vi.mock("@/lib/auth-context", () => ({
  useAuthContext: vi.fn(),
  getFirebaseErrorMessage: vi.fn((err: unknown) => {
    const m = err instanceof Error ? err.message : "Sign-in failed";
    return m;
  }),
}));

// Use mutable objects so tests can change firebase/API config state at runtime
// vi.hoisted() runs before vi.mock() factory calls, so the object is initialized
const { firebaseMock, clientApiMock } = vi.hoisted(() => ({
  firebaseMock: { isFirebaseConfigured: true, firebaseConfigError: null },
  clientApiMock: { apiConfigError: null },
}));

vi.mock("@/lib/firebase", () => firebaseMock);
vi.mock("@/api/client", () => clientApiMock);

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import Login from "@/pages/Login";
import * as authCtx from "@/lib/auth-context";

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

function mockAuthContext(overrides: Record<string, unknown> = {}) {
  vi.mocked(authCtx.useAuthContext).mockReturnValue({
    login: mockLogin,
    signInWithGoogle: mockSignInWithGoogle,
    sendPasswordReset: mockSendPasswordReset,
    isLoading: false,
    isAuthenticated: false,
    user: null,
    token: null,
    logout: vi.fn(),
    register: vi.fn(),
    sendVerification: vi.fn(),
    ...overrides,
  } as never);
}

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthContext();
    // Restore mutable mock defaults
    firebaseMock.isFirebaseConfigured = true;
    firebaseMock.firebaseConfigError = null;
    clientApiMock.apiConfigError = null;
  });

  it("renders the welcome heading", () => {
    renderLogin();
    expect(screen.getByText("Welcome back")).toBeDefined();
  });

  it("renders the sign-in subtitle", () => {
    renderLogin();
    expect(screen.getByText("Sign in to your career OS")).toBeDefined();
  });

  it("renders the email input", () => {
    renderLogin();
    expect(screen.getByLabelText("Email")).toBeDefined();
  });

  it("renders the password input", () => {
    renderLogin();
    expect(screen.getByLabelText("Password")).toBeDefined();
  });

  it("renders the 'Continue with Google' button", () => {
    renderLogin();
    expect(screen.getByText("Continue with Google")).toBeDefined();
  });

  it("renders the 'Sign in' submit button", () => {
    renderLogin();
    expect(screen.getByText("Sign in")).toBeDefined();
  });

  it("renders the register link", () => {
    renderLogin();
    expect(screen.getByText("Create one")).toBeDefined();
    expect(screen.getByText("Don't have an account?")).toBeDefined();
  });

  it("renders 'Forgot password?' link", () => {
    renderLogin();
    expect(screen.getByText("Forgot password?")).toBeDefined();
  });

  it("renders the AgentForge logo", () => {
    renderLogin();
    expect(screen.getByText("AgentForge Career OS")).toBeDefined();
  });

  it("disables Google button while submitting", () => {
    mockAuthContext({ isLoading: true });
    renderLogin();
    const googleBtn = screen.getByText("Continue with Google").closest("button");
    expect(googleBtn?.disabled).toBe(true);
  });

  it("disables submit button when Firebase is not configured", () => {
    firebaseMock.isFirebaseConfigured = false;

    renderLogin();
    const submitBtn = screen.getByText("Sign in").closest("button");
    expect(submitBtn?.disabled).toBe(true);
  });

  it("hides config error when firebase is configured", () => {
    // firebaseMock already has isFirebaseConfigured: true, firebaseConfigError: null
    renderLogin();
    expect(screen.queryByText("Missing Firebase vars")).toBeNull();
  });

  it("calls login on form submit with credentials", async () => {
    mockLogin.mockResolvedValueOnce(undefined);
    renderLogin();

    const emailInput = screen.getByLabelText("Email");
    const passwordInput = screen.getByLabelText("Password");

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    fireEvent.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("navigates to /app on successful login", async () => {
    mockLogin.mockResolvedValueOnce(undefined);
    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/app");
    });
  });

  it("displays error message on login failure", async () => {
    mockLogin.mockRejectedValueOnce(new Error("Invalid credentials"));
    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeDefined();
    });
  });

  it("calls signInWithGoogle when Google button is clicked", async () => {
    mockSignInWithGoogle.mockResolvedValueOnce(undefined);
    renderLogin();

    fireEvent.click(screen.getByText("Continue with Google"));

    await waitFor(() => {
      expect(mockSignInWithGoogle).toHaveBeenCalled();
    });
  });

  it("navigates to /app on successful Google sign-in", async () => {
    mockSignInWithGoogle.mockResolvedValueOnce(undefined);
    renderLogin();

    fireEvent.click(screen.getByText("Continue with Google"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/app");
    });
  });

  it("shows error toast on Google sign-in failure", async () => {
    mockSignInWithGoogle.mockRejectedValueOnce(new Error("Popup blocked"));
    renderLogin();

    fireEvent.click(screen.getByText("Continue with Google"));

    const { toast } = await import("sonner");
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it("shows error when forgot password is clicked without email", async () => {
    renderLogin();
    fireEvent.click(screen.getByText("Forgot password?"));

    const { toast } = await import("sonner");
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Please enter your email address first.");
    });
  });

  it("calls sendPasswordReset with email when forgot password is clicked with email", async () => {
    mockSendPasswordReset.mockResolvedValueOnce(undefined);
    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.click(screen.getByText("Forgot password?"));

    await waitFor(() => {
      expect(mockSendPasswordReset).toHaveBeenCalledWith("user@example.com");
    });
  });

  it("shows success toast after password reset email is sent", async () => {
    mockSendPasswordReset.mockResolvedValueOnce(undefined);
    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.click(screen.getByText("Forgot password?"));

    const { toast } = await import("sonner");
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Password reset email sent!");
    });
  });

  it("shows loading spinner on submit button when submitting", async () => {
    // Keep the promise pending
    mockLogin.mockReturnValue(new Promise(() => {}));
    renderLogin();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pass" } });
    fireEvent.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(screen.getByText("Signing in...")).toBeDefined();
    });
  });

  it("renders the or divider", () => {
    renderLogin();
    expect(screen.getByText("or")).toBeDefined();
  });
});
