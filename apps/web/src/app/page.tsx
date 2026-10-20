import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { CoursePage } from "@/lib/types";

import BackendStatus from "./backend-status";
import { CourseCard } from "./components/course-card";
import { EmptyState, Notice } from "./components/ui";

export const metadata = { title: "Home" };

const PILLARS = [
  {
    title: "AI-generated training",
    description:
      "Turn a topic or policy document into a full course, storyboard, video and quiz in minutes.",
    href: "/manage/studio",
    cta: "Open AI Studio",
  },
  {
    title: "Structured assignments",
    description:
      "Assign courses to people or groups, set due dates, and track completion from one console.",
    href: "/manage/assignments",
    cta: "Manage assignments",
  },
  {
    title: "Visible progress",
    description:
      "Learners see exactly what is due and how far along they are, with per-lesson completion.",
    href: "/learning",
    cta: "Go to My Learning",
  },
];

export default function HomePage() {
  return (
    <main className="flex flex-col">
      <section
        className="border-b border-[var(--border)]"
        style={{
          background:
            "linear-gradient(120deg, #eef4fe 0%, #ffffff 55%, #f6f7f9 100%)",
        }}
      >
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:items-center lg:py-24">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--brand)]">
              AI-powered corporate learning
            </p>
            <h1 className="mt-3 text-4xl font-semibold leading-tight tracking-tight text-zinc-900 sm:text-5xl">
              Learn the skills your team needs, faster.
            </h1>
            <p className="mt-4 max-w-xl text-base text-[var(--muted-foreground)]">
              AI LMS drafts lessons and assessments from your own material, assigns
              them to the right people, and shows progress you can act on.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/courses" className="brand-button px-5 py-2.5">
                Explore the catalog
              </Link>
              <Link href="/manage/studio" className="ghost-button px-5 py-2.5">
                Generate training with AI
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-zinc-900">System status</h2>
            <div className="mt-3">
              <Suspense
                fallback={
                  <p className="text-sm text-zinc-500" role="status">
                    Checking API…
                  </p>
                }
              >
                <BackendStatus />
              </Suspense>
            </div>
            <div className="mt-4">
              <Notice tone="warning">
                Local development build. There is no sign-in page. Protected views
                work only when the API runs with AUTH_PROVIDER=development on a
                development machine. Do not expose this deployment to a public or
                shared network.
              </Notice>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">
              Featured courses
            </h2>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Recently published training available to learners.
            </p>
          </div>
          <Link href="/courses" className="text-sm font-medium link-brand">
            View all courses →
          </Link>
        </div>
        <div className="mt-6">
          <Suspense fallback={<FeaturedSkeleton />}>
            <FeaturedCourses />
          </Suspense>
        </div>
      </section>

      <section className="border-t border-[var(--border)] bg-[var(--surface-muted)]">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
          <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">
            One platform, end to end
          </h2>
          <div className="mt-6 grid gap-5 md:grid-cols-3">
            {PILLARS.map((pillar) => (
              <article
                key={pillar.title}
                className="flex flex-col rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm"
              >
                <h3 className="text-base font-semibold text-zinc-900">{pillar.title}</h3>
                <p className="mt-2 flex-1 text-sm text-[var(--muted-foreground)]">
                  {pillar.description}
                </p>
                <Link href={pillar.href} className="mt-4 text-sm font-medium link-brand">
                  {pillar.cta} →
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function FeaturedSkeleton() {
  return (
    <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <li key={index} className="skeleton h-64 rounded-xl" />
      ))}
    </ul>
  );
}

async function FeaturedCourses() {
  const result = await apiGet<CoursePage>("/courses?limit=3");

  if (!result.ok) {
    return (
      <Notice tone="info">
        The catalog is unavailable right now. Start the API to browse courses.
      </Notice>
    );
  }

  if (result.data.items.length === 0) {
    return (
      <EmptyState
        title="No published courses yet"
        description="Generate a course in the AI Studio or author one manually to see it here."
        action={
          <Link href="/manage/studio" className="brand-button mt-1">
            Generate a course
          </Link>
        }
      />
    );
  }

  return (
    <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {result.data.items.map((course) => (
        <li key={course.id}>
          <CourseCard course={course} />
        </li>
      ))}
    </ul>
  );
}
