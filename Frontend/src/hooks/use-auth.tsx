"use client";

import { createContext, useContext } from "react";
import { signIn, signOut, useSession } from "@/lib/auth-client";

interface User {
  id: string;
  username: string;
  avatar: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, isPending } = useSession();
  // const session: any = { user: null };
  // const isPending = false;

  const user: User | null = session?.user
    ? {
        id: session.user.id,
        username: session.user.name || session.user.email.split("@")[0],
        avatar: session.user.image || "",
        email: session.user.email,
      }
    : null;

  const login = async () => {
    await signIn.social({
      provider: "discord",
      callbackURL: "/dashboard", // Adjust as needed
    });
  };

  const logoutFn = async () => {
    await signOut();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading: isPending,
        login,
        logout: logoutFn,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
