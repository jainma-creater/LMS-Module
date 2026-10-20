import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { CourseContent, CourseDetail, CourseProgress } from "@/lib/types";

import {
  AccessNotice,
  Notice,
  ProgressMeter,
  StatusBadge,
} from "../../components/ui";

export async function generateMetadata(props: PageProps<"/courses/[slug]">) {
  const { slug } = await props.params;
  const result = await apiGet<CourseDetail>(`/courses/slug/${encodeURIComponent(slug)}`);
  if (!result.ok) {
    return { title: "Course" };
  }
  return {
    title: result.data.title,
    description: result.data.short_description ?? undefined,
  };
}

export default function CourseDetailPage(props: PageProps<"/courses/[slug]">) {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <Suspense fallback={<CourseSkeleton />}>
        <CourseDetailView params={props.params} />
      </Suspense>
    </main>
  );
}

function CourseSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-hidden="true">
      <div className="skeleton h-5 w-56 rounded" />
      <div className="skeleton h-10 w-2/3 rounded" />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="skeleton h-80 rounded-xl" />
        <div className="skeleton h-64 rounded-xl" />
      </div>
    </div>
  );
}

async function CourseDetailView({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const detail = await apiGet<CourseDetail>(`/courses/slug/${encodeURIComponent(slug)}`);

  if (!detail.ok) {
    return <AccessNotice kind={detail.kind} message={detail.message} />;
  }

  const course = detail.data;
  const [content, progress] = await Promise.all([
    apiGet<CourseContent>(`/courses/${course.id}/content`),
    apiGet<CourseProgress>(`/courses/${course.id}/progress`),
  ]);

  const lessonCount = course.counts.lessons;
  const requiredLessons = content.ok
    ? content.data.modules.reduce(
        (total, module) => total + module.lessons.filter((lesson) => lesson.is_required).length,
        0,
      )
    : 0;

  return (
    <div className="flex flex-col gap-8">
      <nav aria-label="Breadcrumb" className="text-sm text-zinc-500">
        <ol className="flex flex-wrap items-center gap-2">
          <li>
            <Link href="/" className="hover:text-[var(--brand)]">
              Home
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link href="/courses" className="hover:text-[var(--brand)]">
              Courses
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li className="truncate text-zinc-700">{course.title}</li>
        </ol>
      </nav>

      <header className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge value={course.status} />
          <span className="rounded-full bg-[var(--surface-sunken)] px-2.5 py-0.5 text-xs font-medium capitalize text-zinc-600">
            {course.difficulty_level}
          </span>
          {course.category ? (
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">
              {course.category}
            </span>
          ) : null}
        </div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-900">
          {course.title}
        </h1>
        {course.short_description ? (
          <p className="mt-2 max-w-3xl text-base text-[var(--muted-foreground)]">
            {course.short_description}
          </p>
        ) : null}
        <dl className="mt-5 flex flex-wrap gap-x-8 gap-y-3 text-sm">
          <Meta label="Modules" value={String(course.counts.modules)} />
          <Meta label="Lessons" value={String(lessonCount)} />
          {course.estimated_minutes ? (
            <Meta label="Duration" value={`${course.estimated_minutes} min`} />
          ) : null}
          {course.published_at ? (
            <Meta
              label="Published"
              value={new Date(course.published_at).toLocaleDateString()}
            />
          ) : null}
        </dl>
        {course.tags.length > 0 ? (
          <ul className="mt-5 flex flex-wrap gap-2" aria-label="Tags">
            {course.tags.map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs text-zinc-600"
              >
                {tag}
              </li>
            ))}
          </ul>
        ) : null}
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
        <div className="flex flex-col gap-8">
          {course.description ? (
            <section aria-labelledby="about-heading">
              <h2
                id="about-heading"
                className="text-xl font-semibold tracking-tight text-zinc-900"
              >
                About this course
              </h2>
              <p className="lesson-prose mt-3 text-sm text-zinc-700">
                {course.description}
              </p>
            </section>
          ) : null}

          <section aria-labelledby="syllabus-heading">
            <h2
              id="syllabus-heading"
              className="text-xl font-semibold tracking-tight text-zinc-900"
            >
              Syllabus
            </h2>
            {!content.ok ? (
              <div className="mt-3">
                <AccessNotice kind={content.kind} message={content.message} />
              </div>
            ) : content.data.modules.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-500">No modules yet.</p>
            ) : (
              <ol className="mt-3 flex flex-col gap-3">
                {content.data.modules.map((module, index) => (
                  <li key={module.id}>
                    <details
                      className="group overflow-hidden rounded-xl border border-[var(--border)] bg-white"
                      open={index === 0}
                    >
                      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 hover:bg-[var(--surface-muted)]">
                        <span className="flex items-center gap-3">
                          <span className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
                            Module {index + 1}
                          </span>
                          <span className="font-medium text-zinc-900">{module.title}</span>
                        </span>
                        <span className="flex items-center gap-3 text-xs text-zinc-500">
                          {module.lessons.length} lesson
                          {module.lessons.length === 1 ? "" : "s"}
                          <svg
                            aria-hidden="true"
                            viewBox="0 0 24 24"
                            className="h-4 w-4 transition-transform group-open:rotate-180"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="6 9 12 15 18 9" />
                          </svg>
                        </span>
                      </summary>
                      {module.description ? (
                        <p className="border-t border-[var(--border)] px-4 py-3 text-sm text-[var(--muted-foreground)]">
                          {module.description}
                        </p>
                      ) : null}
                      <ul className="divide-y divide-[var(--border)] border-t border-[var(--border)]">
                        {module.lessons.map((lesson) => (
                          <li
                            key={lesson.id}
                            className="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
                          >
                            <span className="text-sm text-zinc-800">
                              {lesson.title}
                              {lesson.is_required ? null : (
                                <span className="ml-2 text-xs text-zinc-400">optional</span>
                              )}
                            </span>
                            <span className="text-xs uppercase tracking-wide text-zinc-400">
                              {lesson.content_type.replace(/_/g, " ")}
                              {lesson.estimated_minutes ? ` · ${lesson.estimated_minutes} min` : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        <aside className="flex flex-col gap-4 lg:sticky lg:top-24">
          <div className="rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm">
            {progress.ok ? (
              <div className="flex flex-col gap-4">
                <div>
                  <p className="text-sm font-medium text-zinc-500">Your progress</p>
                  <p className="mt-1 text-2xl font-semibold text-zinc-900">
                    {progress.data.percent}%
                  </p>
                </div>
                <ProgressMeter
                  value={progress.data.percent}
                  label={`${progress.data.completed_lessons} of ${progress.data.required_lessons} required lessons complete`}
                />
                <Link
                  href={`/learn/${course.id}`}
                  className="brand-button w-full py-2.5"
                >
                  {progress.data.completed_lessons > 0 ? "Continue learning" : "Start learning"}
                </Link>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-[var(--muted-foreground)]">
                  {requiredLessons > 0
                    ? `${requiredLessons} required lesson${requiredLessons === 1 ? "" : "s"}`
                    : "Self-paced course"}
                </p>
                <Link href={`/learn/${course.id}`} className="brand-button w-full py-2.5">
                  Start learning
                </Link>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-muted)] p-5 text-sm text-zinc-600">
            <p className="font-medium text-zinc-800">What you&apos;ll get</p>
            <ul className="mt-2 flex flex-col gap-1.5">
              <li>{course.counts.modules} modules, {lessonCount} lessons</li>
              <li>Per-lesson progress tracking</li>
              <li>Objective assessment where provided</li>
              <li>Completion recorded for your organisation</li>
            </ul>
          </div>

          {!progress.ok ? (
            <Notice tone="info">
              Progress appears once you are enrolled. Your records are stored
              server-side.
            </Notice>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-400">{label}</dt>
      <dd className="mt-0.5 font-medium text-zinc-800">{value}</dd>
    </div>
  );
}
