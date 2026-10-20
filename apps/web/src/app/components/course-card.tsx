import Link from "next/link";

import type { CatalogCourse } from "@/lib/types";

const DIFFICULTY_TONES: Record<string, string> = {
  beginner: "bg-[var(--accent-success-soft)] text-[var(--accent-success)]",
  intermediate: "bg-[var(--brand-soft)] text-[var(--brand-strong)]",
  advanced: "bg-[var(--accent-warning-soft)] text-[var(--accent-warning)]",
};

export function CourseCard({ course }: { course: CatalogCourse }) {
  const tone =
    DIFFICULTY_TONES[course.difficulty_level] ??
    "bg-[var(--surface-sunken)] text-zinc-600";

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-white shadow-sm transition-shadow hover:shadow-md">
      <Link
        href={`/courses/${course.slug}`}
        className="focus-card block"
        tabIndex={-1}
        aria-hidden="true"
      >
        {course.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- external, author-supplied URL
          <img
            src={course.thumbnail_url}
            alt=""
            loading="lazy"
            className="h-40 w-full object-cover"
          />
        ) : (
          <div
            className="grid h-40 w-full place-items-center text-sm font-medium text-[var(--brand-strong)]"
            style={{
              background:
                "linear-gradient(135deg, var(--brand-soft) 0%, #f6f7f9 100%)",
            }}
          >
            {course.category ?? "Course"}
          </div>
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${tone}`}>
            {course.difficulty_level}
          </span>
          {course.category ? (
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">
              {course.category}
            </span>
          ) : null}
        </div>

        <h2 className="text-base font-semibold leading-snug text-zinc-900">
          <Link href={`/courses/${course.slug}`} className="hover:text-[var(--brand)]">
            {course.title}
          </Link>
        </h2>

        <p className="line-clamp-2 flex-1 text-sm text-[var(--muted-foreground)]">
          {course.short_description ?? "No summary provided."}
        </p>

        {course.tags.length > 0 ? (
          <ul className="flex flex-wrap gap-1.5" aria-label="Tags">
            {course.tags.slice(0, 4).map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-[var(--surface-muted)] px-2 py-0.5 text-xs text-zinc-600"
              >
                {tag}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-1 flex items-center justify-between border-t border-[var(--border)] pt-3 text-xs text-zinc-500">
          <span>
            {course.estimated_minutes ? `${course.estimated_minutes} min` : "Self-paced"}
          </span>
          <Link
            href={`/courses/${course.slug}`}
            className="font-medium link-brand"
            aria-label={`View ${course.title}`}
          >
            View course →
          </Link>
        </div>
      </div>
    </article>
  );
}
