# ADR-009: Deterministic Compliance Learning and Exemption Policy

## Context

Corporate training often requires mandatory compliance courses (e.g., Information Security Awareness, Anti-Bribery, Workplace Safety) with strict regulatory and auditable completion requirements.

Key requirements:
1. Deterministic rules: All compliance statuses, due dates, completion determinations, and recertification cycles must be deterministic and auditable. AI systems must NEVER make compliance pass/fail, completion, or exemption decisions.
2. Distinct lifecycle states: Learning records must distinctly reflect `assigned`, `in_progress`, `completed`, `overdue`, and `exempt`.
3. Auditable exemptions: Any exemption must be recorded with an authorized actor, mandatory reason, and timestamp in the immutable audit log (`audit_events`).
4. Recertification: Mandatory courses may specify a validity period (e.g. 365 days). Once the validity period expires, recertification is required.

## Decision

1. **Course Model**:
   - `is_mandatory`: boolean flag indicating whether the course is a required compliance course.
   - `validity_days`: optional integer specifying the number of days after completion before recertification is required (e.g. 365 days for annual certifications).

2. **Assignment & Exemption Workflow**:
   - `AssignmentStatus` includes `active`, `cancelled`, and `exempt`.
   - Authorized learning administrators can exempt a learner from an assignment by submitting `POST /api/v1/assignments/{id}/exempt` with a mandatory human reason (minimum 5 characters).
   - Exemptions are atomic: the assignment status is updated, exemption details (`exempted_at`, `exempt_reason`, `exempted_by`) are recorded, any associated active enrollment is marked `exempt`, and an audit event `compliance.exempted` is emitted in the same database transaction.

3. **Status Distinctions**:
   - `assigned`: active assignment, not yet begun.
   - `in_progress`: learner has started lessons or quizzes.
   - `completed`: learner completed all required lessons and passed required assessments.
   - `overdue`: current time > due date and course not completed or exempt.
   - `exempt`: learner was formally excused from training with an audited justification.

4. **AI Boundaries**:
   - Under no circumstances shall an AI model or automated heuristic assign an exemption, override a grade, or complete a compliance requirement.

## Consequences

- Compliance reports can accurately separate genuinely completed employees from excused/exempt employees.
- Complete regulatory audit trail for all exemptions and overrides.
- Deterministic behavior with no ambiguity or external dependencies.
