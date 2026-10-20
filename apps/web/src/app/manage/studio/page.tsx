import { Suspense } from "react";
import { connection } from "next/server";
import { apiGet } from "@/lib/api";
import type { LearningGroup } from "@/lib/types";
import { AccessNotice, PageHeader } from "../../components/ui";
import StudioClient from "./studio-client";

export const metadata = {
  title: "AI Training Studio · AI LMS",
  description: "Generate complete corporate training courses, video storyboards, and quizzes in 3–5 clicks.",
};

export default function TrainingStudioPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="AI Training Studio"
        description="Create complete courses, video storyboards, synchronized captions, and assessments from topics or uploaded documents in 3–5 clicks."
      />
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading Studio…
          </p>
        }
      >
        <StudioView />
      </Suspense>
    </div>
  );
}

async function StudioView() {
  await connection();
  const groupsRes = await apiGet<{ items: LearningGroup[] }>("/manage/learning-groups?limit=100");

  let groups: LearningGroup[] = [];
  if (groupsRes.ok && groupsRes.data?.items) {
    groups = groupsRes.data.items.filter((g) => g.status === "active");
  } else if (!groupsRes.ok && groupsRes.status === 403) {
    return <AccessNotice kind={groupsRes.kind} message={groupsRes.message} />;
  }

  return <StudioClient groups={groups} />;
}
