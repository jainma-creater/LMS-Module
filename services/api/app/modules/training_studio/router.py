"""HTTP endpoints for AI Training Studio.

Provides guided 3-to-5 click training generation, review/editing,
question regeneration, video asset streaming, and atomic publishing/assignment.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.training_studio import service
from app.modules.training_studio.schemas import (
    DraftUpdateRequest,
    GenerationJobResponse,
    GenerationRequest,
    PublishDraftRequest,
    PublishDraftResponse,
    QuizQuestionDraft,
    RegenerateQuestionRequest,
)
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(prefix="/studio", tags=["training-studio"])


@router.post("/generate", response_model=GenerationJobResponse, status_code=status.HTTP_201_CREATED)
async def generate_training(
    request: Request,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> GenerationJobResponse:
    """Generate draft course, lessons, quiz, and video storyboard in one guided pipeline."""
    content_type = request.headers.get("content-type", "")
    file_bytes: bytes | None = None
    filename: str | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if file_obj and hasattr(file_obj, "filename") and file_obj.filename:
            filename = file_obj.filename
            file_bytes = await file_obj.read()

        topic = form.get("topic")
        language = str(form.get("language") or "en")
        try:
            target_duration_minutes = int(form.get("target_duration_minutes") or 10)
        except (ValueError, TypeError):
            target_duration_minutes = 10

        def _to_bool(val: object, default: bool = True) -> bool:
            if val is None:
                return default
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("true", "1", "yes")

        include_quiz = _to_bool(form.get("include_quiz"), True)
        include_video = _to_bool(form.get("include_video"), True)
        audience = str(form.get("audience") or "all")

        req = GenerationRequest(
            topic=str(topic) if topic else None,
            source_file_name=filename,
            language=language,
            target_duration_minutes=target_duration_minutes,
            audience=audience,
            include_quiz=include_quiz,
            include_video=include_video,
        )
    else:
        try:
            body = await request.json()
            req = GenerationRequest.model_validate(body)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid request payload: {exc}",
            ) from exc

    if not req.topic and not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either a training topic or a source document is required.",
        )

    job = service.create_generation_job(
        db,
        actor=principal,
        request=req,
        file_bytes=file_bytes,
        filename=filename,
    )
    return GenerationJobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
def get_job_status(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> GenerationJobResponse:
    """Fetch status and current draft contents of a training generation job."""
    try:
        job = service.get_job_or_raise(db, job_id)
        return GenerationJobResponse.model_validate(job)
    except service.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        ) from None


@router.patch("/jobs/{job_id}", response_model=GenerationJobResponse)
def update_draft(
    job_id: uuid.UUID,
    payload: DraftUpdateRequest,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> GenerationJobResponse:
    """Edit draft course, lessons, or quiz before approving and publishing."""
    try:
        job = service.update_draft(db, job_id=job_id, actor=principal, data=payload)
        return GenerationJobResponse.model_validate(job)
    except service.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        ) from None
    except service.InvalidJobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/jobs/{job_id}/regenerate-question", response_model=QuizQuestionDraft)
def regenerate_question(
    job_id: uuid.UUID,
    payload: RegenerateQuestionRequest,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> QuizQuestionDraft:
    """Regenerate a single objective question in the draft quiz."""
    try:
        return service.regenerate_question(
            db,
            job_id=job_id,
            actor=principal,
            question_index=payload.question_index,
            hint=payload.topic_hint,
        )
    except service.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        ) from None
    except service.InvalidJobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/jobs/{job_id}/publish", response_model=PublishDraftResponse)
def publish_draft(
    job_id: uuid.UUID,
    payload: PublishDraftRequest,
    principal: Principal = Depends(require_permission(Permission.COURSES_PUBLISH)),
    db: Session = Depends(get_db),
) -> PublishDraftResponse:
    """Approve and publish draft training, with optional immediate assignment."""
    try:
        return service.publish_draft(
            db,
            job_id=job_id,
            actor=principal,
            publish_req=payload,
        )
    except service.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        ) from None
    except service.InvalidJobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.get("/video-asset/{filename}")
def get_video_asset(
    filename: str,
    principal: Principal = Depends(require_permission(Permission.COURSES_READ)),
) -> FileResponse:
    """Serve rendered training video (requires courses:read; no anonymous access)."""
    # Sanitize filename to prevent directory traversal
    safe_name = Path(filename).name
    asset_path = Path("storage/videos") / safe_name
    if not asset_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video asset not found.")
    return FileResponse(asset_path, media_type="video/mp4")


@router.get("/captions/{job_id}")
def get_captions(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> Response:
    """Serve WebVTT captions for the authoring preview (drafts; requires courses:write)."""
    try:
        job = service.get_job_or_raise(db, job_id)
        vtt = ""
        if job.generated_course_data and "captions_vtt" in job.generated_course_data:
            vtt = job.generated_course_data["captions_vtt"] or ""
        return Response(content=vtt, media_type="text/vtt")
    except service.JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        ) from None
