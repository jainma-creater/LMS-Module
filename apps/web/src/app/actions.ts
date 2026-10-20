"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiDelete, apiGet, apiPatch, apiPost, apiPut, type ApiResult } from "@/lib/api";
import {
  validateCourseInput,
  validateLessonInput,
  validateLearnerInput,
  type FieldErrors,
} from "@/lib/authoring";
import type { FormState } from "@/lib/form";
import type {
  AttemptResult,
  AttemptStart,
  CourseDraft,
  PublishDraftResult,
  QuizDraft,
  QuizQuestionDraft,
  TrainingGenerationJob,
} from "@/lib/types";

type DataResult<T> = { ok: true; data: T } | { ok: false; message: string };

// Form fields arrive as strings; validation (and the API) decide what they mean.
function rawFields(formData: FormData): Record<string, string> {
  const values: Record<string, string> = {};
  formData.forEach((value, key) => {
    if (typeof value === "string") {
      values[key] = value;
    }
  });
  return values;
}

function invalid(errors: FieldErrors): FormState {
  return {
    status: "error",
    message: "Fix the highlighted fields and try again.",
    fieldErrors: errors,
  };
}

function field(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function optionalField(formData: FormData, key: string): string | null {
  const value = field(formData, key);
  return value.length > 0 ? value : null;
}

function fromResult(result: ApiResult<unknown>, successMessage: string): FormState {
  if (result.ok) {
    return { status: "success", message: successMessage };
  }
  return { status: "error", message: result.message };
}

async function run(
  operation: () => Promise<ApiResult<unknown>>,
  successMessage: string,
  revalidate: string[],
): Promise<FormState> {
  const state = fromResult(await operation(), successMessage);
  if (state.status === "success") {
    for (const path of revalidate) {
      revalidatePath(path);
    }
  }
  return state;
}

// --------------------------------------------------------------------------- //
// Courses
// --------------------------------------------------------------------------- //
// Full-record payloads: blank optional fields are sent as null so that an edit
// can clear them (the API treats an explicit null as "clear").
export async function createCourse(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const parsed = validateCourseInput(rawFields(formData));
  if (!parsed.ok) {
    return invalid(parsed.errors);
  }
  const result = await apiPost<{ id: string }>("/courses", parsed.value);
  if (!result.ok) {
    return { status: "error", message: result.message };
  }
  revalidatePath("/manage");
  revalidatePath("/courses", "layout");
  // Send the author straight to the new course to add modules and lessons.
  redirect(`/manage/${result.data.id}`);
}

export async function updateCourse(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  if (courseId.length === 0) {
    return { status: "error", message: "The course could not be identified." };
  }
  const parsed = validateCourseInput(rawFields(formData));
  if (!parsed.ok) {
    return invalid(parsed.errors);
  }
  const result = await apiPatch(`/courses/${courseId}`, parsed.value);
  if (!result.ok) {
    return { status: "error", message: result.message };
  }
  revalidatePath("/manage");
  revalidatePath(`/manage/${courseId}`);
  revalidatePath("/courses", "layout");
  revalidatePath("/catalog");
  return { status: "success", message: "Course saved." };
}

export async function publishCourse(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  return run(
    () => apiPost(`/courses/${courseId}/publish`),
    "Course published.",
    ["/manage", `/manage/${courseId}`, "/catalog"],
  );
}

export async function updateGroup(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const groupId = field(formData, "group_id");
  if (groupId.length === 0) {
    return { status: "error", message: "The group could not be identified." };
  }
  const name = field(formData, "name");
  if (name.length === 0) {
    return { status: "error", message: "A group name is required." };
  }
  return run(
    () =>
      apiPatch(`/learning-groups/${groupId}`, {
        name,
        description: optionalField(formData, "description"),
        kind: field(formData, "kind") || "team",
        status: field(formData, "status") || "active",
      }),
    "Group saved.",
    ["/manage/groups"],
  );
}

export async function archiveCourse(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  return run(
    () => apiPost(`/courses/${courseId}/archive`),
    "Course archived.",
    ["/manage", `/manage/${courseId}`, "/catalog"],
  );
}

export async function createModule(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  const title = field(formData, "title");
  if (title.length === 0) {
    return { status: "error", message: "A module title is required." };
  }
  return run(
    () =>
      apiPost(`/courses/${courseId}/modules`, {
        title,
        description: optionalField(formData, "description"),
      }),
    "Module added.",
    [`/manage/${courseId}`],
  );
}

export async function createLesson(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  const moduleId = field(formData, "module_id");
  const parsed = validateLessonInput(rawFields(formData), formData.get("is_required") === "on");
  if (!parsed.ok) {
    return invalid(parsed.errors);
  }
  return run(
    () => apiPost(`/modules/${moduleId}/lessons`, parsed.value),
    "Lesson added.",
    [`/manage/${courseId}`],
  );
}

export async function updateLesson(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  const lessonId = field(formData, "lesson_id");
  if (lessonId.length === 0) {
    return { status: "error", message: "The lesson could not be identified." };
  }
  const parsed = validateLessonInput(rawFields(formData), formData.get("is_required") === "on");
  if (!parsed.ok) {
    return invalid(parsed.errors);
  }
  return run(
    () => apiPatch(`/lessons/${lessonId}`, parsed.value),
    "Lesson saved.",
    [`/manage/${courseId}`],
  );
}

// --------------------------------------------------------------------------- //
// Learners
// --------------------------------------------------------------------------- //
export async function updateLearner(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const learnerId = field(formData, "learner_id");
  if (learnerId.length === 0) {
    return { status: "error", message: "The learner could not be identified." };
  }
  const parsed = validateLearnerInput(rawFields(formData));
  if (!parsed.ok) {
    return invalid(parsed.errors);
  }
  return run(
    () => apiPatch(`/learners/${learnerId}`, parsed.value),
    "Learner saved.",
    ["/manage/learners", `/manage/learners/${learnerId}`],
  );
}

export async function deleteLesson(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  const lessonId = field(formData, "lesson_id");
  const result = await apiDelete(`/lessons/${lessonId}`);
  if (result.ok) {
    revalidatePath(`/manage/${courseId}`);
    return { status: "success", message: "Lesson removed." };
  }
  return { status: "error", message: result.message };
}

export async function reorderLessons(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  const moduleId = field(formData, "module_id");
  const ids = field(formData, "ordered_ids")
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
  if (ids.length === 0) {
    return { status: "error", message: "Provide the lesson order." };
  }
  return run(
    () => apiPut(`/modules/${moduleId}/lessons/order`, { ordered_ids: ids }),
    "Lesson order updated.",
    [`/manage/${courseId}`],
  );
}

// --------------------------------------------------------------------------- //
// Enrollments
// --------------------------------------------------------------------------- //
export async function assignEnrollment(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const courseId = field(formData, "course_id");
  const learnerId = field(formData, "learner_id");
  if (learnerId.length === 0) {
    return { status: "error", message: "A learner id is required." };
  }
  const dueAt = optionalField(formData, "due_at");
  return run(
    () =>
      apiPost(`/courses/${courseId}/enrollments`, {
        learner_id: learnerId,
        due_at: dueAt,
      }),
    "Learner assigned.",
    [`/manage/${courseId}`, "/learning"],
  );
}

// --------------------------------------------------------------------------- //
// Progress
// --------------------------------------------------------------------------- //
export async function recordLessonProgress(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const lessonId = field(formData, "lesson_id");
  const status = field(formData, "status") || "completed";
  const position = optionalField(formData, "last_position");
  const result = await apiPut(`/lessons/${lessonId}/progress`, {
    status,
    last_position: position === null ? null : Number(position),
  });
  if (result.ok) {
    revalidatePath("/learning");
    revalidatePath("/progress");
    return { status: "success", message: "Progress saved." };
  }
  return { status: "error", message: result.message };
}

// --------------------------------------------------------------------------- //
// Quizzes
// --------------------------------------------------------------------------- //
export async function createQuiz(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const title = field(formData, "title");
  if (title.length === 0) {
    return { status: "error", message: "A quiz title is required." };
  }
  const passScore = optionalField(formData, "pass_score");
  const attemptLimit = optionalField(formData, "attempt_limit");
  return run(
    () =>
      apiPost("/quizzes", {
        title,
        description: optionalField(formData, "description"),
        course_id: optionalField(formData, "course_id"),
        lesson_id: optionalField(formData, "lesson_id"),
        pass_score: passScore === null ? 70 : Number(passScore),
        attempt_limit: attemptLimit === null ? null : Number(attemptLimit),
      }),
    "Quiz created.",
    ["/manage"],
  );
}

export async function addQuestion(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const quizId = field(formData, "quiz_id");
  const prompt = field(formData, "prompt");
  if (prompt.length === 0) {
    return { status: "error", message: "A prompt is required." };
  }
  // Options are entered one per line as "id=text"; ids double as answer keys.
  const options = field(formData, "options")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      const separator = line.indexOf("=");
      if (separator === -1) {
        return { id: line, text: line };
      }
      return { id: line.slice(0, separator).trim(), text: line.slice(separator + 1).trim() };
    })
    .filter((option) => option.id.length > 0 && option.text.length > 0);
  if (options.length < 2) {
    return { status: "error", message: "Provide at least two options (id=text per line)." };
  }
  const answerKey = field(formData, "answer_key")
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
  if (answerKey.length === 0) {
    return { status: "error", message: "Provide at least one answer key." };
  }
  return run(
    () =>
      apiPost(`/quizzes/${quizId}/questions`, {
        question_type: field(formData, "question_type") || "single_choice",
        prompt,
        options,
        answer_key: answerKey,
        explanation: optionalField(formData, "explanation"),
        points: Number(field(formData, "points") || "1"),
      }),
    "Question added.",
    [`/quizzes/${quizId}`],
  );
}

export async function publishQuiz(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const quizId = field(formData, "quiz_id");
  return run(
    () => apiPost(`/quizzes/${quizId}/publish`),
    "Quiz published.",
    [`/quizzes/${quizId}`],
  );
}

// --------------------------------------------------------------------------- //
// Attempts (data-returning actions for the quiz runner)
// --------------------------------------------------------------------------- //
export async function beginAttempt(quizId: string): Promise<DataResult<AttemptStart>> {
  const result = await apiPost<AttemptStart>(`/quizzes/${quizId}/attempts`);
  if (result.ok) {
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}

export async function completeAttempt(
  quizId: string,
  attemptId: string,
  answers: { question_id: string; selected: string[] }[],
): Promise<DataResult<AttemptResult>> {
  const result = await apiPost<AttemptResult>(`/attempts/${attemptId}/submit`, { answers });
  if (result.ok) {
    revalidatePath(`/quizzes/${quizId}`);
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}

// --------------------------------------------------------------------------- //
// AI Training Studio actions
// --------------------------------------------------------------------------- //
export async function generateTrainingDraft(
  input:
    | FormData
    | {
        topic?: string;
        language?: string;
        target_duration_minutes?: number;
        audience?: string;
        include_quiz?: boolean;
        include_video?: boolean;
      },
): Promise<DataResult<TrainingGenerationJob>> {
  const result = await apiPost<TrainingGenerationJob>("/studio/generate", input, 120_000);
  if (result.ok) {
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}

export async function getGenerationJob(
  jobId: string,
): Promise<DataResult<TrainingGenerationJob>> {
  const result = await apiGet<TrainingGenerationJob>(`/studio/jobs/${jobId}`);
  if (result.ok) {
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}

export async function updateTrainingDraft(
  jobId: string,
  courseDraft: CourseDraft,
  quizDraft: QuizDraft | null,
): Promise<DataResult<TrainingGenerationJob>> {
  const result = await apiPatch<TrainingGenerationJob>(`/studio/jobs/${jobId}`, {
    course: courseDraft,
    quiz: quizDraft,
  });
  if (result.ok) {
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}

export async function regenerateQuizQuestion(
  jobId: string,
  questionIndex: number,
  topicHint?: string,
): Promise<DataResult<QuizQuestionDraft>> {
  const result = await apiPost<QuizQuestionDraft>(
    `/studio/jobs/${jobId}/regenerate-question`,
    {
      question_index: questionIndex,
      topic_hint: topicHint?.trim() || null,
    },
  );
  if (result.ok) {
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}

export async function publishTrainingDraft(
  jobId: string,
  options: {
    assign_to_group_id?: string | null;
    assign_to_learner_id?: string | null;
    due_days?: number | null;
  },
): Promise<DataResult<PublishDraftResult>> {
  const result = await apiPost<PublishDraftResult>(
    `/studio/jobs/${jobId}/publish`,
    {
      assign_to_group_id: options.assign_to_group_id || null,
      assign_to_learner_id: options.assign_to_learner_id || null,
      due_days: options.due_days || null,
    },
  );
  if (result.ok) {
    revalidatePath("/manage");
    revalidatePath("/courses", "layout");
    revalidatePath("/learning");
    revalidatePath("/progress");
    return { ok: true, data: result.data };
  }
  return { ok: false, message: result.message };
}
