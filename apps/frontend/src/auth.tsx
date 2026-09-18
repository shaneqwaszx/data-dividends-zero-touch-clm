import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { QueryClientProvider } from "@tanstack/react-query";

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
  const [authState, setAuthState] = useState<AuthState>({
    status: "loading",
    session: null,
    error: null,
  });

  const clearSession = useCallback(() => {
    clearSessionQueries(queryClient);
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
    setAuthState((state) => transitionAuthState(state, { type: "ANONYMOUS" }));
  }, [queryClient]);

  const acceptSession = useCallback((authenticated: AuthSession) => {
    clearSessionQueries(queryClient);
    configureAuthenticatedTransport({
      csrfToken: authenticated.csrf_token,
      onUnauthorized: clearSession,
    });
    setAuthState((state) => transitionAuthState(state, {
      type: "AUTHENTICATED",
      session: authenticated,
    }));
    prefetchSessionQueries(queryClient, authenticated.profile);
  }, [clearSession, queryClient]);

  useEffect(() => {
    let current = true;
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: clearSession });
    void fetchCurrentSession()
      .then((restored) => {
        if (!current) return;
        acceptSession(restored);
      })
      .catch(() => {
        if (current) clearSession();
      });
    return () => {
      current = false;
    };
  }, [acceptSession, clearSession]);

  const login = useCallback(async (userId: string, credential: string) => {
    setAuthState((state) => ({ ...state, error: null }));
    try {
      const authenticated = await requestLogin(userId, credential);
      acceptSession(authenticated);
    } catch (loginError) {
      const message = loginError instanceof ApiError
          ? loginError.message
          : "Sign-in is unavailable. Please try again.";
      setAuthState((state) => transitionAuthState(state, { type: "LOGIN_ERROR", message }));
      throw loginError;
    }
  }, [acceptSession]);

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
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    </QueryClientProvider>
  );
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
