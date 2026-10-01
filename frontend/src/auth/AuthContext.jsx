import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi } from "../api/resources";
import { setTokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const stored = localStorage.getItem("srip_tokens");
    if (!stored) {
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setTokens(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  async function login(username, password) {
    const tokens = await authApi.login(username, password);
    setTokens(tokens);
    const me = await authApi.me();
    setUser(me);
    return me;
  }

  async function register(payload) {
    const data = await authApi.register(payload);
    setTokens({ access: data.access, refresh: data.refresh });
    setUser(data.user);
    return data.user;
  }

  function logout() {
    setTokens(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh: loadMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
