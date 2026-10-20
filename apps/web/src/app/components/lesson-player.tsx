"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

import { recordLessonProgress } from "@/app/actions";
import type { CourseDetail, Lesson, ModuleWithLessons } from "@/lib/types";

interface FlatLesson {
  lesson: Lesson;
  moduleTitle: string;
  moduleIndex: number;
  lessonIndex: number;
  globalIndex: number;
}

function flatten(modules: ModuleWithLessons[]): FlatLesson[] {
  const out: FlatLesson[] = [];
  modules.forEach((module, moduleIndex) => {
    module.lessons.forEach((lesson, lessonIndex) => {
      out.push({
        lesson,
        moduleTitle: module.title,
        moduleIndex,
        lessonIndex,
        globalIndex: out.length,
      });
    });
  });
  return out;
}

function isHttpUrl(value: string | null): boolean {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export default function LessonPlayer({
  course,
  modules,
  progressByLesson,
  requestedLessonId,
}: {
  course: CourseDetail;
  modules: ModuleWithLessons[];
  progressByLesson: Record<string, string>;
  requestedLessonId: string | null;
}) {
  const router = useRouter();
  const flat = useMemo(() => flatten(modules), [modules]);
  const [statusMap, setStatusMap] = useState<Record<string, string>>(progressByLesson);
  const [activeId, setActiveId] = useState<string>(() => {
    if (requestedLessonId && flat.some((item) => item.lesson.id === requestedLessonId)) {
      return requestedLessonId;
    }
    return flat[0]?.lesson.id ?? "";
  });
  const [pending, startTransition] = useTransition();

  const activeIndex = flat.findIndex((item) => item.lesson.id === activeId);
  const active = activeIndex >= 0 ? flat[activeIndex] : null;
  const prev = activeIndex > 0 ? flat[activeIndex - 1] : null;
  const next = activeIndex >= 0 && activeIndex < flat.length - 1 ? flat[activeIndex + 1] : null;

  const requiredLessons = flat.filter((item) => item.lesson.is_required);
  const completedRequired = requiredLessons.filter(
    (item) => statusMap[item.lesson.id] === "completed",
  ).length;
  const percent =
    requiredLessons.length === 0
      ? 0
      : Math.round((completedRequired / requiredLessons.length) * 100);

  function select(lessonId: string) {
    setActiveId(lessonId);
    router.replace(`/learn/${course.id}?lesson=${lessonId}`, { scroll: false });
  }

  function mark(status: "completed" | "in_progress") {
    if (!active) return;
    const lessonId = active.lesson.id;
    const optimistic = { ...statusMap, [lessonId]: status };
    setStatusMap(optimistic);
    startTransition(async () => {
      const formData = new FormData();
      formData.set("lesson_id", lessonId);
      formData.set("status", status);
      const result = await recordLessonProgress({ status: "idle", message: "" }, formData);
      if (result.status === "error") {
        setStatusMap((current) => ({ ...current, [lessonId]: statusMap[lessonId] ?? "not_started" }));
      } else {
        router.refresh();
      }
    });
  }

  if (flat.length === 0) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-16 text-center">
        <h1 className="text-xl font-semibold text-zinc-900">{course.title}</h1>
        <p className="mt-2 text-sm text-zinc-500">
          This course does not have any lessons yet.
        </p>
        <Link href={`/courses/${course.slug}`} className="brand-button mt-4">
          Back to course
        </Link>
      </div>
    );
  }

  return (
    <div className="grid flex-1 lg:grid-cols-[20rem_minmax(0,1fr)]">
      <aside className="border-b border-[var(--border)] bg-[var(--surface-muted)] lg:border-b-0 lg:border-r">
        <div className="sticky top-16 max-h-[calc(100vh-4rem)] overflow-y-auto p-4">
          <Link
            href={`/courses/${course.slug}`}
            className="text-xs font-medium text-zinc-500 hover:text-[var(--brand)]"
          >
            ← {course.title}
          </Link>
          <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
            <span>
              {completedRequired}/{requiredLessons.length} required complete
            </span>
            <span className="font-semibold text-zinc-700">{percent}%</span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-sunken)]">
            <div
              className="h-full rounded-full"
              style={{ width: `${percent}%`, backgroundColor: "var(--brand)" }}
            />
          </div>

          <nav aria-label="Course lessons" className="mt-4 flex flex-col gap-3">
            {modules.map((module, moduleIndex) => (
              <div key={module.id}>
                <p className="px-1 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                  Module {moduleIndex + 1}
                </p>
                <p className="px-1 text-sm font-medium text-zinc-800">{module.title}</p>
                <ul className="mt-1.5 flex flex-col gap-0.5">
                  {module.lessons.map((lesson) => {
                    const isActive = lesson.id === activeId;
                    const done = statusMap[lesson.id] === "completed";
                    return (
                      <li key={lesson.id}>
                        <button
                          type="button"
                          onClick={() => select(lesson.id)}
                          aria-current={isActive ? "true" : undefined}
                          className={`flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                            isActive
                              ? "bg-white font-medium text-[var(--brand)] shadow-sm"
                              : "text-zinc-600 hover:bg-white"
                          }`}
                        >
                          <span
                            aria-hidden="true"
                            className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full border text-[10px] ${
                              done
                                ? "border-[var(--accent-success)] bg-[var(--accent-success)] text-white"
                                : "border-[var(--border-strong)]"
                            }`}
                          >
                            {done ? "✓" : ""}
                          </span>
                          <span className="flex-1">
                            {lesson.title}
                            {lesson.is_required ? null : (
                              <span className="ml-1 text-xs text-zinc-400">optional</span>
                            )}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>
        </div>
      </aside>

      <section className="flex flex-col">
        <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--brand)]">
            {active?.moduleTitle}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
              {active?.lesson.title}
            </h1>
            {statusMap[active?.lesson.id ?? ""] === "completed" ? (
              <span className="rounded-full bg-[var(--accent-success-soft)] px-2.5 py-0.5 text-xs font-medium text-[var(--accent-success)]">
                Completed
              </span>
            ) : null}
          </div>

          <div className="mt-6">
            <LessonBody lesson={active?.lesson ?? null} />
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-6">
            <button
              type="button"
              onClick={() => mark("completed")}
              disabled={pending}
              className="brand-button disabled:opacity-60"
            >
              {statusMap[active?.lesson.id ?? ""] === "completed"
                ? "Completed ✓"
                : pending
                  ? "Saving…"
                  : "Mark as complete"}
            </button>
            {statusMap[active?.lesson.id ?? ""] !== "completed" ? (
              <button
                type="button"
                onClick={() => mark("in_progress")}
                disabled={pending}
                className="ghost-button disabled:opacity-60"
              >
                Save for later
              </button>
            ) : null}
            <div className="ml-auto flex items-center gap-2">
              <button
                type="button"
                onClick={() => prev && select(prev.lesson.id)}
                disabled={!prev}
                className="ghost-button disabled:opacity-40"
              >
                ← Previous
              </button>
              <button
                type="button"
                onClick={() => next && select(next.lesson.id)}
                disabled={!next}
                className="brand-button disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function LessonBody({ lesson }: { lesson: Lesson | null }) {
  if (!lesson) {
    return <p className="text-sm text-zinc-500">Select a lesson to begin.</p>;
  }

  if (lesson.content_type === "video_url" && isHttpUrl(lesson.content)) {
    return (
      <div className="flex flex-col gap-4">
        <video
          controls
          preload="metadata"
          className="w-full rounded-xl border border-[var(--border)] bg-black"
          src={lesson.content ?? undefined}
        />
        {lesson.description ? (
          <p className="text-sm text-[var(--muted-foreground)]">{lesson.description}</p>
        ) : null}
      </div>
    );
  }

  if (lesson.content_type === "external_link" && isHttpUrl(lesson.content)) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-sm text-[var(--muted-foreground)]">
          This lesson opens an external resource.
        </p>
        <a
          href={lesson.content ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="brand-button self-start"
        >
          Open resource ↗
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {lesson.description ? (
        <p className="text-sm text-[var(--muted-foreground)]">{lesson.description}</p>
      ) : null}
      {lesson.content ? (
        <div className="lesson-prose text-zinc-700">{lesson.content}</div>
      ) : (
        <p className="text-sm text-zinc-500">This lesson has no content yet.</p>
      )}
    </div>
  );
}
