"use client";

import { createLesson, updateLesson } from "@/app/actions";
import { LIMITS } from "@/lib/authoring";
import type { Lesson } from "@/lib/types";

import { AuthoringForm, CheckboxField, SelectField, TextAreaField, TextField } from "./authoring-form";

const CONTENT_OPTIONS = [
  { value: "text", label: "Text" },
  { value: "video_url", label: "Video link" },
  { value: "external_link", label: "External link" },
] as const;

// Static hint covering every type: a content-type-specific hint would go stale
// when the form resets after a successful create.
const CONTENT_HINT =
  "Text lessons: the lesson body (optional). Video and external links: a full https:// URL.";

/**
 * Add a lesson to a module (`lesson` unset) or edit an existing lesson.
 * Moving a lesson between modules is not supported by the API, so the module is fixed.
 */
export default function LessonForm({
  courseId,
  moduleId,
  lesson,
}: {
  courseId: string;
  moduleId: string;
  lesson?: Lesson;
}) {
  const isEdit = lesson !== undefined;
  return (
    <AuthoringForm
      action={isEdit ? updateLesson : createLesson}
      idPrefix={lesson ? `lesson-${lesson.id}` : `lesson-new-${moduleId}`}
      submitLabel={isEdit ? "Save lesson" : "Add lesson"}
      pendingLabel={isEdit ? "Saving…" : "Adding…"}
      resetOnSuccess={!isEdit}
    >
      <input type="hidden" name="course_id" value={courseId} />
      {lesson ? (
        <input type="hidden" name="lesson_id" value={lesson.id} />
      ) : (
        <input type="hidden" name="module_id" value={moduleId} />
      )}

      <TextField
        name="title"
        label="Title"
        required
        maxLength={LIMITS.title}
        defaultValue={lesson?.title ?? ""}
      />
      <TextAreaField
        name="description"
        label="Description"
        rows={2}
        maxLength={LIMITS.description}
        defaultValue={lesson?.description ?? ""}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          name="content_type"
          label="Content type"
          options={CONTENT_OPTIONS.map((option) => ({ value: option.value, label: option.label }))}
          defaultValue={lesson?.content_type ?? "text"}
        />
        <TextField
          name="estimated_minutes"
          label="Estimated duration (minutes)"
          type="number"
          min={0}
          max={LIMITS.minutesMax}
          defaultValue={lesson?.estimated_minutes?.toString() ?? ""}
        />
      </div>
      <TextAreaField
        name="content"
        label="Content"
        hint={CONTENT_HINT}
        rows={4}
        maxLength={LIMITS.lessonContent}
        defaultValue={lesson?.content ?? ""}
      />
      <CheckboxField
        name="is_required"
        label="Required for completion"
        defaultChecked={lesson?.is_required ?? true}
      />
    </AuthoringForm>
  );
}
