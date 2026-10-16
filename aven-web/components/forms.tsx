"use client";

import { useActionState, useEffect, useRef } from "react";
import { useFormStatus } from "react-dom";
import { createPracticeAction, createUserAction, loginAction, registerAction } from "@/app/actions";
import type { FormState } from "@/lib/types";

const initial: FormState = {};

const inputClass =
  "mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm " +
  "focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600";

function SubmitButton({ children }: { children: React.ReactNode }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
    >
      {pending ? "Please wait…" : children}
    </button>
  );
}

function Field({
  label,
  name,
  type = "text",
  autoComplete,
  hint,
  required = true,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  hint?: string;
  required?: boolean;
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input
        name={name}
        type={type}
        autoComplete={autoComplete}
        required={required}
        className={inputClass}
      />
      {hint && <span className="mt-1 block text-xs font-normal text-slate-500">{hint}</span>}
    </label>
  );
}

function Message({ state }: { state: FormState }) {
  if (state.error)
    return (
      <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
        {state.error}
      </p>
    );
  return null;
}

/** Clears the form after a successful submit. */
function useResetOnSuccess(state: FormState) {
  const ref = useRef<HTMLFormElement>(null);
  useEffect(() => {
    if (state.ok) ref.current?.reset();
  }, [state]);
  return ref;
}

export function LoginForm() {
  const [state, action] = useActionState(loginAction, initial);
  return (
    <form action={action} className="space-y-4">
      <Field label="Email" name="email" type="email" autoComplete="username" />
      <Field label="Password" name="password" type="password" autoComplete="current-password" />
      <Message state={state} />
      <SubmitButton>Sign in</SubmitButton>
    </form>
  );
}

export function RegisterForm() {
  const [state, action] = useActionState(registerAction, initial);
  return (
    <form action={action} className="space-y-4">
      <Field label="Organization name" name="organization_name" autoComplete="organization" />
      <Field label="Your name" name="admin_name" autoComplete="name" />
      <Field label="Email" name="email" type="email" autoComplete="username" />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        hint="At least 12 characters."
      />
      <Message state={state} />
      <SubmitButton>Create organization</SubmitButton>
    </form>
  );
}

export function PracticeForm() {
  const [state, action] = useActionState(createPracticeAction, initial);
  const ref = useResetOnSuccess(state);
  return (
    <form ref={ref} action={action} className="space-y-3">
      <Field label="Practice name" name="name" />
      <Field label="Specialty (optional)" name="specialty" required={false} />
      <Message state={state} />
      <SubmitButton>Add practice</SubmitButton>
    </form>
  );
}

export function UserForm() {
  const [state, action] = useActionState(createUserAction, initial);
  const ref = useResetOnSuccess(state);
  return (
    <form ref={ref} action={action} className="space-y-3">
      <Field label="Full name" name="full_name" />
      <Field label="Email" name="email" type="email" />
      <Field
        label="Temporary password"
        name="password"
        type="password"
        autoComplete="new-password"
        hint="At least 12 characters. Share it securely."
      />
      <label className="block text-sm font-medium text-slate-700">
        Role
        <select name="role" defaultValue="biller" className={inputClass}>
          <option value="biller">Biller: view and work cases</option>
          <option value="manager">Manager: also add practices, see users</option>
          <option value="admin">Admin: also manage users, see audit log</option>
        </select>
      </label>
      <Message state={state} />
      <SubmitButton>Add user</SubmitButton>
    </form>
  );
}
