import { Suspense } from "react";

import { apiGet } from "@/lib/api";
import type { CourseContent, CourseDetail, CourseProgress } from "@/lib/types";

import LessonPlayer from "../../components/lesson-player";
import { AccessNotice } from "../../components/ui";

export default function LearnPage(props: PageProps<"/learn/[courseId]">) {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col">
      <Suspense fallback={<PlayerSkeleton />}>
        <LearnView params={props.params} searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

function PlayerSkeleton() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10" aria-hidden="true">
      <div className="skeleton h-96 rounded-xl" />
    </div>
  );
}

async function LearnView({
  params,
  searchParams,
}: {
  params: Promise<{ courseId: string }>;
  searchParams: Promise<{ lesson?: string | string[] }>;
}) {
  const { courseId } = await params;
  const query = await searchParams;

  const [detail, content, progress] = await Promise.all([
    apiGet<CourseDetail>(`/courses/${courseId}`),
    apiGet<CourseContent>(`/courses/${courseId}/content`),
    apiGet<CourseProgress>(`/courses/${courseId}/progress`),
  ]);

  if (!detail.ok) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10">
        <AccessNotice kind={detail.kind} message={detail.message} />
      </div>
    );
  }

  if (!content.ok) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10">
        <AccessNotice kind={content.kind} message={content.message} />
      </div>
    );
  }

  const progressByLesson: Record<string, string> = {};
  if (progress.ok) {
    for (const row of progress.data.lessons) {
      progressByLesson[row.lesson_id] = row.status;
    }
  }

  const requested = Array.isArray(query.lesson) ? query.lesson[0] : query.lesson;

  return (
    <LessonPlayer
      course={detail.data}
      modules={content.data.modules}
      progressByLesson={progressByLesson}
      requestedLessonId={requested ?? null}
    />
  );
}
