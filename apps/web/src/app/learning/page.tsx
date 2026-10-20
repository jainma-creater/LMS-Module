import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { MyLearningItem } from "@/lib/types";

import {
  AccessNotice,
  EmptyState,
  PageHeader,
  ProgressRing,
  StatusBadge,
} from "../components/ui";

export const metadata = { title: "My Learning" };

export default function LearningPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-10 sm:px-6">
      <PageHeader
        eyebrow="Learner"
        title="My Learning"
        description="Courses assigned to you, with due dates and progress."
        action={
          <Link href="/courses" className="ghost-button">
            Browse catalog
          </Link>
        }
      />
      <Suspense fallback={<LearningSkeleton />}>
        <LearningList />
      </Suspense>
    </main>
  );
}

function LearningSkeleton() {
  return (
    <ul className="flex flex-col gap-4" aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <li key={index} className="skeleton h-28 rounded-xl" />
      ))}
    </ul>
  );
}

async function LearningList() {
  const result = await apiGet<MyLearningItem[]>("/me/learning");

  if (!result.ok) {
    return <AccessNotice kind={result.kind} message={result.message} />;
  }

  if (result.data.length === 0) {
    return (
      <EmptyState
        title="Nothing assigned yet"
        description="Courses assigned to you will appear here. You can also browse the catalog and start learning."
        action={
          <Link href="/courses" className="brand-button mt-1">
            Explore the catalog
          </Link>
        }
      />
    );
  }

  return (
    <ul className="flex flex-col gap-4">
      {result.data.map((item) => (
        <li key={item.enrollment.id}>
          <article className="flex flex-wrap items-center gap-5 rounded-xl border border-[var(--border)] bg-white p-5 shadow-sm">
            <ProgressRing value={item.progress.percent} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-semibold text-zinc-900">
                  <Link href={`/courses/${item.course.slug}`} className="hover:text-[var(--brand)]">
                    {item.course.title}
                  </Link>
                </h2>
                <StatusBadge value={item.enrollment.status} />
                {item.enrollment.overdue ? <StatusBadge value="overdue" /> : null}
              </div>
              <p className="mt-1 text-sm text-[var(--muted-foreground)]">
                {item.progress.completed_lessons} of {item.progress.required_lessons} required
                lessons complete
              </p>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-zinc-500">
                <span>{item.course.category ?? "Uncategorised"}</span>
                <span className="capitalize">{item.course.difficulty_level}</span>
                <span>
                  Assigned {new Date(item.enrollment.assigned_at).toLocaleDateString()}
                </span>
                {item.enrollment.due_at ? (
                  <span className={item.enrollment.overdue ? "font-medium text-[var(--accent-danger)]" : ""}>
                    Due {new Date(item.enrollment.due_at).toLocaleDateString()}
                  </span>
                ) : null}
              </div>
              {item.enrollment.overdue ? (
                <p className="mt-2 text-sm text-[var(--accent-danger)]">This assignment is overdue.</p>
              ) : null}
            </div>
            <div className="flex shrink-0 flex-col items-stretch gap-2">
              <Link href={`/learn/${item.course.id}`} className="brand-button">
                {item.progress.is_complete
                  ? "Review"
                  : item.progress.completed_lessons > 0
                    ? "Continue"
                    : "Start"}
              </Link>
              <Link
                href={`/courses/${item.course.slug}`}
                className="text-center text-xs text-zinc-500 hover:text-[var(--brand)]"
              >
                Course details
              </Link>
            </div>
          </article>
        </li>
      ))}
    </ul>
  );
}
