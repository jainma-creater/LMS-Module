import Link from "next/link";
import { Suspense } from "react";

import AdminNav from "./admin-nav";

function AdminNavFallback() {
  return (
    <nav aria-label="Admin sections" className="flex flex-col gap-1" aria-hidden="true">
      {["Overview", "AI Studio", "Learners", "Groups", "Assignments", "Group Assignments"].map(
        (label) => (
          <span key={label} className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-500">
            {label}
          </span>
        ),
      )}
    </nav>
  );
}

export default function ManageLayout({ children }: LayoutProps<"/manage">) {
  return (
    <div className="border-t border-[var(--border)] bg-[var(--surface-muted)]">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-xl border border-[var(--border)] bg-white p-4 shadow-sm">
            <p className="px-1 text-xs font-semibold uppercase tracking-wide text-[var(--brand)]">
              Admin console
            </p>
            <div className="mt-3">
              <Suspense fallback={<AdminNavFallback />}>
                <AdminNav />
              </Suspense>
            </div>
            <div className="mt-4 border-t border-[var(--border)] pt-3">
              <Link
                href="/courses"
                className="block rounded-lg px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-[var(--surface-muted)]"
              >
                ← Back to learner view
              </Link>
            </div>
          </div>
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
