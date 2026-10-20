import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { CoursePage as CoursePageData } from "@/lib/types";

import { CourseCard } from "../components/course-card";
import { CourseFilters, type CatalogQuery } from "../components/course-filters";
import { AccessNotice, EmptyState, PageHeader } from "../components/ui";

export const metadata = { title: "Courses · AI LMS" };

const PAGE_SIZE = 12;

export default function CoursesPage(props: PageProps<"/courses">) {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
      <PageHeader
        eyebrow="Catalog"
        title="Courses"
        description="Browse published courses. Search, filter by category, difficulty, or tag."
      />
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading courses…
          </p>
        }
      >
        <CourseListView searchParams={props.searchParams} />
      </Suspense>
    </main>
  );
}

function first(value: string | string[] | undefined): string | undefined {
  const picked = Array.isArray(value) ? value[0] : value;
  const trimmed = picked?.trim();
  return trimmed ? trimmed : undefined;
}

function parsePage(value: string | undefined): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed >= 1 ? parsed : 1;
}

function buildQuery(query: CatalogQuery, page: number): string {
  const params = new URLSearchParams();
  if (query.search) params.set("search", query.search);
  if (query.category) params.set("category", query.category);
  if (query.difficulty_level) params.set("difficulty_level", query.difficulty_level);
  if (query.tag) params.set("tag", query.tag);
  if (page > 1) params.set("page", String(page));
  const text = params.toString();
  return text ? `/courses?${text}` : "/courses";
}

async function CourseListView({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query: CatalogQuery = {
    search: first(raw.search),
    category: first(raw.category),
    difficulty_level: first(raw.difficulty_level),
    tag: first(raw.tag),
  };
  const page = parsePage(first(raw.page));
  const offset = (page - 1) * PAGE_SIZE;

  const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
  if (query.search) params.set("search", query.search);
  if (query.category) params.set("category", query.category);
  if (query.difficulty_level) params.set("difficulty_level", query.difficulty_level);
  if (query.tag) params.set("tag", query.tag);

  const [catalog, categories] = await Promise.all([
    apiGet<CoursePageData>(`/courses?${params.toString()}`),
    apiGet<string[]>("/courses/categories"),
  ]);

  if (!catalog.ok) {
    return <AccessNotice kind={catalog.kind} message={catalog.message} />;
  }

  const { items, total } = catalog.data;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <CourseFilters
        query={query}
        categories={categories.ok ? categories.data : []}
      />

      {items.length === 0 ? (
        <EmptyState
          title="No courses match"
          description="Try a different search or clear the filters."
        />
      ) : (
        <>
          <p className="text-sm text-zinc-500" aria-live="polite">
            {total} course{total === 1 ? "" : "s"} · page {page} of {lastPage}
          </p>
          <ul className="grid gap-4 sm:grid-cols-2">
            {items.map((course) => (
              <li key={course.id}>
                <CourseCard course={course} />
              </li>
            ))}
          </ul>
          <nav aria-label="Pagination" className="flex items-center justify-between text-sm">
            {page > 1 ? (
              <Link href={buildQuery(query, page - 1)} className="text-blue-700 hover:underline dark:text-blue-400">
                ← Previous
              </Link>
            ) : (
              <span />
            )}
            {page < lastPage ? (
              <Link href={buildQuery(query, page + 1)} className="text-blue-700 hover:underline dark:text-blue-400">
                Next →
              </Link>
            ) : null}
          </nav>
        </>
      )}
    </>
  );
}
