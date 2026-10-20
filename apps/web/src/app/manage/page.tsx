import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { CourseRecord } from "@/lib/types";

import CourseForm from "../components/course-form";
import {
  AccessNotice,
  Card,
  EmptyState,
  PageHeader,
  StatCard,
  StatusBadge,
} from "../components/ui";

export const metadata = { title: "Admin console" };

export default function ManagePage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Admin console"
        title="Overview"
        description="Author courses, generate training with AI, and manage learners and assignments."
        action={
          <Link href="/manage/studio" className="brand-button">
            Open AI Studio
          </Link>
        }
      />
      <Suspense fallback={<DashboardSkeleton />}>
        <Dashboard />
      </Suspense>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-hidden="true">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="skeleton h-24 rounded-xl" />
        ))}
      </div>
      <div className="skeleton h-48 rounded-xl" />
    </div>
  );
}

async function Dashboard() {
  // Listing all courses requires courses:write, so this doubles as the
  // authoring-access check. Without it, no admin controls are rendered.
  const [courses, learners, assignments, groups] = await Promise.all([
    apiGet<CourseRecord[]>("/admin/courses"),
    apiGet<{ total: number }>("/manage/learners?limit=1"),
    apiGet<{ total: number }>("/manage/assignments?limit=1"),
    apiGet<{ total: number }>("/manage/learning-groups?limit=1"),
  ]);

  if (!courses.ok) {
    return <AccessNotice kind={courses.kind} message={courses.message} />;
  }

  const published = courses.data.filter((course) => course.status === "published").length;
  const drafts = courses.data.filter((course) => course.status === "draft").length;

  return (
    <div className="flex flex-col gap-8">
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Courses" value={courses.data.length} hint={`${published} published · ${drafts} draft`} />
        <StatCard label="Learners" value={learners.ok ? learners.data.total : "—"} />
        <StatCard label="Assignments" value={assignments.ok ? assignments.data.total : "—"} />
        <StatCard label="Groups" value={groups.ok ? groups.data.total : "—"} />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Link
          href="/manage/studio"
          className="rounded-xl border border-[var(--border)] bg-gradient-to-br from-[var(--brand-soft)] to-white p-6 shadow-sm transition-shadow hover:shadow-md lg:col-span-2"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--brand)]">
            AI-powered training studio
          </p>
          <h2 className="mt-2 text-lg font-semibold text-zinc-900">
            Generate complete training in a few clicks
          </h2>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Upload policies or SOPs, or enter a topic, to automatically draft the
            syllabus, lessons, video storyboard and objective assessment.
          </p>
          <span className="mt-4 inline-block text-sm font-medium link-brand">
            Launch Studio →
          </span>
        </Link>
        <Card title="Quick actions">
          <ul className="flex flex-col gap-2">
            <li>
              <Link href="/manage/learners" className="link-brand text-sm">
                Add a learner
              </Link>
            </li>
            <li>
              <Link href="/manage/groups" className="link-brand text-sm">
                Create a learning group
              </Link>
            </li>
            <li>
              <Link href="/manage/group-assignments" className="link-brand text-sm">
                Assign a course to a group
              </Link>
            </li>
            <li>
              <Link href="/manage/assignments" className="link-brand text-sm">
                Review assignments &amp; due dates
              </Link>
            </li>
          </ul>
        </Card>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900">Courses</h2>
          <Link href="/courses" className="text-sm link-brand">
            View learner catalog →
          </Link>
        </div>

        <Card title="Create a course manually">
          <CourseForm />
        </Card>

        {courses.data.length === 0 ? (
          <EmptyState
            title="No courses yet"
            description="Create your first course manually or generate one with the AI Studio."
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--surface-muted)] text-xs uppercase tracking-wide text-zinc-500">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">Course</th>
                  <th scope="col" className="px-4 py-3 font-medium">Category</th>
                  <th scope="col" className="px-4 py-3 font-medium">Level</th>
                  <th scope="col" className="px-4 py-3 font-medium">Status</th>
                  <th scope="col" className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {courses.data.map((course) => (
                  <tr key={course.id} className="hover:bg-[var(--surface-muted)]">
                    <td className="px-4 py-3 font-medium text-zinc-900">{course.title}</td>
                    <td className="px-4 py-3 text-zinc-600">
                      {course.category ?? "Uncategorised"}
                    </td>
                    <td className="px-4 py-3 capitalize text-zinc-600">
                      {course.difficulty_level}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={course.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/manage/${course.id}`}
                        className="font-medium link-brand"
                      >
                        Edit
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
