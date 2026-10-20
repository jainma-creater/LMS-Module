# Low-Level Design: Course Catalog and Content

Scope: course, module, lesson, and tag persistence; the catalog query model; and the
course lifecycle. Enrollment, progress, and assessment design are covered by their
own modules.

## Tables

| Table | Key columns | Notes |
| --- | --- | --- |
| `courses` | `id`, `title`, `slug` (unique), `short_description` (≤500), `description`, `category`, `difficulty_level`, `estimated_minutes`, `thumbnail_url` (http(s)), `status`, `owner_id`, `version`, `published_at` | Indexes on `status`, `category`, and `(status, created_at)` for the catalog listing. |
| `course_tags` | `id`, `course_id` (FK, cascade), `tag` (≤50, lower-case) | Unique `(course_id, tag)`. Indexes on `course_id` and `tag`. Normalised so tag filtering is portable. |
| `modules` | `id`, `course_id`, `title`, `description`, `sort_order` | Index `(course_id, sort_order)`. |
| `lessons` | `id`, `module_id`, `title`, `description`, `content_type`, `content`, `estimated_minutes`, `is_required`, `sort_order` | Index `(module_id, sort_order)`. |

Migrations: `0003_core_lms` created the base tables; `0004_course_catalog_content` adds
the catalog columns, `course_tags`, and `lessons.description`, and rewrites legacy
`content_type` values (`link` to `external_link`, `video` to `video_url`). Downgrade
reverses all of it. Applied migrations are never edited.

`0007_query_indexes` adds composite indexes for the hot read paths
(`courses(status, created_at)`, `lesson_progress(user_id, status)`,
`course_completions(user_id, completed_at)`, `enrollments(course_id, status)`).
They are also declared in the model `__table_args__` so `alembic revision
--autogenerate` reports no drift. `0008_reconcile_schema_drift` adds the
`enrollments.withdrawn_at` column (written by the enrollment service but missing
from earlier migrations) and drops the unused `course_assignments.exempted_*`
columns.

## Read-path performance

- List endpoints avoid N+1 queries. `GET /me/learning` and `GET /me/progress`
  resolve every referenced course in a single `IN (…)` query and compute
  per-course progress with two grouped counts, regardless of enrollment count.
- `GET /courses/{id}/content` loads all modules and all their lessons in two
  queries (`list_lessons_for_course`) instead of one query per module.
- Course tags use `lazy="selectin"`, so serialising a catalog page does not
  issue a query per course.


## Lesson content types

| `content_type` | `content` rule |
| --- | --- |
| `text` | Optional free text (prose). |
| `video_url` | Required, must be an absolute http(s) URL. |
| `external_link` | Required, must be an absolute http(s) URL. |

The rule is enforced by `validate_lesson_content` in `courses/schemas.py`, which both
create and update paths use. Violations return `422`.

## Lifecycle

```
draft --publish--> published        (publish needs >= 1 module AND >= 1 lesson, else 409)
draft --archive--> archived
published --archive--> archived
archived: read-only (writes 409); cannot be published (409)
published --publish--> 409 (already published)
```

Publish records `published_at` and writes an audit event in the same transaction.

## Catalog queries

- Public list (`GET /courses`) only ever returns `published` rows. Filters are
  `search` (case-insensitive match on title, short description, or description),
  `category`, `difficulty_level`, and `tag`. Results are paginated by `limit`/`offset`
  and return `total` for the same filters.
- Ordering is `created_at desc, id desc`, so pages are stable across requests.
- `GET /courses/slug/{slug}` returns a published course only. Drafts and archived
  courses are `404` (not `403`), so their existence is not revealed.
- `GET /courses/categories` returns the distinct categories of published courses.
- Route order matters: the literal `/courses/categories` and `/courses/slug/{slug}`
  routes are declared before `/courses/{course_id}`.

## Authorization

All reads require `courses:read`. Writes require `courses:write` and publish or
archive requires `courses:publish`. Authentication is still deferred (ADR-002), so no
role is granted to anonymous requests and the write paths remain protected.
