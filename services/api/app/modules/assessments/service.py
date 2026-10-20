"""Business logic for assessments.

Scoring happens entirely server-side from the stored answer key. The answer key
is never included in learner-facing data (see ``schemas.py``). Attempts and
responses are retained as history.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.assessments import repository
from app.modules.assessments.models import (
    AttemptStatus,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
    QuizResponse,
    QuizStatus,
)
from app.modules.assessments.schemas import (
    AnswerSubmission,
    Option,
    QuestionCreate,
    QuestionUpdate,
    QuizCreate,
    QuizUpdate,
)
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.courses import repository as courses_repository
from app.modules.enrollments import repository as enrollments_repository
from app.security.principal import Principal


class QuizNotFoundError(Exception):
    """No quiz exists for the given identifier."""


class QuestionNotFoundError(Exception):
    """No question exists for the given identifier."""


class QuizScopeError(Exception):
    """A quiz must be associated with a course or a lesson."""


class QuizAlreadyPublishedError(Exception):
    """The quiz is already published."""


class QuizEmptyError(Exception):
    """The quiz has no questions and cannot be published."""


class QuizNotPublishedError(Exception):
    """The quiz is not published and cannot be attempted."""


class QuizNotEditableError(Exception):
    """The quiz is archived and cannot be edited."""


class InvalidQuestionError(Exception):
    """The answer key or options are inconsistent."""


class InvalidResponseError(Exception):
    """A submitted answer references an unknown option."""


class AttemptLimitReachedError(Exception):
    """The learner has used all permitted attempts."""


class AttemptNotFoundError(Exception):
    """No attempt exists for the given identifier (or it is not owned)."""


class AttemptAlreadySubmittedError(Exception):
    """The attempt has already been submitted."""


class NotEnrolledError(Exception):
    """The learner is not enrolled in the quiz's course."""


def _now() -> datetime:
    return datetime.now(UTC)


def _option_ids(options: list[Option] | list[dict]) -> set[str]:
    return {option.id if isinstance(option, Option) else option["id"] for option in options}


def _validate_question(
    options: list[Option] | list[dict],
    answer_key: list[str],
    question_type: str,
) -> None:
    option_ids = _option_ids(options)
    if len(option_ids) != len(options):
        raise InvalidQuestionError("option ids must be unique")
    if not set(answer_key) <= option_ids:
        raise InvalidQuestionError("answer_key must reference known option ids")
    if len(set(answer_key)) != len(answer_key):
        raise InvalidQuestionError("answer_key must not contain duplicates")
    if question_type == QuestionType.SINGLE_CHOICE.value and len(answer_key) != 1:
        raise InvalidQuestionError("single-choice questions require exactly one answer")


def get_quiz(db: Session, quiz_id: uuid.UUID) -> Quiz:
    quiz = repository.get_quiz(db, quiz_id)
    if quiz is None:
        raise QuizNotFoundError(str(quiz_id))
    return quiz


def list_questions(db: Session, quiz_id: uuid.UUID) -> list[Question]:
    return repository.list_questions(db, quiz_id)


def quiz_course_id(db: Session, quiz: Quiz) -> uuid.UUID:
    if quiz.course_id is not None:
        return quiz.course_id
    lesson = courses_repository.get_lesson(db, quiz.lesson_id)
    if lesson is None:
        raise QuizScopeError("lesson not found")
    module = courses_repository.get_module(db, lesson.module_id)
    return module.course_id


def create_quiz(db: Session, *, actor: Principal, data: QuizCreate) -> Quiz:
    if data.course_id is None and data.lesson_id is None:
        raise QuizScopeError("course_id or lesson_id is required")
    if data.course_id is not None and courses_repository.get_course(db, data.course_id) is None:
        raise QuizScopeError("course not found")
    if data.lesson_id is not None and courses_repository.get_lesson(db, data.lesson_id) is None:
        raise QuizScopeError("lesson not found")
    quiz = Quiz(
        title=data.title,
        description=data.description,
        course_id=data.course_id,
        lesson_id=data.lesson_id,
        pass_score=data.pass_score,
        attempt_limit=data.attempt_limit,
        status=QuizStatus.DRAFT,
    )
    db.add(quiz)
    db.flush()
    audit_service.record_event(
        db,
        action=audit_service.ACTION_QUIZ_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="quiz",
        target_id=str(quiz.id),
        metadata={"course_id": str(data.course_id) if data.course_id else None},
    )
    db.commit()
    db.refresh(quiz)
    return quiz


def update_quiz(db: Session, *, actor: Principal, quiz_id: uuid.UUID, data: QuizUpdate) -> Quiz:
    quiz = get_quiz(db, quiz_id)
    if quiz.status == QuizStatus.ARCHIVED:
        raise QuizNotEditableError(str(quiz_id))
    for field in ("title", "description", "pass_score", "attempt_limit"):
        value = getattr(data, field)
        if value is not None:
            setattr(quiz, field, value)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_QUIZ_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="quiz",
        target_id=str(quiz.id),
    )
    db.commit()
    db.refresh(quiz)
    return quiz


def publish_quiz(db: Session, *, actor: Principal, quiz_id: uuid.UUID) -> Quiz:
    quiz = get_quiz(db, quiz_id)
    if quiz.status == QuizStatus.PUBLISHED:
        raise QuizAlreadyPublishedError(str(quiz_id))
    if not repository.list_questions(db, quiz_id):
        raise QuizEmptyError(str(quiz_id))
    quiz.status = QuizStatus.PUBLISHED
    audit_service.record_event(
        db,
        action=audit_service.ACTION_QUIZ_PUBLISHED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="quiz",
        target_id=str(quiz.id),
    )
    db.commit()
    db.refresh(quiz)
    return quiz


def add_question(
    db: Session, *, actor: Principal, quiz_id: uuid.UUID, data: QuestionCreate
) -> Question:
    quiz = get_quiz(db, quiz_id)
    if quiz.status == QuizStatus.ARCHIVED:
        raise QuizNotEditableError(str(quiz_id))
    _validate_question(data.options, data.answer_key, data.question_type.value)
    question = Question(
        quiz_id=quiz_id,
        question_type=data.question_type.value,
        prompt=data.prompt,
        options_json=[option.model_dump() for option in data.options],
        answer_key=list(data.answer_key),
        explanation=data.explanation,
        sort_order=len(repository.list_questions(db, quiz_id)),
        points=data.points,
    )
    db.add(question)
    db.flush()
    audit_service.record_event(
        db,
        action=audit_service.ACTION_QUESTION_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="question",
        target_id=str(question.id),
        metadata={"quiz_id": str(quiz_id)},
    )
    db.commit()
    db.refresh(question)
    return question


def update_question(
    db: Session, *, actor: Principal, question_id: uuid.UUID, data: QuestionUpdate
) -> Question:
    question = repository.get_question(db, question_id)
    if question is None:
        raise QuestionNotFoundError(str(question_id))
    quiz = get_quiz(db, question.quiz_id)
    if quiz.status == QuizStatus.ARCHIVED:
        raise QuizNotEditableError(str(quiz.id))

    options = data.options if data.options is not None else question.options_json
    answer_key = data.answer_key if data.answer_key is not None else question.answer_key
    _validate_question(options, answer_key, question.question_type)

    if data.prompt is not None:
        question.prompt = data.prompt
    if data.options is not None:
        question.options_json = [option.model_dump() for option in data.options]
    if data.answer_key is not None:
        question.answer_key = list(data.answer_key)
    if data.explanation is not None:
        question.explanation = data.explanation
    if data.points is not None:
        question.points = data.points
    audit_service.record_event(
        db,
        action=audit_service.ACTION_QUESTION_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="question",
        target_id=str(question.id),
        metadata={"quiz_id": str(question.quiz_id)},
    )
    db.commit()
    db.refresh(question)
    return question


def start_attempt(
    db: Session, *, user_id: uuid.UUID, quiz_id: uuid.UUID
) -> tuple[QuizAttempt, list[Question]]:
    quiz = get_quiz(db, quiz_id)
    if quiz.status != QuizStatus.PUBLISHED:
        raise QuizNotPublishedError(str(quiz_id))
    course_id = quiz_course_id(db, quiz)
    if enrollments_repository.get_latest_enrollment(db, user_id, course_id) is None:
        raise NotEnrolledError(str(course_id))

    existing = repository.get_in_progress_attempt(db, quiz_id, user_id)
    if existing is not None:
        return existing, repository.list_questions(db, quiz_id)

    if quiz.attempt_limit is not None:
        used = repository.count_attempts(db, quiz_id, user_id)
        if used >= quiz.attempt_limit:
            raise AttemptLimitReachedError(str(quiz_id))

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user_id,
        attempt_number=repository.count_attempts_max_number(db, quiz_id, user_id) + 1,
        status=AttemptStatus.IN_PROGRESS,
        started_at=_now(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt, repository.list_questions(db, quiz_id)


def _score_attempt(
    quiz: Quiz, questions: list[Question], answers: list[AnswerSubmission]
) -> tuple[list[tuple[Question, list[str], bool]], int, bool]:
    by_question = {answer.question_id: answer for answer in answers}
    results: list[tuple[Question, list[str], bool]] = []
    total_points = sum(question.points for question in questions)
    earned = 0
    for question in questions:
        submitted = by_question.get(question.id)
        selected = list(submitted.selected) if submitted is not None else []
        if not set(selected) <= _option_ids(question.options_json):
            raise InvalidResponseError(str(question.id))
        is_correct = set(selected) == set(question.answer_key) and bool(selected)
        earned += question.points if is_correct else 0
        results.append((question, selected, is_correct))
    score = round(earned / total_points * 100) if total_points else 0
    return results, score, score >= quiz.pass_score


def submit_attempt(
    db: Session, *, user_id: uuid.UUID, attempt_id: uuid.UUID, answers: list[AnswerSubmission]
) -> tuple[QuizAttempt, list[QuizResponse]]:
    attempt = repository.get_attempt(db, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise AttemptNotFoundError(str(attempt_id))
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise AttemptAlreadySubmittedError(str(attempt_id))

    quiz = repository.get_quiz(db, attempt.quiz_id)
    questions = repository.list_questions(db, attempt.quiz_id)
    results, score, passed = _score_attempt(quiz, questions, answers)

    responses: list[QuizResponse] = []
    for question, selected, is_correct in results:
        response = QuizResponse(
            attempt_id=attempt.id,
            question_id=question.id,
            response_json=selected,
            is_correct=is_correct,
            points_awarded=question.points if is_correct else 0,
        )
        db.add(response)
        responses.append(response)

    attempt.status = AttemptStatus.SUBMITTED
    attempt.score = score
    attempt.passed = passed
    attempt.submitted_at = _now()
    db.commit()
    db.refresh(attempt)
    return attempt, repository.list_responses(db, attempt.id)


def list_attempts(db: Session, *, quiz_id: uuid.UUID, user_id: uuid.UUID) -> list[QuizAttempt]:
    get_quiz(db, quiz_id)
    return repository.list_attempts(db, quiz_id, user_id)


def attempt_responses(db: Session, attempt: QuizAttempt) -> list[QuizResponse]:
    return repository.list_responses(db, attempt.id)


__all__ = [
    "AttemptAlreadySubmittedError",
    "AttemptLimitReachedError",
    "AttemptNotFoundError",
    "InvalidQuestionError",
    "InvalidResponseError",
    "NotEnrolledError",
    "QuestionNotFoundError",
    "QuizAlreadyPublishedError",
    "QuizEmptyError",
    "QuizNotEditableError",
    "QuizNotFoundError",
    "QuizNotPublishedError",
    "QuizScopeError",
    "add_question",
    "attempt_responses",
    "create_quiz",
    "get_quiz",
    "list_questions",
    "publish_quiz",
    "quiz_course_id",
    "submit_attempt",
    "update_question",
    "update_quiz",
]
