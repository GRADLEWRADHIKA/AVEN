import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { api, ApiError } from "./api";
import type { Me } from "./types";

const COOKIE = "aven_token";

export async function setSessionCookie(token: string, maxAgeSeconds: number): Promise<void> {
  (await cookies()).set(COOKIE, token, {
    httpOnly: true, // not readable by browser JavaScript
    sameSite: "lax",
    secure: process.env.COOKIE_SECURE === "true", // set COOKIE_SECURE=true behind HTTPS
    path: "/",
    maxAge: maxAgeSeconds,
  });
}

export async function clearSessionCookie(): Promise<void> {
  (await cookies()).delete(COOKIE);
}

export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE)?.value;
}

/** Returns the signed-in user, or null if there is no valid session. */
export async function getSessionOrNull(): Promise<{ token: string; me: Me } | null> {
  const token = await getToken();
  if (!token) return null;
  try {
    return { token, me: await api<Me>("/me", { token }) };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}

/** For protected pages: returns the session or sends the visitor to the login page. */
export async function requireSession(): Promise<{ token: string; me: Me }> {
  const session = await getSessionOrNull();
  if (!session) redirect("/login");
  return session;
}
