"""HTTP endpoints for assessments.

Authoring requires ``assessments:write``. Attempting requires
``assessments:attempt`` and an enrollment in the quiz's course. Answer keys are
only ever returned to callers with authoring rights.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.assessments import service
from app.modules.assessments.models import Question, QuizStatus
from app.modules.assessments.schemas import (
    AttemptResult,
    AttemptStartResponse,
    AttemptSubmitRequest,
    AttemptSummary,
    Option,
    QuestionAuthorResponse,
    QuestionCreate,
    QuestionLearnerResponse,
    QuestionUpdate,
    QuizAuthorDetail,
    QuizCreate,
    QuizLearnerDetail,
    QuizResponse,
    QuizUpdate,
    ResponseResult,
)
from app.modules.enrollments import repository as enrollments_repository
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["assessments"])

_DOMAIN_ERRORS = (
    service.QuizNotFoundError,
    service.QuestionNotFoundError,
    service.QuizScopeError,
    service.QuizAlreadyPublishedError,
    service.QuizEmptyError,
    service.QuizNotPublishedError,
    service.QuizNotEditableError,
    service.InvalidQuestionError,
    service.InvalidResponseError,
    service.AttemptLimitReachedError,
    service.AttemptNotFoundError,
    service.AttemptAlreadySubmittedError,
    service.NotEnrolledError,
)


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, (service.QuizNotFoundError, service.QuestionNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    if isinstance(exc, (service.AttemptNotFoundError, service.QuizNotPublishedError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    if isinstance(exc, service.QuizScopeError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz scope is invalid."
        )
    if isinstance(exc, (service.InvalidQuestionError, service.InvalidResponseError)):
        return HTTPException(status_code=422, detail="Invalid assessment data.")
    if isinstance(exc, service.QuizAlreadyPublishedError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Quiz is already published."
        )
    if isinstance(exc, service.QuizEmptyError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Quiz has no questions to publish."
        )
    if isinstance(exc, service.QuizNotEditableError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Archived quizzes cannot be edited."
        )
    if isinstance(exc, service.AttemptLimitReachedError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt limit reached.")
    if isinstance(exc, service.AttemptAlreadySubmittedError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt already submitted."
        )
    if isinstance(exc, service.NotEnrolledError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Not enrolled in this course."
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected.")


def _options(question: Question) -> list[Option]:
    return [Option(**option) for option in question.options_json]


def _author_question(question: Question) -> QuestionAuthorResponse:
    return QuestionAuthorResponse(
        id=question.id,
        quiz_id=question.quiz_id,
        question_type=question.question_type,
        prompt=question.prompt,
        options=_options(question),
        answer_key=list(question.answer_key),
        explanation=question.explanation,
        sort_order=question.sort_order,
        points=question.points,
    )


def _learner_question(question: Question) -> QuestionLearnerResponse:
    return QuestionLearnerResponse(
        id=question.id,
        question_type=question.question_type,
        prompt=question.prompt,
        options=_options(question),
        sort_order=question.sort_order,
        points=question.points,
    )


def _attempt_result(db: Session, attempt) -> AttemptResult:
    questions = {q.id: q for q in service.list_questions(db, attempt.quiz_id)}
    responses = service.attempt_responses(db, attempt)
    results = [
        ResponseResult(
            question_id=response.question_id,
            selected=list(response.response_json),
            is_correct=bool(response.is_correct),
            points_awarded=response.points_awarded,
            explanation=questions[response.question_id].explanation
            if response.question_id in questions
            else None,
        )
        for response in responses
    ]
    return AttemptResult(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        score=attempt.score,
        passed=attempt.passed,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        results=results,
    )


# --------------------------------------------------------------------------- #
# Authoring (assessments:write)
# --------------------------------------------------------------------------- #
@router.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
def create_quiz(
    payload: QuizCreate,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_WRITE)),
    db: Session = Depends(get_db),
) -> QuizResponse:
    try:
        quiz = service.create_quiz(db, actor=principal, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return QuizResponse.model_validate(quiz)


@router.patch("/quizzes/{quiz_id}", response_model=QuizResponse)
def update_quiz(
    quiz_id: uuid.UUID,
    payload: QuizUpdate,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_WRITE)),
    db: Session = Depends(get_db),
) -> QuizResponse:
    try:
        quiz = service.update_quiz(db, actor=principal, quiz_id=quiz_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return QuizResponse.model_validate(quiz)


@router.post("/quizzes/{quiz_id}/publish", response_model=QuizResponse)
def publish_quiz(
    quiz_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_WRITE)),
    db: Session = Depends(get_db),
) -> QuizResponse:
    try:
        quiz = service.publish_quiz(db, actor=principal, quiz_id=quiz_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return QuizResponse.model_validate(quiz)


@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuestionAuthorResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_question(
    quiz_id: uuid.UUID,
    payload: QuestionCreate,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_WRITE)),
    db: Session = Depends(get_db),
) -> QuestionAuthorResponse:
    try:
        question = service.add_question(db, actor=principal, quiz_id=quiz_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _author_question(question)


@router.patch("/questions/{question_id}", response_model=QuestionAuthorResponse)
def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_WRITE)),
    db: Session = Depends(get_db),
) -> QuestionAuthorResponse:
    try:
        question = service.update_question(
            db, actor=principal, question_id=question_id, data=payload
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _author_question(question)


# --------------------------------------------------------------------------- #
# Reading a quiz (author sees keys; learner does not)
# --------------------------------------------------------------------------- #
@router.get("/quizzes/{quiz_id}", response_model=QuizAuthorDetail | QuizLearnerDetail)
def get_quiz(
    quiz_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_ATTEMPT)),
    db: Session = Depends(get_db),
) -> QuizAuthorDetail | QuizLearnerDetail:
    try:
        quiz = service.get_quiz(db, quiz_id)
        questions = service.list_questions(db, quiz_id)
        is_author = principal.has_permission(Permission.ASSESSMENTS_WRITE.value)
        if not is_author:
            if quiz.status != QuizStatus.PUBLISHED:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
                )
            course_id = service.quiz_course_id(db, quiz)
            enrolled = enrollments_repository.get_latest_enrollment(
                db, principal.user_id, course_id
            )
            if enrolled is None:
                raise service.NotEnrolledError(str(course_id))
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    if is_author:
        return QuizAuthorDetail(
            **QuizResponse.model_validate(quiz).model_dump(),
            questions=[_author_question(question) for question in questions],
        )
    return QuizLearnerDetail(
        **QuizResponse.model_validate(quiz).model_dump(),
        questions=[_learner_question(question) for question in questions],
    )


# --------------------------------------------------------------------------- #
# Attempting (assessments:attempt)
# --------------------------------------------------------------------------- #
@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_attempt(
    quiz_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_ATTEMPT)),
    db: Session = Depends(get_db),
) -> AttemptStartResponse:
    try:
        attempt, questions = service.start_attempt(db, user_id=principal.user_id, quiz_id=quiz_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return AttemptStartResponse(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        started_at=attempt.started_at,
        questions=[_learner_question(question) for question in questions],
    )


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult)
def submit_attempt(
    attempt_id: uuid.UUID,
    payload: AttemptSubmitRequest,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_ATTEMPT)),
    db: Session = Depends(get_db),
) -> AttemptResult:
    try:
        attempt, _ = service.submit_attempt(
            db,
            user_id=principal.user_id,
            attempt_id=attempt_id,
            answers=payload.answers,
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _attempt_result(db, attempt)


@router.get("/quizzes/{quiz_id}/results", response_model=list[AttemptSummary])
def list_results(
    quiz_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ASSESSMENTS_ATTEMPT)),
    db: Session = Depends(get_db),
) -> list[AttemptSummary]:
    try:
        attempts = service.list_attempts(db, quiz_id=quiz_id, user_id=principal.user_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return [AttemptSummary.model_validate(attempt) for attempt in attempts]
