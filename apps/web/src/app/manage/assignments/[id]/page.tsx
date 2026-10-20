import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { AssignmentDetail } from "@/lib/types";

import { AccessNotice, Card, PageHeader, ProgressMeter, StatusBadge } from "../../../components/ui";

export default function AssignmentDetailPage(props: PageProps<"/manage/assignments/[id]">) {
  return (
    <div className="flex flex-col gap-6">
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading assignment…
          </p>
        }
      >
        <AssignmentDetailView params={props.params} />
      </Suspense>
    </div>
  );
}

async function AssignmentDetailView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await apiGet<AssignmentDetail>(`/manage/assignments/${id}`);

  if (!detail.ok) {
    return (
      <>
        <BackLink />
        <AccessNotice kind={detail.kind} message={detail.message} />
      </>
    );
  }

  const assignment = detail.data;
  const progress = detail.data.progress;

  return (
    <>
      <BackLink />
      <PageHeader
        title={`Assignment: ${assignment.course_title}`}
        description={`${assignment.learner_name} (${assignment.learner_employee_id})`}
        action={<StatusBadge value={assignment.derived_status} />}
      />

      <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-zinc-500">Source</dt>
          <dd className="font-medium capitalize">{assignment.source}</dd>
        </div>
        {assignment.group_name ? (
          <div>
            <dt className="text-zinc-500">Group</dt>
            <dd className="font-medium">
              <Link href={`/manage/groups/${assignment.group_id}`} className="hover:underline">
                {assignment.group_name}
              </Link>
            </dd>
          </div>
        ) : null}
        <div>
          <dt className="text-zinc-500">Status</dt>
          <dd className="font-medium">{assignment.status}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Derived Status</dt>
          <dd className="font-medium">{assignment.derived_status.replace("_", " ")}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Due Date</dt>
          <dd className="font-medium">
            {assignment.due_at ? new Date(assignment.due_at).toLocaleDateString() : "Not set"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Overdue</dt>
          <dd className="font-medium">{assignment.overdue ? "Yes" : "No"}</dd>
        </div>
      </dl>

      {assignment.cancelled_at ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Cancelled: {new Date(assignment.cancelled_at).toLocaleString()}
          {assignment.cancel_reason ? ` — Reason: ${assignment.cancel_reason}` : ""}
        </p>
      ) : (
        <div className="flex flex-wrap gap-3">
          {assignment.status === "active" && (
            <form action={`/manage/assignments/${id}/cancel`} method="post">
              <button
                type="submit"
                className="inline-flex items-center rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
              >
                Cancel assignment
              </button>
            </form>
          )}
          {assignment.enrollment_id && (
            <Link
              href={`/manage/enrollments/${assignment.enrollment_id}`}
              className="text-sm font-medium text-blue-700 hover:underline dark:text-blue-400"
            >
              View enrollment →
            </Link>
          )}
        </div>
      )}

      {assignment.enrollment ? (
        <Card title="Enrollment">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-zinc-500">Status</dt>
              <dd className="font-medium">{assignment.enrollment?.status}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Due Date</dt>
              <dd className="font-medium">{assignment.enrollment?.due_at ? new Date(assignment.enrollment.due_at).toLocaleDateString() : "Not set"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Overdue</dt>
              <dd className="font-medium">{assignment.enrollment?.overdue ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Completed</dt>
              <dd className="font-medium">{assignment.enrollment?.completed_at ? new Date(assignment.enrollment.completed_at).toLocaleString() : "Not completed"}</dd>
            </div>
          </dl>
        </Card>
      ) : null}

      {progress ? (
        <Card title="Progress">
          <ProgressMeter
            value={progress.percent}
            label={`${progress.completed_lessons} of ${progress.required_lessons} required lessons complete`}
          />
        </Card>
      ) : null}
    </>
  );
}

function BackLink() {
  return (
    <div>
      <Link href="/manage/assignments" className="text-sm text-zinc-500 hover:underline dark:text-zinc-400">
        ← All assignments
      </Link>
    </div>
  );
}