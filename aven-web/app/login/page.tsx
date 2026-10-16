import Link from "next/link";
import { redirect } from "next/navigation";
import { LoginForm } from "@/components/forms";
import { getSessionOrNull } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  if (await getSessionOrNull()) redirect("/dashboard");
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="text-2xl font-semibold">Sign in to AVEN</h1>
      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <LoginForm />
      </div>
      <p className="mt-4 text-sm text-slate-600">
        New billing company or practice?{" "}
        <Link href="/register" className="font-medium text-teal-700 hover:underline">
          Create an organization
        </Link>
      </p>
    </main>
  );
}
