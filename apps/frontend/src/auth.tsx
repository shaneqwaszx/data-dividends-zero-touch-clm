import {
  createContext,
  Fragment,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router";

import {
  ApiError,
  changeOwnPassword as requestPasswordChange,
  configureAuthenticatedTransport,
  fetchCurrentSession,
  fetchSessionEndReason,
  type SessionEndReason,
  login as requestLogin,
  logout as requestLogout,
} from "./api";
import type { AuthSession } from "./types";
import { prefetchSessionQueries } from "./caseQueries";
import { clearSessionQueries, createSessionQueryClient } from "./queryClient";

type AuthStatus = "loading" | "anonymous" | "authenticated";
export interface AuthState {
  status: AuthStatus;
  session: AuthSession | null;
  error: string | null;
  // D-098: why an earlier session ended (shown on the sign-in page); never set while signed in.
  notice?: string;
}

export type AuthTransition =
  | { type: "AUTHENTICATED"; session: AuthSession }
  | { type: "ANONYMOUS" }
  | { type: "SESSION_ENDED"; notice: string }
  | { type: "LOGIN_ERROR"; message: string };

const BACKGROUND_WORK = " Work that runs on the server, such as an AI model qualification, keeps running: sign in again to follow it.";
export const SESSION_END_TEXT: Record<SessionEndReason, string> = {
  SESSION_EXPIRED: "Your session ended because it reached its 8-hour limit." + BACKGROUND_WORK,
  SESSION_REPLACED: "Your session ended because this account signed in somewhere else (another browser or device). Each account has one session at a time." + BACKGROUND_WORK,
  SESSION_REVOKED: "Your session ended because your account or team access changed." + BACKGROUND_WORK,
  SIGNED_OUT: "This session was signed out." + BACKGROUND_WORK,
  SESSION_UNKNOWN: "Your session is no longer recognised, usually because the onboarding service was restarted." + BACKGROUND_WORK,
};

export function transitionAuthState(state: AuthState, action: AuthTransition): AuthState {
  if (action.type === "AUTHENTICATED") {
    return { status: "authenticated", session: action.session, error: null };
  }
  if (action.type === "LOGIN_ERROR") {
    return { ...state, error: action.message };
  }
  if (action.type === "SESSION_ENDED") {
    // Only an anonymous page explains; a newer sign-in is never overwritten.
    return state.status === "anonymous" ? { ...state, notice: action.notice } : state;
  }
  return { status: "anonymous", session: null, error: null };
}

interface AuthContextValue {
  status: AuthStatus;
  session: AuthSession | null;
  error: string | null;
  notice: string | null;
  login: (userId: string, credential: string) => Promise<void>;
  logout: () => Promise<void>;
  changeOwnPassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createSessionQueryClient);
  const navigate = useNavigate();
  const location = useLocation();
  const activeSession = useRef<AuthSession | null>(null);
  const pendingInteractiveSession = useRef<AuthSession | null>(null);
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const [sessionGeneration, setSessionGeneration] = useState(0);
  const [authState, setAuthState] = useState<AuthState>({
    status: "loading",
    session: null,
    error: null,
  });

  const clearSession = useCallback((resetRoute = true, explain = true) => {
    activeSession.current = null;
    pendingInteractiveSession.current = null;
    clearSessionQueries(queryClient);
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
    setAuthState((state) => transitionAuthState(state, { type: "ANONYMOUS" }));
    if (resetRoute) navigateRef.current("/", { replace: true });
    if (!explain) return;
    // D-098: ask the backend once why the session ended (nothing is retried or extended).
    void fetchSessionEndReason().then((reason) => {
      if (reason) {
        setAuthState((state) => transitionAuthState(state, {
          type: "SESSION_ENDED",
          notice: SESSION_END_TEXT[reason],
        }));
      }
    });
  }, [queryClient]);

  const acceptSession = useCallback((authenticated: AuthSession) => {
    activeSession.current = authenticated;
    clearSessionQueries(queryClient);
    configureAuthenticatedTransport({
      csrfToken: authenticated.csrf_token,
      onUnauthorized: clearSession,
    });
    setSessionGeneration((generation) => generation + 1);
    setAuthState((state) => transitionAuthState(state, {
      type: "AUTHENTICATED",
      session: authenticated,
    }));
    prefetchSessionQueries(queryClient, authenticated.profile);
  }, [clearSession, queryClient]);

  useEffect(() => {
    const pending = pendingInteractiveSession.current;
    if (!pending || location.pathname !== "/" || location.search || location.hash) return;
    // Declarative Router navigation is a transition: accept the identity only after root commits.
    pendingInteractiveSession.current = null;
    acceptSession(pending);
  }, [acceptSession, authState.status, location.pathname, location.search, location.hash]);

  useEffect(() => {
    let current = true;
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: () => clearSession(false) });
    void fetchCurrentSession()
      .then((restored) => {
        if (!current) return;
        acceptSession(restored);
      })
      .catch(() => {
        if (current) clearSession(false);
      });
    return () => {
      current = false;
    };
  }, [acceptSession, clearSession]);

  const login = useCallback(async (userId: string, credential: string) => {
    setAuthState((state) => ({ ...state, error: null }));
    try {
      const authenticated = await requestLogin(userId, credential);
      activeSession.current = null;
      clearSessionQueries(queryClient);
      configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
      pendingInteractiveSession.current = authenticated;
      setAuthState({ status: "loading", session: null, error: null });
      navigateRef.current("/", { replace: true });
    } catch (loginError) {
      const message = loginError instanceof ApiError
          ? loginError.message
          : "Sign-in is unavailable. Please try again.";
      setAuthState((state) => transitionAuthState(state, { type: "LOGIN_ERROR", message }));
      throw loginError;
    }
  }, [queryClient]);

  const logout = useCallback(async () => {
    try {
      await requestLogout();
    } finally {
      clearSession(true, false);
    }
  }, [clearSession]);

  const changeOwnPassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const session = activeSession.current;
    await requestPasswordChange(currentPassword, newPassword);
    if (session && activeSession.current === session) {
      clearSession(true, false);
      setAuthState((state) => transitionAuthState(state, {
        type: "SESSION_ENDED",
        notice: "Password changed. Sign in with your new password.",
      }));
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ ...authState, notice: authState.notice ?? null, login, logout, changeOwnPassword }),
    [authState, login, logout, changeOwnPassword],
  );
  return (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={value}>
        <Fragment key={sessionGeneration}>{children}</Fragment>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
