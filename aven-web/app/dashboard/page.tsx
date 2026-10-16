import { logoutAction, setUserActiveAction } from "@/app/actions";
import { PracticeForm, UserForm } from "@/components/forms";
import { api } from "@/lib/api";
import { requireSession } from "@/lib/session";
import { ROLE_RANK, type AuditEntry, type Practice, type User } from "@/lib/types";

export const dynamic = "force-dynamic";

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-slate-500">{children}</p>;
}

export default async function DashboardPage() {
  const { token, me } = await requireSession();
  const rank = ROLE_RANK[me.user.role];
  const canManage = rank >= ROLE_RANK.manager;
  const isAdmin = rank >= ROLE_RANK.admin;

  const [practices, users, audit] = await Promise.all([
    api<Practice[]>("/practices", { token }),
    canManage ? api<User[]>("/users", { token }) : Promise.resolve([] as User[]),
    isAdmin
      ? api<AuditEntry[]>("/audit-logs?limit=10", { token })
      : Promise.resolve([] as AuditEntry[]),
  ]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{me.organization.name}</h1>
          <p className="text-sm text-slate-600">
            Signed in as {me.user.full_name} ({me.user.email}) ·{" "}
            <span className="rounded bg-teal-50 px-1.5 py-0.5 text-xs font-medium text-teal-800">
              {me.user.role}
            </span>
          </p>
        </div>
        <form action={logoutAction}>
          <button className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50">
            Sign out
          </button>
        </form>
      </header>

      <div className="mt-6 grid gap-6 md:grid-cols-3">
        <div className="space-y-6 md:col-span-2">
          <Card title={`Practices (${practices.length})`}>
            {practices.length === 0 ? (
              <Empty>No practices yet.{canManage && " Add the first one."}</Empty>
            ) : (
              <ul className="divide-y divide-slate-100">
                {practices.map((p) => (
                  <li key={p.id} className="flex justify-between py-2 text-sm">
                    <span className="font-medium">{p.name}</span>
                    <span className="text-slate-500">{p.specialty ?? "—"}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {canManage && (
            <Card title={`Users (${users.length})`}>
              <ul className="divide-y divide-slate-100">
                {users.map((u) => (
                  <li key={u.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <div>
                      <div
                        className={
                          u.is_active ? "font-medium" : "font-medium text-slate-400 line-through"
                        }
                      >
                        {u.full_name}
                      </div>
                      <div className="text-slate-500">
                        {u.email} · {u.role}
                        {!u.is_active && " · deactivated"}
                      </div>
                    </div>
                    {isAdmin && u.id !== me.user.id && (
                      <form action={setUserActiveAction}>
                        <input type="hidden" name="user_id" value={u.id} />
                        <input type="hidden" name="active" value={String(!u.is_active)} />
                        <button className="rounded-md border border-slate-300 px-2.5 py-1 text-xs hover:bg-slate-50">
                          {u.is_active ? "Deactivate" : "Reactivate"}
                        </button>
                      </form>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {isAdmin && (
            <Card title="Recent activity (audit log)">
              {audit.length === 0 ? (
                <Empty>Nothing recorded yet.</Empty>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {audit.map((e) => (
                    <li key={e.id} className="flex justify-between py-2 text-sm">
                      <span className="font-mono text-xs">{e.action}</span>
                      <span className="text-slate-500">{formatDate(e.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
        </div>

        <div className="space-y-6">
          {canManage && (
            <Card title="Add a practice">
              <PracticeForm />
            </Card>
          )}
          {isAdmin && (
            <Card title="Add a user">
              <UserForm />
            </Card>
          )}
          {!canManage && (
            <Card title="Your access">
              <Empty>
                You can view practices and work cases. Ask a manager or admin if you need to add
                practices or users.
              </Empty>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
