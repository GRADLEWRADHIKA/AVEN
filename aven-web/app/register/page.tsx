import Link from "next/link";
import { redirect } from "next/navigation";
import { RegisterForm } from "@/components/forms";
import { getSessionOrNull } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function RegisterPage() {
  if (await getSessionOrNull()) redirect("/dashboard");
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="text-2xl font-semibold">Create your organization</h1>
      <p className="mt-1 text-sm text-slate-600">You become its first admin.</p>
      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <RegisterForm />
      </div>
      <p className="mt-4 text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-teal-700 hover:underline">
          Sign in
        </Link>
      </p>
    </main>
  );
}
