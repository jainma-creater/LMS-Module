"""Permission registry and role-to-permission mapping.

Permissions are defined in code, not stored in the database, so that adding a
new capability is an explicit, reviewable change. Role assignments are stored
in the database (``roles`` / ``user_roles`` tables).

Design rule: there is no wildcard administrator bypass. ``system_admin`` holds
an explicit, enumerated set of permissions; granting a new permission requires
deliberately adding it here.
"""

from enum import StrEnum


class Role(StrEnum):
    LEARNER = "learner"
    TRAINER = "trainer"
    MANAGER = "manager"
    LEARNING_ADMIN = "learning_admin"
    SYSTEM_ADMIN = "system_admin"
    AUDITOR = "auditor"


class Permission(StrEnum):
    # Identity / self-service
    PROFILE_READ = "profile:read"
    # Security administration
    ROLES_ASSIGN = "roles:assign"
    # Audit and compliance
    AUDIT_READ = "audit:read"
    # Course catalog
    COURSES_READ = "courses:read"
    COURSES_WRITE = "courses:write"
    COURSES_PUBLISH = "courses:publish"
    # Enrollment / assignment
    ENROLLMENTS_ASSIGN = "enrollments:assign"
    # Learner records, learning groups, and group membership
    LEARNERS_READ = "learners:read"
    LEARNERS_WRITE = "learners:write"
    # Learner activity (own records)
    LEARNING_READ = "learning:read"
    PROGRESS_WRITE = "progress:write"
    # Assessments
    ASSESSMENTS_WRITE = "assessments:write"
    ASSESSMENTS_ATTEMPT = "assessments:attempt"


ALL_ROLES: tuple[Role, ...] = tuple(Role)

ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.LEARNER: "Consumes assigned courses and tracks own progress.",
    Role.TRAINER: "Authors and publishes assigned course content.",
    Role.MANAGER: "Views permitted team learning status.",
    Role.LEARNING_ADMIN: "Manages catalog, enrollments, and assignments.",
    Role.SYSTEM_ADMIN: "Configures roles, integrations, and security settings.",
    Role.AUDITOR: "Read-only access to authorized audit and completion evidence.",
}

# Permissions every active employee/learner holds: browse the catalog and manage
# their own learning records. Auditors are deliberately read-only and excluded.
_LEARNER_BASELINE: frozenset[Permission] = frozenset(
    {
        Permission.COURSES_READ,
        Permission.LEARNING_READ,
        Permission.PROGRESS_WRITE,
        Permission.ASSESSMENTS_ATTEMPT,
    }
)

# Explicit, least-privilege mapping. Do not use wildcards.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.LEARNER: frozenset({Permission.PROFILE_READ}) | _LEARNER_BASELINE,
    Role.TRAINER: frozenset(
        {Permission.PROFILE_READ, Permission.COURSES_WRITE, Permission.ASSESSMENTS_WRITE}
    )
    | _LEARNER_BASELINE,
    Role.MANAGER: frozenset({Permission.PROFILE_READ}) | _LEARNER_BASELINE,
    Role.LEARNING_ADMIN: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.COURSES_WRITE,
            Permission.COURSES_PUBLISH,
            Permission.ENROLLMENTS_ASSIGN,
            Permission.LEARNERS_READ,
            Permission.LEARNERS_WRITE,
            Permission.ASSESSMENTS_WRITE,
        }
    )
    | _LEARNER_BASELINE,
    Role.SYSTEM_ADMIN: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.ROLES_ASSIGN,
            Permission.AUDIT_READ,
            Permission.COURSES_WRITE,
            Permission.COURSES_PUBLISH,
            Permission.ENROLLMENTS_ASSIGN,
            Permission.LEARNERS_READ,
            Permission.LEARNERS_WRITE,
            Permission.ASSESSMENTS_WRITE,
        }
    )
    | _LEARNER_BASELINE,
    Role.AUDITOR: frozenset(
        {Permission.PROFILE_READ, Permission.AUDIT_READ, Permission.COURSES_READ}
    ),
}


def permissions_for_roles(roles: frozenset[str] | set[str]) -> frozenset[Permission]:
    """Union of permissions granted by the given role names.

    Unknown role names contribute no permissions (deny by default).
    """
    granted: set[Permission] = set()
    for name in roles:
        try:
            role = Role(name)
        except ValueError:
            continue
        granted |= ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(granted)
