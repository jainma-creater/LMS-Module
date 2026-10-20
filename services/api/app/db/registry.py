"""Import all ORM models so ``Base.metadata`` is fully populated.

Import this module (never the individual model modules) wherever the complete
metadata is required: the test suite's ``create_all`` and Alembic's
``target_metadata``.
"""

from app.modules.assessments.models import (  # noqa: F401
    Question,
    Quiz,
    QuizAttempt,
    QuizResponse,
)
from app.modules.assignments.models import (  # noqa: F401
    CourseAssignment,
    GroupCourseAssignment,
)
from app.modules.audit.models import AuditEvent  # noqa: F401
from app.modules.courses.models import Course, CourseTag, Lesson, Module  # noqa: F401
from app.modules.enrollments.models import Enrollment  # noqa: F401
from app.modules.learners.models import (  # noqa: F401
    Learner,
    LearningGroup,
    LearningGroupMember,
)
from app.modules.progress.models import CourseCompletion, LessonProgress  # noqa: F401
from app.modules.training_studio.models import TrainingGenerationJob  # noqa: F401
from app.modules.users.models import Role, User, UserRole  # noqa: F401
