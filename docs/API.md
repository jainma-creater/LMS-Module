# API contract (core LMS)

Base path: `/api/v1`. Interactive docs are served at `/api/docs` when the API
is running. All endpoints below require an authenticated principal with the
listed permission. Authentication is deny-by-default (`AUTH_PROVIDER=disabled`),
so every protected endpoint returns `401` until an approved identity provider is
configured. For local development only, `AUTH_PROVIDER=development` grants a fixed local
user with `DEV_ACCESS_ROLES` (default `learning_admin`) and refuses to start unless
`APP_ENV=development`. See [`SECURITY.md`](SECURITY.md) and
[`adr/ADR-002-identity-provider.md`](adr/ADR-002-identity-provider.md).

## Conventions

- Learner identity (progress, enrollments, attempts) always comes from the
  authenticated principal, never from the request body.
- Draft or unpublished content is hidden from callers without authoring rights
  (`404`, not `403`).
- Answer keys and explanations are never returned to callers without
  `assessments:write`, and never before an attempt is submitted.
- Scoring, pass/fail, completion, and overdue are computed server-side.
- Every response carries `X-Request-ID` and `X-Process-Time-Ms`. Permission-gated
  read endpoints set `Cache-Control: private, max-age=…` so the caller's browser
  may reuse them briefly, but no shared proxy may store them.

## Courses

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/courses` | `courses:read` | Published catalog page `{items, total, limit, offset}`; optional `search`, `category`, `difficulty_level`, `tag`; `limit` 1–100 (default 20), `offset` ≥ 0; order `created_at desc, id desc` |
| GET | `/courses/categories` | `courses:read` | Distinct categories of published courses |
| GET | `/courses/slug/{slug}` | `courses:read` | Published course detail by slug; drafts/archived are `404` |
| GET | `/courses/{id}` | `courses:read` | Detail with module/lesson counts; drafts hidden |
| GET | `/courses/{id}/content` | `courses:read` | Module and lesson tree; drafts hidden |
| GET | `/admin/courses` | `courses:write` | All courses; optional `status`, `category`, `difficulty_level` |
| POST | `/courses` | `courses:write` | Create a draft course |
| PATCH | `/courses/{id}` | `courses:write` | Update fields. An explicit `null` clears an optional field; omitted fields are unchanged; a `tags` list replaces the set. Archived courses are read-only (`409`) |
| POST | `/courses/{id}/publish` | `courses:publish` | Publish from draft only; already published, archived, or missing a module or lesson is `409` |
| POST | `/courses/{id}/archive` | `courses:publish` | Archive |
| POST | `/courses/{id}/modules` | `courses:write` | Add a module |
| PUT | `/courses/{id}/modules/order` | `courses:write` | Reorder; exact id set required (`400` otherwise) |
| PATCH | `/modules/{id}` | `courses:write` | Update a module |
| DELETE | `/modules/{id}` | `courses:write` | Delete a module (cascades lessons) |
| POST | `/modules/{id}/lessons` | `courses:write` | Add a lesson |
| PUT | `/modules/{id}/lessons/order` | `courses:write` | Reorder lessons |
| PATCH | `/lessons/{id}` | `courses:write` | Update a lesson. `content_type` values are `text`, `video_url`, `external_link`; link types require an http(s) URL. Archived courses are read-only (`409`) |
| DELETE | `/lessons/{id}` | `courses:write` | Delete a lesson |

## Enrollments

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| POST | `/courses/{id}/enrollments` | `enrollments:assign` | Assign a learner; duplicate active enrollment is `409` |
| GET | `/courses/{id}/enrollments` | `enrollments:assign` | List enrollments for a course |
| GET | `/me/learning` | `learning:read` | Caller's assignments with per-course progress |
| GET | `/enrollments/{id}` | `learning:read` | Caller's own enrollment (`404` for others) |
| PATCH | `/enrollments/{id}` | `enrollments:assign` | Update the due date |

## Progress

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| PUT | `/lessons/{id}/progress` | `progress:write` | Record lesson status/position; requires enrollment (`409`) |
| GET | `/courses/{id}/progress` | `learning:read` | Per-lesson and aggregate progress |
| GET | `/me/progress` | `learning:read` | Completion history |

## Assessments

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| POST | `/quizzes` | `assessments:write` | Create a quiz (scoped to a course or lesson) |
| GET | `/quizzes/{id}` | `assessments:attempt` | Author detail includes answer keys; learners get a key-free view |
| PATCH | `/quizzes/{id}` | `assessments:write` | Update a quiz |
| POST | `/quizzes/{id}/publish` | `assessments:write` | Publish; empty quizzes are `409` |
| POST | `/quizzes/{id}/questions` | `assessments:write` | Add a question |
| PATCH | `/questions/{id}` | `assessments:write` | Update a question |
| POST | `/quizzes/{id}/attempts` | `assessments:attempt` | Start an attempt; requires enrollment; attempt limit enforced (`409`) |
| POST | `/attempts/{id}/submit` | `assessments:attempt` | Submit answers; scoring returned; resubmission is `409` |
| GET | `/quizzes/{id}/results` | `assessments:attempt` | Caller's attempts for a quiz |

## Web routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page with system status and featured courses |
| `/courses` | Learner catalog (search + filters); `/courses/{slug}` is course detail |
| `/learn/{courseId}` | Learning player for an enrolled course |
| `/learning` | Assigned courses with due dates and progress |
| `/progress` | In-progress and completed courses |
| `/manage` | Admin dashboard; `/manage/{courseId}` authors a course |
| `/manage/studio` | AI Training Studio (generate → review → publish) |
| `/manage/learners`, `/manage/groups`, `/manage/assignments`, `/manage/group-assignments` | Learner, group, and assignment administration |
| `/quizzes/{quizId}` | Author a quiz, or attempt it as a learner |

## Health and observability

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/healthz` | Liveness only (no dependencies); also aliased without the `/api/v1` prefix |
| GET | `/readyz` | Readiness: checks the database and reports `checks.schema_revision` (current Alembic revision) when available |

Every request logs `request.started`/`request.finished` with `request_id`,
`actor_id`, `status`, and `duration_ms`.
