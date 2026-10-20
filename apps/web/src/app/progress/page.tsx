import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { CompletionItem, MyLearningItem } from "@/lib/types";

import {
  AccessNotice,
  EmptyState,
  PageHeader,
  ProgressRing,
  ProgressMeter,
  StatCard,
} from "../components/ui";

export const metadata = { title: "My Progress" };

export default function ProgressPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-10 sm:px-6">
      <PageHeader
        eyebrow="Learner"
        title="My Progress"
        description="Your active assignments and completion history."
      />
      <Suspense fallback={<ProgressSkeleton />}>
        <ProgressView />
      </Suspense>
    </main>
  );
}

function ProgressSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-hidden="true">
      <div className="skeleton h-24 rounded-xl" />
      <div className="skeleton h-40 rounded-xl" />
    </div>
  );
}

async function ProgressView() {
  const [learning, completions] = await Promise.all([
    apiGet<MyLearningItem[]>("/me/learning"),
    apiGet<CompletionItem[]>("/me/progress"),
  ]);

  if (!learning.ok) {
    return <AccessNotice kind={learning.kind} message={learning.message} />;
  }
  if (!completions.ok) {
    return <AccessNotice kind={completions.kind} message={completions.message} />;
  }

  const inProgress = learning.data.filter((item) => !item.progress.is_complete);

  return (
    <div className="flex flex-col gap-10">
      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Assigned" value={learning.data.length} />
        <StatCard label="In progress" value={inProgress.length} />
        <StatCard label="Completed" value={completions.data.length} />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900">In progress</h2>
        {inProgress.length === 0 ? (
          <EmptyState
            title="No active assignments"
            description="Courses you have not finished appear here."
          />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {inProgress.map((item) => (
              <li key={item.enrollment.id}>
                <article className="flex h-full items-center gap-4 rounded-xl border border-[var(--border)] bg-white p-5 shadow-sm">
                  <ProgressRing value={item.progress.percent} size={56} />
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-medium text-zinc-900">
                      <Link
                        href={`/courses/${item.course.slug}`}
                        className="hover:text-[var(--brand)]"
                      >
                        {item.course.title}
                      </Link>
                    </h3>
                    <ProgressMeter
                      value={item.progress.percent}
                      label={`${item.progress.completed_lessons} of ${item.progress.required_lessons} required lessons`}
                    />
                    <Link
                      href={`/learn/${item.course.id}`}
                      className="mt-2 inline-block text-sm font-medium link-brand"
                    >
                      Continue →
                    </Link>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold tracking-tight text-zinc-900">Completed</h2>
        {completions.data.length === 0 ? (
          <EmptyState
            title="No completions yet"
            description="Finished courses are recorded here automatically."
          />
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-xl border border-[var(--border)] bg-white">
            {completions.data.map((item) => (
              <li
                key={item.course_id}
                className="flex flex-wrap items-center justify-between gap-3 p-4"
              >
                <div>
                  <p className="font-medium text-zinc-900">
                    <Link href="/courses" className="hover:text-[var(--brand)]">
                      {item.course_title}
                    </Link>
                  </p>
                  <p className="text-xs text-zinc-500">
                    Completed {new Date(item.completed_at).toLocaleDateString()} · rule v
                    {item.completion_rule_version}
                  </p>
                </div>
                <span className="rounded-full bg-[var(--accent-success-soft)] px-2.5 py-0.5 text-xs font-medium text-[var(--accent-success)]">
                  Completed
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
