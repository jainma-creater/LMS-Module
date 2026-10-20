// Pure authoring validation and payload builders.
//
// Rules mirror services/api/app/modules/courses/schemas.py. The API is the
// authority; this module gives users field-level feedback before a request is
// sent. Keep the two in step when either side changes. This file has no imports
// so it can be exercised directly by the Node test runner.

export type FieldErrors = Record<string, string>;

export type Validated<T> = { ok: true; value: T } | { ok: false; errors: FieldErrors };

export const COURSE_DIFFICULTIES = ["beginner", "intermediate", "advanced"] as const;
export type CourseDifficulty = (typeof COURSE_DIFFICULTIES)[number];

export const LESSON_CONTENT_TYPES = ["text", "video_url", "external_link"] as const;
export type LessonContentKind = (typeof LESSON_CONTENT_TYPES)[number];

export const LIMITS = {
  title: 255,
  shortDescription: 500,
  description: 20000,
  category: 100,
  thumbnailUrl: 500,
  tagCount: 20,
  tagLength: 50,
  minutesMax: 60000,
  lessonContent: 100000,
} as const;

export type LearnerStatus = "active" | "inactive";

export interface LearnerPayload {
  employee_id: string;
  first_name: string;
  last_name: string;
  email: string;
  department: string | null;
  business_unit: string | null;
  status: LearnerStatus;
  user_id: string | null;
}

export function validateLearnerInput(raw: Record<string, string>): Validated<LearnerPayload> {
  const errors: FieldErrors = {};
  const employee_id = requiredText(raw, "employee_id", 64, errors, "Employee ID");
  const first_name = requiredText(raw, "first_name", 100, errors, "First name");
  const last_name = requiredText(raw, "last_name", 100, errors, "Last name");
  const email = requiredText(raw, "email", 320, errors, "Email");
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    errors.email = "Email must be a valid address.";
  }
  const department = optionalText(raw, "department", 120, errors, "Department");
  const business_unit = optionalText(raw, "business_unit", 120, errors, "Business Unit");
  const status = (raw.status ?? "active").trim();
  if (!["active", "inactive"].includes(status)) {
    errors.status = "Status must be active or inactive.";
  }
  let user_id: string | null = null;
  if (raw.user_id) {
    const uid = raw.user_id.trim();
    if (uid.length > 0) {
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(uid)) {
        errors.user_id = "User ID must be a valid UUID.";
      } else {
        user_id = uid;
}
    }
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    value: {
      employee_id,
      first_name,
      last_name,
      email,
      department,
      business_unit,
      status: status as LearnerStatus,
      user_id,
    },
  };
}

export interface CoursePayload {
  title: string;
  short_description: string | null;
  description: string | null;
  category: string | null;
  difficulty_level: CourseDifficulty;
  estimated_minutes: number | null;
  thumbnail_url: string | null;
  tags: string[];
}

export interface LessonPayload {
  title: string;
  description: string | null;
  content_type: LessonContentKind;
  content: string | null;
  estimated_minutes: number | null;
  is_required: boolean;
}

const HTTP_URL_PREFIX = /^https?:\/\/[^\s/?#]+/i;

/** True only for absolute http(s) URLs with a host, matching the API rule. */
export function isHttpUrl(value: string): boolean {
  if (!HTTP_URL_PREFIX.test(value)) {
    return false;
  }
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}



function optionalText(
  raw: Record<string, string>,
  key: string,
  max: number,
  errors: FieldErrors,
  label: string,
): string | null {
  const value = (raw[key] ?? "").trim();
  if (value.length === 0) {
    return null;
  }
  if (value.length > max) {
    errors[key] = `${label} must be ${max} characters or fewer.`;
  }
  return value;
}

function requiredText(
  raw: Record<string, string>,
  key: string,
  max: number,
  errors: FieldErrors,
  label: string,
): string {
  const value = (raw[key] ?? "").trim();
  if (value.length === 0) {
    errors[key] = `${label} is required.`;
  } else if (value.length > max) {
    errors[key] = `${label} must be ${max} characters or fewer.`;
  }
  return value;
}

/** Empty input means "no value" (null); otherwise a whole number from 0 to the maximum. */
export function parseMinutes(raw: string | undefined): Validated<number | null> {
  const value = (raw ?? "").trim();
  if (value.length === 0) {
    return { ok: true, value: null };
  }
  if (!/^\d+$/.test(value)) {
    return {
      ok: false,
      errors: { estimated_minutes: "Enter a whole number of minutes (0 or more)." },
    };
  }
  const minutes = Number(value);
  if (minutes > LIMITS.minutesMax) {
    return {
      ok: false,
      errors: {
        estimated_minutes: `Duration must be ${LIMITS.minutesMax} minutes or fewer.`,
      },
    };
  }
  return { ok: true, value: minutes };
}

/**
 * Split a comma-separated tag list. Tags are trimmed and lower-cased, empties
 * are dropped, and duplicates are removed while keeping first-seen order.
 */
export function parseTags(raw: string | undefined): Validated<string[]> {
  const tags: string[] = [];
  for (const piece of (raw ?? "").split(",")) {
    const tag = piece.trim().toLowerCase();
    if (tag.length === 0 || tags.includes(tag)) {
      continue;
    }
    if (tag.length > LIMITS.tagLength) {
      return {
        ok: false,
        errors: { tags: `Each tag must be ${LIMITS.tagLength} characters or fewer.` },
      };
    }
    tags.push(tag);
  }
  if (tags.length > LIMITS.tagCount) {
    return { ok: false, errors: { tags: `Use at most ${LIMITS.tagCount} tags.` } };
  }
  return { ok: true, value: tags };
}

export function validateCourseInput(raw: Record<string, string>): Validated<CoursePayload> {
  const errors: FieldErrors = {};
  const title = requiredText(raw, "title", LIMITS.title, errors, "Title");
  const shortDescription = optionalText(
    raw,
    "short_description",
    LIMITS.shortDescription,
    errors,
    "Short description",
  );
  const description = optionalText(raw, "description", LIMITS.description, errors, "Description");
  const category = optionalText(raw, "category", LIMITS.category, errors, "Category");

  const difficulty = (raw.difficulty_level ?? "beginner").trim();
  if (!(COURSE_DIFFICULTIES as readonly string[]).includes(difficulty)) {
    errors.difficulty_level = "Choose beginner, intermediate, or advanced.";
  }

  const minutes = parseMinutes(raw.estimated_minutes);
  if (!minutes.ok) {
    Object.assign(errors, minutes.errors);
  }

  let thumbnail: string | null = null;
  const thumbnailRaw = (raw.thumbnail_url ?? "").trim();
  if (thumbnailRaw.length > 0) {
    if (thumbnailRaw.length > LIMITS.thumbnailUrl) {
      errors.thumbnail_url = `Thumbnail URL must be ${LIMITS.thumbnailUrl} characters or fewer.`;
    } else if (!isHttpUrl(thumbnailRaw)) {
      errors.thumbnail_url = "Enter a full http:// or https:// URL.";
    }
    thumbnail = thumbnailRaw;
  }

  const tags = parseTags(raw.tags);
  if (!tags.ok) {
    Object.assign(errors, tags.errors);
  }

  if (Object.keys(errors).length > 0 || !minutes.ok || !tags.ok) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    value: {
      title,
      short_description: shortDescription,
      description,
      category,
      difficulty_level: difficulty as CourseDifficulty,
      estimated_minutes: minutes.value,
      thumbnail_url: thumbnail,
      tags: tags.value,
    },
  };
}

export function validateLessonInput(
  raw: Record<string, string>,
  isRequired: boolean,
): Validated<LessonPayload> {
  const errors: FieldErrors = {};
  const title = requiredText(raw, "title", LIMITS.title, errors, "Title");
  const description = optionalText(raw, "description", LIMITS.description, errors, "Description");

  const contentType = (raw.content_type ?? "").trim();
  if (!(LESSON_CONTENT_TYPES as readonly string[]).includes(contentType)) {
    errors.content_type = "Choose text, video link, or external link.";
  }

  const content = (raw.content ?? "").trim();
  if (contentType === "text") {
    if (content.length > LIMITS.lessonContent) {
      errors.content = `Content must be ${LIMITS.lessonContent} characters or fewer.`;
    }
  } else if (contentType === "video_url" || contentType === "external_link") {
    if (content.length === 0) {
      errors.content = "Enter the link for this lesson.";
    } else if (content.length > LIMITS.lessonContent) {
      errors.content = `Content must be ${LIMITS.lessonContent} characters or fewer.`;
    } else if (!isHttpUrl(content)) {
      errors.content = "Enter a full http:// or https:// URL.";
    }
  }

  const minutes = parseMinutes(raw.estimated_minutes);
  if (!minutes.ok) {
    Object.assign(errors, minutes.errors);
  }

  if (Object.keys(errors).length > 0 || !minutes.ok) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    value: {
      title,
      description,
      content_type: contentType as LessonContentKind,
      content: content.length > 0 ? content : null,
      estimated_minutes: minutes.value,
      is_required: isRequired,
    },
  };
}
