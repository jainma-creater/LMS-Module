"""Database queries for assessments."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.assessments.models import (
    AttemptStatus,
    Question,
    Quiz,
    QuizAttempt,
    QuizResponse,
)


def get_quiz(db: Session, quiz_id: uuid.UUID) -> Quiz | None:
    return db.get(Quiz, quiz_id)


def list_quizzes_for_course(db: Session, course_id: uuid.UUID) -> list[Quiz]:
    stmt = select(Quiz).where(Quiz.course_id == course_id).order_by(Quiz.created_at)
    return list(db.execute(stmt).scalars())


def list_questions(db: Session, quiz_id: uuid.UUID) -> list[Question]:
    stmt = (
        select(Question)
        .where(Question.quiz_id == quiz_id)
        .order_by(Question.sort_order, Question.id)
    )
    return list(db.execute(stmt).scalars())


def get_question(db: Session, question_id: uuid.UUID) -> Question | None:
    return db.get(Question, question_id)


def next_question_order(db: Session, quiz_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Question).where(Question.quiz_id == quiz_id)
    return int(db.execute(stmt).scalar_one())


def get_attempt(db: Session, attempt_id: uuid.UUID) -> QuizAttempt | None:
    return db.get(QuizAttempt, attempt_id)


def count_attempts(db: Session, quiz_id: uuid.UUID, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
    )
    return int(db.execute(stmt).scalar_one())


def count_submitted_attempts(db: Session, quiz_id: uuid.UUID, user_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(QuizAttempt)
        .where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == AttemptStatus.SUBMITTED,
        )
    )
    return int(db.execute(stmt).scalar_one())


def get_in_progress_attempt(
    db: Session, quiz_id: uuid.UUID, user_id: uuid.UUID
) -> QuizAttempt | None:
    stmt = select(QuizAttempt).where(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.user_id == user_id,
        QuizAttempt.status == AttemptStatus.IN_PROGRESS,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_attempts(db: Session, quiz_id: uuid.UUID, user_id: uuid.UUID) -> list[QuizAttempt]:
    stmt = (
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.attempt_number)
    )
    return list(db.execute(stmt).scalars())


def get_response(db: Session, attempt_id: uuid.UUID, question_id: uuid.UUID) -> QuizResponse | None:
    stmt = select(QuizResponse).where(
        QuizResponse.attempt_id == attempt_id, QuizResponse.question_id == question_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_responses(db: Session, attempt_id: uuid.UUID) -> list[QuizResponse]:
    stmt = select(QuizResponse).where(QuizResponse.attempt_id == attempt_id)
    return list(db.execute(stmt).scalars())


def count_attempts_max_number(db: Session, quiz_id: uuid.UUID, user_id: uuid.UUID) -> int:
    stmt = select(func.max(QuizAttempt.attempt_number)).where(
        QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id
    )
    return int(db.execute(stmt).scalar_one_or_none() or 0)
