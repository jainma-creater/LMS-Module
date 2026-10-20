import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { Learner } from "@/lib/types";

import LearnerForm from "../../../components/learner-form";
import { AccessNotice, Card, PageHeader, StatusBadge } from "../../../components/ui";

export default function LearnerDetailPage(props: PageProps<"/manage/learners/[id]">) {
  return (
    <div className="flex flex-col gap-6">
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading learner…
          </p>
        }
      >
        <LearnerDetailView params={props.params} />
      </Suspense>
    </div>
  );
}

async function LearnerDetailView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await apiGet<Learner>(`/manage/learners/${id}`);

  if (!detail.ok) {
    return (
      <>
        <BackLink />
        <AccessNotice kind={detail.kind} message={detail.message} />
      </>
    );
  }

  const learner = detail.data;

  return (
    <>
      <BackLink />
      <PageHeader
        title={learner.full_name}
        description={learner.email}
        action={<StatusBadge value={learner.status} />}
      />

      <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-zinc-500">Employee ID</dt>
          <dd className="font-mono font-medium">{learner.employee_id}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Email</dt>
          <dd className="font-medium">{learner.email}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Department</dt>
          <dd className="font-medium">{learner.department ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Business Unit</dt>
          <dd className="font-medium">{learner.business_unit ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Identity Link</dt>
          <dd className="font-medium">
            {learner.user_id ? (
              <span className="font-mono text-xs">{learner.user_id}</span>
            ) : (
              <span className="text-zinc-500">Not linked</span>
            )}
          </dd>
        </div>
      </dl>

      <Card title="Edit learner">
        <LearnerForm learner={detail.data} />
      </Card>
    </>
  );
}

function BackLink() {
  return (
    <div>
      <Link href="/manage/learners" className="text-sm text-zinc-500 hover:underline dark:text-zinc-400">
        ← All learners
      </Link>
    </div>
  );
}