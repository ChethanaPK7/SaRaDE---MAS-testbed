import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

const client = axios.create({ baseURL: API_BASE });

function getTokens() {
  try {
    return JSON.parse(localStorage.getItem("srip_tokens") || "null");
  } catch {
    return null;
  }
}

export function setTokens(tokens) {
  if (tokens) localStorage.setItem("srip_tokens", JSON.stringify(tokens));
  else localStorage.removeItem("srip_tokens");
}

client.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

let refreshing = null;

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      const tokens = getTokens();
      if (!tokens?.refresh) {
        setTokens(null);
        return Promise.reject(error);
      }
      original._retry = true;
      try {
        refreshing =
          refreshing ||
          axios
            .post(`${API_BASE}/auth/login/refresh/`, { refresh: tokens.refresh })
            .then((r) => {
              setTokens({ ...tokens, access: r.data.access });
              return r.data.access;
            })
            .finally(() => {
              refreshing = null;
            });
        const newAccess = await refreshing;
        original.headers.Authorization = `Bearer ${newAccess}`;
        return client(original);
      } catch (refreshError) {
        setTokens(null);
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default client;
