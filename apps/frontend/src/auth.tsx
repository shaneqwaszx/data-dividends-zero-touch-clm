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
  configureAuthenticatedTransport,
  fetchCurrentSession,
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
}

export type AuthTransition =
  | { type: "AUTHENTICATED"; session: AuthSession }
  | { type: "ANONYMOUS" }
  | { type: "LOGIN_ERROR"; message: string };

export function transitionAuthState(state: AuthState, action: AuthTransition): AuthState {
  if (action.type === "AUTHENTICATED") {
    return { status: "authenticated", session: action.session, error: null };
  }
  if (action.type === "LOGIN_ERROR") {
    return { ...state, error: action.message };
  }
  return { status: "anonymous", session: null, error: null };
}

interface AuthContextValue {
  status: AuthStatus;
  session: AuthSession | null;
  error: string | null;
  login: (userId: string, credential: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createSessionQueryClient);
  const navigate = useNavigate();
  const location = useLocation();
  const pendingInteractiveSession = useRef<AuthSession | null>(null);
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const [sessionGeneration, setSessionGeneration] = useState(0);
  const [authState, setAuthState] = useState<AuthState>({
    status: "loading",
    session: null,
    error: null,
  });

  const clearSession = useCallback((resetRoute = true) => {
    pendingInteractiveSession.current = null;
    clearSessionQueries(queryClient);
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
    setAuthState((state) => transitionAuthState(state, { type: "ANONYMOUS" }));
    if (resetRoute) navigateRef.current("/", { replace: true });
  }, [queryClient]);

  const acceptSession = useCallback((authenticated: AuthSession) => {
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
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ ...authState, login, logout }),
    [authState, login, logout],
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
