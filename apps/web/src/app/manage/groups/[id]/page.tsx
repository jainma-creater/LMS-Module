import Link from "next/link";
import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { LearningGroup, GroupMember } from "@/lib/types";

import GroupForm from "../../../components/group-form";
import { AccessNotice, Card, PageHeader, StatusBadge } from "../../../components/ui";

export default function GroupDetailPage(props: PageProps<"/manage/groups/[id]">) {
  return (
    <div className="flex flex-col gap-6">
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading group…
          </p>
        }
      >
        <GroupDetailView params={props.params} />
      </Suspense>
    </div>
  );
}

async function GroupDetailView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await apiGet<{ group: LearningGroup; members: GroupMember[] }>(`/manage/learning-groups/${id}?include_members=true`);

  if (!detail.ok) {
    return (
      <>
        <BackLink />
        <AccessNotice kind={detail.kind} message={detail.message} />
      </>
    );
  }

  const group = detail.data.group;
  const members = detail.data.members;

  return (
    <>
      <BackLink />
      <PageHeader
        title={group.name}
        description={group.description ?? undefined}
        action={<StatusBadge value={group.status} />}
      />

      <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-zinc-500">Kind</dt>
          <dd className="font-medium capitalize">{group.kind}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Members</dt>
          <dd className="font-medium">{group.member_count}</dd>
        </div>
      </dl>

      <Card title="Edit group">
        <GroupForm group={group} />
      </Card>

      <Card title="Members">
        <GroupMembersList groupId={group.id} members={members} />
      </Card>
    </>
  );
}

function GroupMembersList({ groupId, members }: { groupId: string; members: GroupMember[] }) {
  if (members.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 px-6 py-10 text-center dark:border-zinc-700">
        <p className="font-medium text-zinc-800 dark:text-zinc-200">No members yet</p>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Add learners to this group to enable bulk course assignments.
        </p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-4">
      {members.map((member) => (
        <li key={member.membership_id} className="flex flex-col gap-2 py-3 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <span className="font-medium text-zinc-800 dark:text-zinc-200">{member.full_name}</span>
              <span className="ml-2 text-xs text-zinc-500 font-mono">{member.employee_id}</span>
              <span className="ml-2 text-xs text-zinc-500">{member.email}</span>
              <span className="ml-2 text-xs text-zinc-500 capitalize">{member.learner_status}</span>
            </div>
            {member.removed_at ? (
              <span className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                Removed {new Date(member.removed_at).toLocaleDateString()}
              </span>
            ) : (
              <form action={`/manage/groups/${groupId}/members/${member.learner_id}`} method="post" className="flex items-center gap-2">
                <input type="hidden" name="learner_id" value={member.learner_id} />
                <button
                  type="submit"
                  className="text-sm text-red-600 hover:underline dark:text-red-400"
                >
                  Remove
                </button>
              </form>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function BackLink() {
  return (
    <div>
      <Link href="/manage/groups" className="text-sm text-zinc-500 hover:underline dark:text-zinc-400">
        ← All groups
      </Link>
    </div>
  );
}