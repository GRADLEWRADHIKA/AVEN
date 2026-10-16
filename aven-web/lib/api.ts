// Server-side client for the AVEN API. Only used from server components and server actions,
// so the access token never reaches client-side JavaScript.

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

interface Options {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  token?: string;
  body?: unknown;
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      // FastAPI validation errors: [{ loc: ["body", "password"], msg: "..." }]
      return detail
        .map((d: { loc?: unknown[]; msg?: string }) => {
          const field = d.loc?.[d.loc.length - 1];
          return field ? `${String(field).replaceAll("_", " ")}: ${d.msg}` : String(d.msg);
        })
        .join("; ");
    }
  } catch {
    // fall through
  }
  return `Request failed (${res.status})`;
}

export async function api<T>(
  path: string,
  { method = "GET", token, body }: Options = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, "Cannot reach the AVEN API. Is it running?");
  }

  if (!res.ok) throw new ApiError(res.status, await readError(res));
  return (await res.json()) as T;
}

export function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : "Something went wrong. Please try again.";
}
