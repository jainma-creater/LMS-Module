import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { Learner } from "@/lib/types";
import { first, parsePage, buildQuery } from "@/lib/manage-utils";

import { LearnerTable } from "../../components/learner-table";
import { AccessNotice, EmptyState, PageHeader } from "../../components/ui";

export const metadata = { title: "Learners · AI LMS" };

export default function LearnersPage(props: PageProps<"/manage/learners">) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Learners"
        description="Manage learner records. Create, edit, and link learners to identity accounts."
        action={
          <Link
            href="/manage/learners/new"
            className="brand-button"
          >
            Create learner
          </Link>
        }
      />
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading learners…
          </p>
        }
      >
        <LearnersListView searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

async function LearnersListView({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = {
    search: first(raw.search),
    status: first(raw.status),
    department: first(raw.department),
    business_unit: first(raw.business_unit),
  };
  const page = parsePage(first(raw.page));
  const offset = (page - 1) * 20;

  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (query.search) params.set("search", query.search);
  if (query.status) params.set("status", query.status);
  if (query.department) params.set("department", query.department);
  if (query.business_unit) params.set("business_unit", query.business_unit);

  const [list, departments, businessUnits] = await Promise.all([
    apiGet<{ items: Learner[]; total: number; limit: number; offset: number }>(`/manage/learners?${params.toString()}`),
    apiGet<string[]>("/manage/learners/departments"),
    apiGet<string[]>("/manage/learners/business-units"),
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
          action="/manage/learners"
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
                placeholder="Name, email, or employee ID"
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
            <span className="font-medium text-zinc-700">Department</span>
            <select name="department" defaultValue={""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All departments</option>
              {departments.ok ? departments.data.map((d) => <option key={d} value={d}>{d}</option>) : null}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700">Business Unit</span>
            <select name="business_unit" defaultValue={""} className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-sm text-black outline-none focus:border-[var(--brand)]">
              <option value="">All business units</option>
              {businessUnits.ok ? businessUnits.data.map((b) => <option key={b} value={b}>{b}</option>) : null}
            </select>
          </label>
          <div className="flex items-end gap-3 sm:col-span-2 lg:col-span-5">
            <button
              type="submit"
              className="brand-button"
            >
              Apply filters
            </button>
            <Link href="/manage/learners" className="link-brand text-sm">
              Clear
            </Link>
          </div>
        </form>
      </div>

      <LearnerTable learners={items} />

      {items.length === 0 ? (
        <EmptyState
          title="No learners match"
          description="Try a different search or clear the filters."
        />
      ) : (
        <>
          <p className="text-sm text-zinc-500" aria-live="polite">
            {total} learner{total === 1 ? "" : "s"} · page {page} of {lastPage}
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