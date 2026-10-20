import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { LearningGroup } from "@/lib/types";
import { first, parsePage, buildQuery } from "@/lib/manage-utils";

import { GroupTable } from "../../components/group-table";
import { AccessNotice, EmptyState, PageHeader } from "../../components/ui";

export const metadata = { title: "Learning Groups · AI LMS" };

export default function GroupsPage(props: PageProps<"/manage/groups">) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Learning Groups"
        description="Organize learners into groups for bulk course assignments."
        action={
          <Link
            href="/manage/groups/new"
            className="brand-button"
          >
            Create group
          </Link>
        }
      />
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading groups…
          </p>
        }
      >
        <GroupsListView searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function GroupsListView({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = {
    search: first(raw.search),
    status: first(raw.status),
    kind: first(raw.kind),
  };
  const page = parsePage(first(raw.page));
  const offset = (page - 1) * 20;

  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (query.search) params.set("search", query.search);
  if (query.status) params.set("status", query.status);
  if (query.kind) params.set("kind", query.kind);

  const [list, kinds] = await Promise.all([
    apiGet<{ items: LearningGroup[]; total: number; limit: number; offset: number }>(`/manage/learning-groups?${params.toString()}`),
    apiGet<string[]>("/manage/learning-groups/kinds"),
  ]);

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
          action="/manage/groups"
          role="search"
          className="grid gap-3 rounded-lg border border-[var(--border)] bg-white p-4 sm:grid-cols-2 lg:grid-cols-5"
        >
          <div className="sm:col-span-2 lg:col-span-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-zinc-700">Search</span>
              <input
                type="search"
                name="search"
                defaultValue={""}
                placeholder="Group name"
                maxLength={200}
                className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]"
              />
            </label>
          </div>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Status</span>
            <select name="status" defaultValue={""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Kind</span>
            <select name="kind" defaultValue={""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All kinds</option>
              {kinds.ok ? kinds.data.map((k) => <option key={k} value={k}>{k}</option>) : null}
            </select>
          </label>
          <div className="flex items-end gap-3 sm:col-span-2 lg:col-span-5">
            <button
              type="submit"
              className="brand-button"
            >
              Apply filters
            </button>
            <Link href="/manage/groups" className="link-brand text-sm">
              Clear
            </Link>
          </div>
        </form>
      </div>

      <GroupTable groups={items} />

      {items.length === 0 ? (
        <EmptyState
          title="No groups match"
          description="Try a different search or clear the filters."
        />
      ) : (
        <>
          <p className="text-sm text-zinc-500" aria-live="polite">
            {total} group{total === 1 ? "" : "s"} · page {page} of {lastPage}
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