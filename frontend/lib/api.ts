import type {
  AnalysisDetail,
  Product,
  TokenResponse,
  User,
} from "@/lib/types";

export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") || "http://localhost:8080";

const ACCESS_KEY = "pg.access";
const REFRESH_KEY = "pg.refresh";

export const tokenStore = {
  get access() {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    window.localStorage.setItem(ACCESS_KEY, access);
    window.localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let message = res.statusText || "Request failed";
  let code: string | undefined;
  try {
    const body = await res.json();
    if (body?.error) {
      message = body.error.message || message;
      code = body.error.code;
    } else if (typeof body?.detail === "string") {
      message = body.detail;
    }
  } catch {
    /* keep default */
  }
  return new ApiError(message, res.status, code);
}

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    tokenStore.clear();
    return false;
  }
  const data: TokenResponse = await res.json();
  tokenStore.set(data.access_token, data.refresh_token);
  return true;
}

type FetchOpts = RequestInit & { auth?: boolean; retry?: boolean };

export async function api<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const { auth = true, retry = true, headers, ...rest } = opts;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };
  if (auth && tokenStore.access) {
    finalHeaders.Authorization = `Bearer ${tokenStore.access}`;
  }

  const res = await fetch(`${BACKEND_URL}${path}`, { ...rest, headers: finalHeaders });

  if (res.status === 401 && auth && retry) {
    if (await refreshTokens()) {
      return api<T>(path, { ...opts, retry: false });
    }
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// -- auth ------------------------------------------------------------------
export const auth = {
  register: (name: string, email: string, password: string) =>
    api<TokenResponse>("/api/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ name, email, password }),
    }),
  login: (email: string, password: string) =>
    api<TokenResponse>("/api/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<User>("/api/auth/me"),
  logout: () => api<void>("/api/auth/logout", { method: "POST" }),
};

// -- domain --------------------------------------------------------------
export const products = {
  create: (input: { name: string; description: string; image_url?: string | null }) =>
    api<Product>("/api/products", { method: "POST", body: JSON.stringify(input) }),
};

export const analyses = {
  create: (product_id: string) =>
    api<{ id: string; status: string }>("/api/analyses", {
      method: "POST",
      body: JSON.stringify({ product_id }),
    }),
  get: (id: string) => api<AnalysisDetail>(`/api/analyses/${id}`),
  streamUrl: (id: string) =>
    `${BACKEND_URL}/api/analyses/${id}/stream?token=${encodeURIComponent(
      tokenStore.access || "",
    )}`,
};

export function mediaUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http")) return path;
  return `${BACKEND_URL}${path}`;
}
