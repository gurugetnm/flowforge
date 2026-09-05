"use client";

import { createContext, useCallback, useContext, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api";
import { authApi, type Credentials, type RegistrationDetails } from "@/lib/api/auth";
import { queryKeys } from "@/lib/queries";
import type { User } from "@/lib/types";

interface SessionContextValue {
  user: User | null;
  isLoading: boolean;
  signIn: (credentials: Credentials) => Promise<User>;
  signUp: (details: RegistrationDetails) => Promise<User>;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.session,
    queryFn: authApi.me,
    // A signed-out visitor is an expected outcome, not an error to retry.
    retry: false,
    staleTime: 5 * 60_000,
  });

  const setSession = useCallback(
    (user: User) => {
      queryClient.setQueryData(queryKeys.session, user);
      return user;
    },
    [queryClient],
  );

  const signIn = useMutation({ mutationFn: authApi.login, onSuccess: setSession }).mutateAsync;
  const signUp = useMutation({ mutationFn: authApi.register, onSuccess: setSession }).mutateAsync;

  const signOutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      // Everything cached belongs to the account that just signed out.
      queryClient.clear();
    },
  });

  const value = useMemo<SessionContextValue>(
    () => ({
      user: data ?? null,
      isLoading,
      signIn,
      signUp,
      signOut: async () => {
        await signOutMutation.mutateAsync();
      },
    }),
    [data, isLoading, signIn, signUp, signOutMutation],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside a SessionProvider");
  return context;
}

/** True when a query failed only because the visitor is not signed in. */
export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.isUnauthorized;
}
