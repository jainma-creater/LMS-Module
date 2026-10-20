"""Service orchestration for AI Training Studio."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.modules.assessments.models import Question, QuestionType, Quiz, QuizStatus
from app.modules.assignments import service as assignments_service
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.courses import service as courses_service
from app.modules.courses.schemas import CourseCreate, LessonCreate, ModuleCreate
from app.modules.training_studio import generator, parser, renderer_client
from app.modules.training_studio.models import JobStage, JobStatus, TrainingGenerationJob
from app.modules.training_studio.schemas import (
    CourseDraft,
    DraftUpdateRequest,
    GenerationRequest,
    PublishDraftRequest,
    PublishDraftResponse,
    QuizDraft,
    QuizQuestionDraft,
)
from app.modules.training_studio.video_pipeline import get_video_pipeline
from app.security.principal import Principal


class JobNotFoundError(Exception):
    """Raised when a generation job does not exist."""


class InvalidJobStateError(Exception):
    """Raised when attempting an operation on a job not in the required state."""


def get_job_or_raise(db: Session, job_id: uuid.UUID) -> TrainingGenerationJob:
    job = db.get(TrainingGenerationJob, job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")
    return job


def create_generation_job(
    db: Session,
    *,
    actor: Principal,
    request: GenerationRequest,
    file_bytes: bytes | None = None,
    filename: str | None = None,
) -> TrainingGenerationJob:
    """Create and execute an end-to-end training generation pipeline."""
    initial_title = request.topic or (filename or "New Training Course")

    job = TrainingGenerationJob(
        title=initial_title[:255],
        topic=request.topic,
        source_file_name=filename,
        language=request.language,
        target_duration_minutes=request.target_duration_minutes,
        audience=request.audience,
        include_quiz=request.include_quiz,
        include_video=request.include_video,
        status=JobStatus.PROCESSING,
        progress_percent=10,
        stage=JobStage.PARSING,
        created_by=actor.user_id,
    )
    db.add(job)
    # Commit before generation so a failure can be recorded even after rollback.
    db.commit()
    job_id = job.id

    try:
        # Step 1: Document Parsing
        extracted_text = request.source_text or ""
        if file_bytes and filename:
            parsed = parser.extract_text_from_bytes(file_bytes, filename)
            extracted_text = (extracted_text + "\n\n" + parsed).strip()

        job.progress_percent = 30
        job.stage = JobStage.DRAFTING_CONTENT
        db.flush()

        # Step 2: Course Content Generation
        course_draft = generator.generate_course_from_source(
            topic=request.topic,
            source_text=extracted_text,
            language=request.language,
            target_duration_minutes=request.target_duration_minutes,
            audience=request.audience,
        )

        job.progress_percent = 55
        job.stage = JobStage.DRAFTING_QUIZ
        db.flush()

        # Step 3: Quiz Generation
        quiz_draft: QuizDraft | None = None
        if request.include_quiz:
            quiz_draft = generator.generate_quiz_for_course(
                course_draft, target_minutes=request.target_duration_minutes
            )

        job.progress_percent = 75
        job.stage = JobStage.RENDERING_VIDEO
        db.flush()

        # Step 4: Video Narration & Storyboard
        video_url: str | None = None
        duration_sec: int | None = None
        if request.include_video:
            pipeline = get_video_pipeline()
            storyboard = pipeline.build_storyboard(
                title=course_draft.title,
                objectives=course_draft.learning_objectives,
                modules_outline=[
                    {"title": m.title, "description": m.description} for m in course_draft.modules
                ],
                language=request.language,
                target_minutes=request.target_duration_minutes,
            )
            vtt_captions = pipeline.generate_vtt_captions(storyboard)
            course_draft.storyboard = storyboard
            course_draft.captions_vtt = vtt_captions

            video_url, duration_sec = renderer_client.render_course_video(
                job_id=str(job.id),
                course=course_draft,
                storyboard=storyboard,
                storage_dir=Path("storage/videos"),
            )

        job.title = course_draft.title
        job.generated_course_data = course_draft.model_dump()
        job.generated_quiz_data = quiz_draft.model_dump() if quiz_draft else None
        job.generated_video_asset_url = video_url
        job.generated_video_duration_seconds = duration_sec
        job.progress_percent = 100
        job.stage = JobStage.COMPLETE
        job.status = JobStatus.GENERATED

        db.commit()
        db.refresh(job)
        return job

    except Exception as exc:
        db.rollback()
        # The job row was committed above, so it survives the rollback.
        failed_job = db.get(TrainingGenerationJob, job_id)
        if failed_job is None:
            raise
        failed_job.status = JobStatus.FAILED
        failed_job.stage = JobStage.FAILED
        failed_job.error_message = str(exc)[:2000]
        db.commit()
        db.refresh(failed_job)
        return failed_job


def update_draft(
    db: Session,
    *,
    job_id: uuid.UUID,
    actor: Principal,
    data: DraftUpdateRequest,
) -> TrainingGenerationJob:
    """Update editable fields of a generated training draft before publishing."""
    job = get_job_or_raise(db, job_id)
    if job.status not in (JobStatus.GENERATED, JobStatus.PROCESSING):
        raise InvalidJobStateError("Only generated drafts can be edited.")

    if data.course:
        job.generated_course_data = data.course.model_dump()
        job.title = data.course.title
    if data.quiz:
        job.generated_quiz_data = data.quiz.model_dump()

    db.commit()
    db.refresh(job)
    return job


def regenerate_question(
    db: Session,
    *,
    job_id: uuid.UUID,
    actor: Principal,
    question_index: int,
    hint: str | None = None,
) -> QuizQuestionDraft:
    """Regenerate a single objective question in the draft quiz without touching other content."""
    job = get_job_or_raise(db, job_id)
    if not job.generated_quiz_data or "questions" not in job.generated_quiz_data:
        raise InvalidJobStateError("Draft does not have a quiz to regenerate questions in.")

    questions = job.generated_quiz_data["questions"]
    if question_index < 0 or question_index >= len(questions):
        raise InvalidJobStateError(
            f"Question index {question_index} out of range (0-{len(questions) - 1})."
        )

    course_draft = CourseDraft.model_validate(job.generated_course_data)
    avoid = [q.get("prompt", "") for i, q in enumerate(questions) if i != question_index]
    new_q = generator.regenerate_single_question(
        course_draft, question_index, hint, avoid_prompts=avoid
    )

    quiz_data = dict(job.generated_quiz_data)
    questions = list(quiz_data.get("questions", []))
    questions[question_index] = new_q.model_dump()
    quiz_data["questions"] = questions
    job.generated_quiz_data = quiz_data
    flag_modified(job, "generated_quiz_data")
    db.commit()
    db.refresh(job)
    return new_q


def publish_draft(
    db: Session,
    *,
    job_id: uuid.UUID,
    actor: Principal,
    publish_req: PublishDraftRequest,
) -> PublishDraftResponse:
    """Atomically approve and publish course, modules, quiz, and optional assignment."""
    job = get_job_or_raise(db, job_id)
    if job.status != JobStatus.GENERATED:
        raise InvalidJobStateError("Only drafts in 'generated' state can be published.")
    if not job.generated_course_data:
        raise InvalidJobStateError("Missing generated course data.")

    course_data = CourseDraft.model_validate(job.generated_course_data)

    # 1. Create Course
    course_create = CourseCreate(
        title=course_data.title,
        short_description=course_data.short_description,
        description=course_data.description,
        category=course_data.category,
        difficulty_level=course_data.difficulty_level,
        estimated_minutes=sum(
            lesson.estimated_minutes for mod in course_data.modules for lesson in mod.lessons
        ),
        thumbnail_url=None,
        tags=course_data.tags,
        is_mandatory=course_data.is_mandatory,
        validity_days=course_data.validity_days,
    )
    course = courses_service.create_course(db, actor=actor, data=course_create)

    # 2. Create Modules and Lessons
    for mod_idx, mod_draft in enumerate(course_data.modules):
        mod = courses_service.create_module(
            db, actor=actor, course_id=course.id, data=ModuleCreate(title=mod_draft.title)
        )
        for lesson_idx, lesson_draft in enumerate(mod_draft.lessons):
            # The course video attaches to the very first lesson only (by position, not equality).
            content_type = lesson_draft.content_type
            content = lesson_draft.content
            is_video_lesson = mod_idx == 0 and lesson_idx == 0
            if job.generated_video_asset_url and is_video_lesson:
                # Absolute URL on the public web origin, served by the Next.js video proxy.
                content_type = "video_url"
                content = (
                    f"{get_settings().public_web_url.rstrip('/')}"
                    f"/api/studio/video-asset/{Path(job.generated_video_asset_url).name}"
                )

            courses_service.create_lesson(
                db,
                actor=actor,
                module_id=mod.id,
                data=LessonCreate(
                    title=lesson_draft.title,
                    description=lesson_draft.description,
                    content_type=content_type,
                    content=content,
                    estimated_minutes=lesson_draft.estimated_minutes,
                    is_required=lesson_draft.is_required,
                ),
            )

    # 3. Publish the course
    course = courses_service.publish_course(db, actor=actor, course_id=course.id)

    # 4. Create and Publish Quiz if quiz data was generated
    published_quiz_id: uuid.UUID | None = None
    if job.generated_quiz_data:
        quiz_data = QuizDraft.model_validate(job.generated_quiz_data)
        quiz = Quiz(
            title=f"{course.title} - Assessment",
            course_id=course.id,
            pass_score=quiz_data.pass_score,
            attempt_limit=quiz_data.attempt_limit,
            status=QuizStatus.DRAFT,
        )
        db.add(quiz)
        db.flush()

        for idx, q_draft in enumerate(quiz_data.questions):
            q_type = QuestionType.SINGLE_CHOICE
            if q_draft.question_type == "multiple_choice":
                q_type = QuestionType.MULTIPLE_CHOICE
            elif q_draft.question_type == "true_false":
                q_type = QuestionType.TRUE_FALSE

            question = Question(
                quiz_id=quiz.id,
                question_type=q_type,
                prompt=q_draft.prompt,
                options_json=[opt.model_dump() for opt in q_draft.options],
                answer_key=q_draft.answer_key,
                explanation=q_draft.explanation,
                sort_order=idx + 1,
            )
            db.add(question)
        db.flush()

        # Publish quiz
        quiz.status = QuizStatus.PUBLISHED
        db.flush()
        published_quiz_id = quiz.id

    # 5. Optional Immediate Assignment
    assignment_id: uuid.UUID | None = None
    group_assignment_id: uuid.UUID | None = None
    due_at = (
        datetime.now(UTC) + timedelta(days=publish_req.due_days) if publish_req.due_days else None
    )

    if publish_req.assign_to_group_id:
        group_assign_result = assignments_service.create_group_assignment(
            db,
            actor=actor,
            course_id=course.id,
            group_id=publish_req.assign_to_group_id,
            due_at=due_at,
        )
        group_assignment_id = group_assign_result.group_assignment.id

    if publish_req.assign_to_learner_id:
        learner_assign = assignments_service.create_individual_assignment(
            db,
            actor=actor,
            course_id=course.id,
            learner_id=publish_req.assign_to_learner_id,
            due_at=due_at,
        )
        assignment_id = learner_assign.id

    # 6. Update Job State
    job.status = JobStatus.PUBLISHED
    job.published_course_id = course.id
    job.published_quiz_id = published_quiz_id

    # 7. Record Audit Event
    audit_service.record_event(
        db,
        action="training_studio.published",
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="course",
        target_id=str(course.id),
        metadata={
            "job_id": str(job.id),
            "course_title": course.title,
            "quiz_id": str(published_quiz_id) if published_quiz_id else None,
            "assigned_group": str(group_assignment_id) if group_assignment_id else None,
            "assigned_learner": str(assignment_id) if assignment_id else None,
        },
    )

    db.commit()
    db.refresh(job)

    return PublishDraftResponse(
        course_id=course.id,
        course_slug=course.slug,
        quiz_id=published_quiz_id,
        assignment_id=assignment_id,
        group_assignment_id=group_assignment_id,
        message=(
            f"Course '{course.title}' published successfully "
            "with verified modules, lessons, and assessment."
        ),
    )
