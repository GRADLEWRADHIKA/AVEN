"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { api, ApiError, errorMessage } from "@/lib/api";
import { clearSessionCookie, getToken, setSessionCookie } from "@/lib/session";
import type { FormState, Practice, Role, TokenResponse, User } from "@/lib/types";

const text = (formData: FormData, key: string) => String(formData.get(key) ?? "").trim();

async function authToken(): Promise<string> {
  const token = await getToken();
  if (!token) redirect("/login");
  return token;
}

/** Runs an API call for a signed-in user; an expired session sends them back to login. */
async function withSession(run: (token: string) => Promise<void>): Promise<FormState> {
  const token = await authToken();
  try {
    await run(token);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/login");
    return { error: errorMessage(e) };
  }
  revalidatePath("/dashboard");
  return { ok: true };
}

// ---- sign in / sign up / sign out -----------------------------------------------------------

export async function loginAction(_prev: FormState, formData: FormData): Promise<FormState> {
  try {
    const t = await api<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email: text(formData, "email"), password: String(formData.get("password") ?? "") },
    });
    await setSessionCookie(t.access_token, t.expires_in);
  } catch (e) {
    return { error: errorMessage(e) };
  }
  redirect("/dashboard");
}

export async function registerAction(_prev: FormState, formData: FormData): Promise<FormState> {
  try {
    const t = await api<TokenResponse>("/auth/register-organization", {
      method: "POST",
      body: {
        organization_name: text(formData, "organization_name"),
        admin_name: text(formData, "admin_name"),
        email: text(formData, "email"),
        password: String(formData.get("password") ?? ""),
      },
    });
    await setSessionCookie(t.access_token, t.expires_in);
  } catch (e) {
    return { error: errorMessage(e) };
  }
  redirect("/dashboard");
}

export async function logoutAction(): Promise<void> {
  await clearSessionCookie();
  redirect("/login");
}

// ---- dashboard actions ------------------------------------------------------------------------

export async function createPracticeAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  return withSession(async (token) => {
    await api<Practice>("/practices", {
      method: "POST",
      token,
      body: { name: text(formData, "name"), specialty: text(formData, "specialty") || null },
    });
  });
}

export async function createUserAction(_prev: FormState, formData: FormData): Promise<FormState> {
  return withSession(async (token) => {
    await api<User>("/users", {
      method: "POST",
      token,
      body: {
        email: text(formData, "email"),
        full_name: text(formData, "full_name"),
        password: String(formData.get("password") ?? ""),
        role: text(formData, "role") as Role,
      },
    });
  });
}

export async function setUserActiveAction(formData: FormData): Promise<void> {
  await withSession(async (token) => {
    await api<User>(`/users/${text(formData, "user_id")}`, {
      method: "PATCH",
      token,
      body: { is_active: text(formData, "active") === "true" },
    });
  });
}
