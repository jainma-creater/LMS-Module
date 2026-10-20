import Link from "next/link";
import { Suspense } from "react";

import {
  archiveCourse,
  assignEnrollment,
  createModule,
  createQuiz,
  deleteLesson,
  publishCourse,
  reorderLessons,
} from "@/app/actions";
import { apiGet } from "@/lib/api";
import type { CourseContent, CourseRecord } from "@/lib/types";

import ActionForm from "../../components/action-form";
import CourseForm from "../../components/course-form";
import { Field, inputClass } from "../../components/fields";
import LessonForm from "../../components/lesson-form";
import {
  AccessNotice,
  Card,
  EmptyState,
  Notice,
  PageHeader,
  StatusBadge,
} from "../../components/ui";

interface CourseEnrollments {
  course_id: string;
  enrollments: {
    id: string;
    learner_id: string;
    status: string;
    due_at: string | null;
    overdue: boolean;
  }[];
}

export default function ManageCoursePage(props: PageProps<"/manage/[courseId]">) {
  return (
    <div className="flex flex-col gap-6">
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading course…
          </p>
        }
      >
        <ManageView params={props.params} />
      </Suspense>
    </div>
  );
}

async function ManageView({ params }: { params: Promise<{ courseId: string }> }) {
  const { courseId } = await params;

  // courses:write gates every authoring control on this page. Course detail
  // alone is readable by learners, so it cannot be used as the access check.
  const access = await apiGet<CourseRecord[]>("/admin/courses");
  if (!access.ok) {
    return (
      <>
        <BackLink />
        <AccessNotice kind={access.kind} message={access.message} />
      </>
    );
  }

  const [detail, content, enrollments] = await Promise.all([
    apiGet<CourseRecord>(`/courses/${courseId}`),
    apiGet<CourseContent>(`/courses/${courseId}/content`),
    apiGet<CourseEnrollments>(`/courses/${courseId}/enrollments`),
  ]);

  if (!detail.ok) {
    return (
      <>
        <BackLink />
        <AccessNotice kind={detail.kind} message={detail.message} />
      </>
    );
  }

  const course = detail.data;
  const readOnly = course.status === "archived";

  return (
    <>
      <BackLink />
      <PageHeader
        title={course.title}
        description={course.short_description ?? "No summary provided."}
        action={<StatusBadge value={course.status} />}
      />

      <div className="flex flex-wrap gap-3">
        <ActionForm action={publishCourse} submitLabel="Publish">
          <input type="hidden" name="course_id" value={course.id} />
        </ActionForm>
        <ActionForm action={archiveCourse} submitLabel="Archive">
          <input type="hidden" name="course_id" value={course.id} />
        </ActionForm>
      </div>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-medium">Course details</h2>
        {readOnly ? (
          <Notice tone="warning">Archived courses are read-only.</Notice>
        ) : (
          <Card title="Edit course">
            <CourseForm course={course} />
          </Card>
        )}
      </section>

      {!content.ok ? (
        <AccessNotice kind={content.kind} message={content.message} />
      ) : (
        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-medium">Curriculum</h2>
          {content.data.modules.map((module) => (
            <Card
              key={module.id}
              title={module.title}
              meta={<span className="text-xs text-zinc-500">{module.lessons.length} lessons</span>}
            >
              {module.lessons.length > 0 ? (
                <ul className="mb-3 flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
                  {module.lessons.map((lesson) => (
                    <li key={lesson.id} className="flex flex-col gap-2 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <span>
                          {lesson.title}
                          <span className="ml-2 text-xs uppercase tracking-wide text-zinc-400">
                            {lesson.content_type.replace(/_/g, " ")}
                            {lesson.estimated_minutes ? ` · ${lesson.estimated_minutes} min` : ""}
                            {lesson.is_required ? "" : " · optional"}
                          </span>
                        </span>
                        {readOnly ? null : (
                          <ActionForm action={deleteLesson} submitLabel="Remove">
                            <input type="hidden" name="course_id" value={course.id} />
                            <input type="hidden" name="lesson_id" value={lesson.id} />
                          </ActionForm>
                        )}
                      </div>
                      {readOnly ? null : (
                        <details className="text-sm">
                          <summary className="cursor-pointer text-blue-700 dark:text-blue-400">
                            Edit lesson
                          </summary>
                          <div className="mt-3">
                            <LessonForm courseId={course.id} moduleId={module.id} lesson={lesson} />
                          </div>
                        </details>
                      )}
                    </li>
                  ))}
                </ul>
              ) : null}

              {readOnly ? null : (
                <>
                  <details className="text-sm">
                    <summary className="cursor-pointer text-blue-700 dark:text-blue-400">
                      Add lesson
                    </summary>
                    <div className="mt-3">
                      <LessonForm courseId={course.id} moduleId={module.id} />
                    </div>
                  </details>

                  {module.lessons.length > 0 ? (
                    <details className="mt-3 text-sm">
                      <summary className="cursor-pointer text-blue-700 dark:text-blue-400">
                        Reorder lessons
                      </summary>
                      <ActionForm
                        action={reorderLessons}
                        submitLabel="Save order"
                        className="mt-3 flex flex-col gap-3"
                      >
                        <input type="hidden" name="course_id" value={course.id} />
                        <input type="hidden" name="module_id" value={module.id} />
                        <Field label="Lesson ids in order (comma-separated)">
                          <input
                            name="ordered_ids"
                            defaultValue={module.lessons.map((lesson) => lesson.id).join(",")}
                            className={inputClass}
                          />
                        </Field>
                      </ActionForm>
                    </details>
                  ) : null}
                </>
              )}
            </Card>
          ))}

          {content.data.modules.length === 0 ? (
            <EmptyState
              title="No modules yet"
              description="Add a module, then lessons. A course needs at least one module and one lesson to publish."
            />
          ) : null}

          {readOnly ? null : (
            <Card title="Add module">
              <ActionForm action={createModule} submitLabel="Add module">
                <input type="hidden" name="course_id" value={course.id} />
                <Field label="Title">
                  <input name="title" required className={inputClass} />
                </Field>
                <Field label="Description">
                  <textarea name="description" rows={2} className={inputClass} />
                </Field>
              </ActionForm>
            </Card>
          )}
        </section>
      )}

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-medium">Assignments</h2>
        <Card title="Assign a learner">
          <ActionForm action={assignEnrollment} submitLabel="Assign learner">
            <input type="hidden" name="course_id" value={course.id} />
            <Field label="Learner ID">
              <input
                name="learner_id"
                required
                placeholder="00000000-0000-0000-0000-000000000000"
                className={inputClass}
              />
            </Field>
            <Field label="Due date">
              <input name="due_at" type="datetime-local" className={inputClass} />
            </Field>
          </ActionForm>
        </Card>
        {!enrollments.ok ? (
          <AccessNotice kind={enrollments.kind} message={enrollments.message} />
        ) : enrollments.data.enrollments.length === 0 ? (
          <EmptyState title="No enrollments" description="No learners are assigned to this course." />
        ) : (
          <ul className="flex flex-col gap-2 text-sm">
            {enrollments.data.enrollments.map((enrollment) => (
              <li
                key={enrollment.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-zinc-200 px-3 py-2 dark:border-zinc-800"
              >
                <span className="font-mono text-xs">{enrollment.learner_id}</span>
                <span className="flex items-center gap-3">
                  {enrollment.due_at ? (
                    <span className="text-zinc-500">
                      due {new Date(enrollment.due_at).toLocaleDateString()}
                    </span>
                  ) : null}
                  <StatusBadge value={enrollment.overdue ? "overdue" : enrollment.status} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-medium">Assessments</h2>
        <Card title="Create a quiz">
          <ActionForm action={createQuiz} submitLabel="Create quiz">
            <input type="hidden" name="course_id" value={course.id} />
            <Field label="Title">
              <input name="title" required className={inputClass} />
            </Field>
            <Field label="Description">
              <textarea name="description" rows={2} className={inputClass} />
            </Field>
            <div className="flex flex-wrap gap-3">
              <Field label="Pass score (%)">
                <input
                  name="pass_score"
                  type="number"
                  min={0}
                  max={100}
                  defaultValue={70}
                  className={inputClass}
                />
              </Field>
              <Field label="Attempt limit">
                <input name="attempt_limit" type="number" min={1} className={inputClass} />
              </Field>
            </div>
          </ActionForm>
        </Card>
      </section>
    </>
  );
}

function BackLink() {
  return (
    <Link href="/manage" className="text-sm text-zinc-500 hover:underline dark:text-zinc-400">
      ← Manage courses
    </Link>
  );
}
