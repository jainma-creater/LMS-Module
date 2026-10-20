import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { AssignmentView } from "@/lib/types";
import { first, parsePage, buildQuery } from "@/lib/manage-utils";

import { AssignmentTable } from "../../components/assignment-table";
import { AccessNotice, EmptyState, PageHeader } from "../../components/ui";

export const metadata = { title: "Assignments · AI LMS" };

export default function AssignmentsPage(props: PageProps<"/manage/assignments">) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Assignments"
        description="Manage individual and group course assignments."
      />
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading assignments…
          </p>
        }
      >
        <AssignmentsListView searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function AssignmentsListView({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = {
    course_id: first(raw.course_id),
    learner_id: first(raw.learner_id),
    status: first(raw.status),
    derived: first(raw.derived),
    overdue: raw.overdue === "true",
    search: first(raw.search),
  };
  const page = parsePage(first(raw.page));
  const offset = (page - 1) * 20;

  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (query.course_id) params.set("course_id", query.course_id);
  if (query.learner_id) params.set("learner_id", query.learner_id);
  if (query.status) params.set("status", query.status);
  if (query.derived) params.set("derived", query.derived);
  if (query.overdue) params.set("overdue", "true");
  if (query.search) params.set("search", query.search);

  const list = await apiGet<{ items: AssignmentView[]; total: number; limit: number; offset: number }>(
    `/manage/assignments?${params.toString()}`
  );

  if (!list.ok) {
    return <AccessNotice kind={list.kind} message={list.message} />;
  }

  const { items, total } = list.data;
  const lastPage = Math.max(1, Math.ceil(total / 20));

  return (
    <>
      <div className="flex flex-wrap gap-3 mb-6">
        <form
          method="get"
          action="/manage/assignments"
          role="search"
          className="grid gap-3 rounded-lg border border-[var(--border)] bg-white p-4 sm:grid-cols-2 lg:grid-cols-6"
        >
          <div className="sm:col-span-2 lg:col-span-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-zinc-700">Search</span>
              <input
                type="search"
                name="search"
                defaultValue={query.search ?? ""}
                placeholder="Course title, learner name, or employee ID"
                maxLength={200}
                className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]"
              />
            </label>
          </div>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Course</span>
            <input
              type="text"
              name="course_id"
              defaultValue={query.course_id ?? ""}
              placeholder="Course ID"
              className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Learner</span>
            <input
              type="text"
              name="learner_id"
              defaultValue={query.learner_id ?? ""}
              placeholder="Learner ID"
              className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Status</span>
            <select name="status" defaultValue={query.status ?? ""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Progress</span>
            <select name="derived" defaultValue={query.derived ?? ""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All</option>
              <option value="awaiting_account">Awaiting account</option>
              <option value="assigned">Assigned</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
              <option value="withdrawn">Withdrawn</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Overdue</span>
            <select name="overdue" defaultValue={query.overdue ? "true" : ""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </label>
          <div className="flex items-end gap-3 sm:col-span-2 lg:col-span-6">
            <button
              type="submit"
              className="brand-button"
            >
              Apply filters
            </button>
            <Link href="/manage/assignments" className="link-brand text-sm">
              Clear
            </Link>
          </div>
        </form>
      </div>

      <AssignmentTable assignments={items} />

      {items.length === 0 ? (
        <EmptyState
          title="No assignments match"
          description="Try a different search or clear the filters."
        />
      ) : (
        <>
          <p className="text-sm text-zinc-500" aria-live="polite">
            {total} assignment{total === 1 ? "" : "s"} · page {page} of {lastPage}
          </p>
          <nav aria-label="Pagination" className="flex items-center justify-between text-sm">
            {page > 1 ? (
              <Link href={buildQuery(query, page - 1)} className="link-brand">
                ← Previous
              </Link>
            ) : (
              <span />
            )}
            {page < lastPage ? (
              <Link href={buildQuery(query, page + 1)} className="link-brand">
                Next →
              </Link>
            ) : null}
          </nav>
        </>
      )}
    </>
  );
}