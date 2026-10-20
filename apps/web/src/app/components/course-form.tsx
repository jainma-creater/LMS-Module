"use client";

import { createCourse, updateCourse } from "@/app/actions";
import { COURSE_DIFFICULTIES, LIMITS } from "@/lib/authoring";
import type { CourseRecord } from "@/lib/types";

import { AuthoringForm, SelectField, TextAreaField, TextField } from "./authoring-form";

const DIFFICULTY_OPTIONS = COURSE_DIFFICULTIES.map((level) => ({
  value: level,
  label: level.charAt(0).toUpperCase() + level.slice(1),
}));

/**
 * Create or edit a course. With `course` set, the form edits that course; the
 * slug is shown read-only because the API generates it from the title at creation.
 */
export default function CourseForm({ course }: { course?: CourseRecord }) {
  const isEdit = course !== undefined;
  return (
    <AuthoringForm
      action={isEdit ? updateCourse : createCourse}
      idPrefix={course ? `course-${course.id}` : "course-new"}
      submitLabel={isEdit ? "Save course" : "Create course"}
      pendingLabel={isEdit ? "Saving…" : "Creating…"}
    >
      {course ? <input type="hidden" name="course_id" value={course.id} /> : null}

      {course ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Slug: <span className="font-mono">{course.slug}</span>
          <span className="block text-xs text-zinc-500">
            Generated from the title when the course was created. It is not editable here.
          </span>
        </p>
      ) : null}

      <TextField
        name="title"
        label="Title"
        required
        maxLength={LIMITS.title}
        defaultValue={course?.title ?? ""}
      />
      <TextAreaField
        name="short_description"
        label="Short description"
        hint={`Shown on course cards. Up to ${LIMITS.shortDescription} characters.`}
        rows={2}
        maxLength={LIMITS.shortDescription}
        defaultValue={course?.short_description ?? ""}
      />
      <TextAreaField
        name="description"
        label="Full description"
        rows={5}
        maxLength={LIMITS.description}
        defaultValue={course?.description ?? ""}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          name="category"
          label="Category"
          maxLength={LIMITS.category}
          defaultValue={course?.category ?? ""}
        />
        <SelectField
          name="difficulty_level"
          label="Difficulty"
          options={DIFFICULTY_OPTIONS}
          defaultValue={course?.difficulty_level ?? "beginner"}
        />
        <TextField
          name="estimated_minutes"
          label="Estimated duration (minutes)"
          type="number"
          min={0}
          max={LIMITS.minutesMax}
          hint="Leave blank if unknown."
          defaultValue={course?.estimated_minutes?.toString() ?? ""}
        />
        <TextField
          name="thumbnail_url"
          label="Thumbnail URL"
          type="url"
          maxLength={LIMITS.thumbnailUrl}
          hint="Full https:// link to an image. Leave blank for none."
          defaultValue={course?.thumbnail_url ?? ""}
        />
      </div>
      <TextField
        name="tags"
        label="Tags"
        hint={`Comma-separated. Saved in lower case, up to ${LIMITS.tagCount} tags.`}
        defaultValue={course?.tags.join(", ") ?? ""}
      />
    </AuthoringForm>
  );
}
