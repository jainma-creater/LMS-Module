import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { GroupAssignmentView } from "@/lib/types";
import { first, parsePage, buildQuery } from "@/lib/manage-utils";

import { GroupAssignmentTable } from "../../components/group-assignment-table";
import { AccessNotice, EmptyState, PageHeader } from "../../components/ui";

export const metadata = { title: "Group Assignments · AI LMS" };

export default function GroupAssignmentsPage(props: PageProps<"/manage/group-assignments">) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Group Assignments"
        description="Manage course assignments for learning groups."
      />
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading group assignments…
          </p>
        }
      >
        <GroupAssignmentsListView searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function GroupAssignmentsListView({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = {
    course_id: first(raw.course_id),
    group_id: first(raw.group_id),
    status: first(raw.status),
  };
  const page = parsePage(first(raw.page));
  const offset = (page - 1) * 20;

  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (query.course_id) params.set("course_id", query.course_id);
  if (query.group_id) params.set("group_id", query.group_id);
  if (query.status) params.set("status", query.status);

  const list = await apiGet<{ items: GroupAssignmentView[]; total: number; limit: number; offset: number }>(
    `/manage/group-assignments?${params.toString()}`
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
          action="/manage/group-assignments"
          role="search"
          className="grid gap-3 rounded-lg border border-[var(--border)] bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <div className="sm:col-span-2 lg:col-span-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-zinc-700">Search</span>
              <input
                type="search"
                name="search"
                defaultValue={""}
                placeholder="Course or group name"
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
            <span className="font-medium text-zinc-700">Group</span>
            <input
              type="text"
              name="group_id"
              defaultValue={query.group_id ?? ""}
              placeholder="Group ID"
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
          <div className="flex items-end gap-3 sm:col-span-2 lg:col-span-4">
            <button
              type="submit"
              className="brand-button"
            >
              Apply filters
            </button>
            <Link href="/manage/group-assignments" className="link-brand text-sm">
              Clear
            </Link>
          </div>
        </form>
      </div>

      <GroupAssignmentTable groupAssignments={items} />

      {items.length === 0 ? (
        <EmptyState
          title="No group assignments match"
          description="Try a different search or clear the filters."
        />
      ) : (
        <>
          <p className="text-sm text-zinc-500" aria-live="polite">
            {total} group assignment{total === 1 ? "" : "s"} · page {page} of {lastPage}
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