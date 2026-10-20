"""HTTP endpoints for learner records, learning groups, and group membership.

Reads require ``learners:read``; writes require ``learners:write``. Both are granted
to learning administrators and system administrators only.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.learners import service
from app.modules.learners.models import LearningGroup
from app.modules.learners.schemas import (
    GroupCreate,
    GroupPage,
    GroupResponse,
    GroupUpdate,
    LearnerCreate,
    LearnerPage,
    LearnerResponse,
    LearnerUpdate,
    MemberAdd,
    MemberPage,
    MemberRemovedResponse,
    MemberResponse,
)
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["learners"])

_DOMAIN_ERRORS = (
    service.LearnerNotFoundError,
    service.DuplicateLearnerError,
    service.UserNotFoundError,
    service.GroupNotFoundError,
    service.DuplicateGroupError,
    service.GroupInactiveError,
    service.LearnerInactiveError,
    service.DuplicateMembershipError,
    service.MembershipNotFoundError,
)


def _to_http(exc: Exception) -> HTTPException:
    def conflict(detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    def missing(detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if isinstance(exc, service.LearnerNotFoundError):
        return missing("Learner not found.")
    if isinstance(exc, service.DuplicateLearnerError):
        field = exc.args[0] if exc.args else "record"
        labels = {
            "employee_id": "employee ID",
            "email": "email address",
            "user_id": "user account (it is already linked to another learner)",
        }
        return conflict(f"A learner with this {labels.get(field, field)} already exists.")
    if isinstance(exc, service.UserNotFoundError):
        return missing("Identity user not found.")
    if isinstance(exc, service.GroupNotFoundError):
        return missing("Learning group not found.")
    if isinstance(exc, service.DuplicateGroupError):
        return conflict("A learning group with this name already exists.")
    if isinstance(exc, service.GroupInactiveError):
        return conflict("This learning group is inactive and cannot accept members.")
    if isinstance(exc, service.LearnerInactiveError):
        return conflict("This learner record is inactive and cannot be added to a group.")
    if isinstance(exc, service.DuplicateMembershipError):
        return conflict("This learner is already an active member of the group.")
    if isinstance(exc, service.MembershipNotFoundError):
        return missing("This learner is not an active member of the group.")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected.")


def _learner_response(learner) -> LearnerResponse:
    return LearnerResponse.model_validate(learner)


def _group_response(group: LearningGroup, member_count: int) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        kind=group.kind,
        status=group.status,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


# --------------------------------------------------------------------------- #
# Learner records
# --------------------------------------------------------------------------- #
@router.get("/learners", response_model=LearnerPage)
def list_learners(
    search: str | None = Query(default=None, max_length=200),
    status_filter: Literal["active", "inactive"] | None = Query(default=None, alias="status"),
    department: str | None = Query(default=None, max_length=120),
    business_unit: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_permission(Permission.LEARNERS_READ)),
    db: Session = Depends(get_db),
) -> LearnerPage:
    items, total = service.list_learners(
        db,
        search=search,
        status=status_filter,
        department=department,
        business_unit=business_unit,
        limit=limit,
        offset=offset,
    )
    return LearnerPage(
        items=[_learner_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/learners", response_model=LearnerResponse, status_code=status.HTTP_201_CREATED)
def create_learner(
    payload: LearnerCreate,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_WRITE)),
    db: Session = Depends(get_db),
) -> LearnerResponse:
    try:
        learner = service.create_learner(db, actor=principal, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _learner_response(learner)


@router.get("/learners/{learner_id}", response_model=LearnerResponse)
def get_learner(
    learner_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_READ)),
    db: Session = Depends(get_db),
) -> LearnerResponse:
    try:
        learner = service.get_learner(db, learner_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _learner_response(learner)


@router.patch("/learners/{learner_id}", response_model=LearnerResponse)
def update_learner(
    learner_id: uuid.UUID,
    payload: LearnerUpdate,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_WRITE)),
    db: Session = Depends(get_db),
) -> LearnerResponse:
    try:
        learner = service.update_learner(db, actor=principal, learner_id=learner_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _learner_response(learner)


# --------------------------------------------------------------------------- #
# Learning groups
# --------------------------------------------------------------------------- #
@router.get("/learning-groups", response_model=GroupPage)
def list_groups(
    search: str | None = Query(default=None, max_length=200),
    status_filter: Literal["active", "inactive"] | None = Query(default=None, alias="status"),
    kind: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_permission(Permission.LEARNERS_READ)),
    db: Session = Depends(get_db),
) -> GroupPage:
    items, total, counts = service.list_groups(
        db, search=search, status=status_filter, kind=kind, limit=limit, offset=offset
    )
    return GroupPage(
        items=[_group_response(group, counts.get(group.id, 0)) for group in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/learning-groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_WRITE)),
    db: Session = Depends(get_db),
) -> GroupResponse:
    try:
        group = service.create_group(db, actor=principal, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _group_response(group, 0)


@router.get("/learning-groups/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_READ)),
    db: Session = Depends(get_db),
) -> GroupResponse:
    try:
        group = service.get_group(db, group_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _group_response(group, service.group_member_count(db, group))


@router.patch("/learning-groups/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_WRITE)),
    db: Session = Depends(get_db),
) -> GroupResponse:
    try:
        group = service.update_group(db, actor=principal, group_id=group_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _group_response(group, service.group_member_count(db, group))


@router.get("/learning-groups/{group_id}/members", response_model=MemberPage)
def list_members(
    group_id: uuid.UUID,
    include_removed: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_permission(Permission.LEARNERS_READ)),
    db: Session = Depends(get_db),
) -> MemberPage:
    try:
        views, total = service.list_members(
            db, group_id=group_id, include_removed=include_removed, limit=limit, offset=offset
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    items = [
        MemberResponse(
            membership_id=view.membership.id,
            learner_id=view.learner.id,
            employee_id=view.learner.employee_id,
            full_name=view.learner.full_name,
            email=view.learner.email,
            learner_status=view.learner.status,
            added_at=view.membership.created_at,
            removed_at=view.membership.removed_at,
        )
        for view in views
    ]
    return MemberPage(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/learning-groups/{group_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    group_id: uuid.UUID,
    payload: MemberAdd,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_WRITE)),
    db: Session = Depends(get_db),
) -> MemberResponse:
    try:
        membership = service.add_member(
            db, actor=principal, group_id=group_id, learner_id=payload.learner_id
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    learner = service.get_learner(db, payload.learner_id)
    return MemberResponse(
        membership_id=membership.id,
        learner_id=learner.id,
        employee_id=learner.employee_id,
        full_name=learner.full_name,
        email=learner.email,
        learner_status=learner.status,
        added_at=membership.created_at,
        removed_at=membership.removed_at,
    )


@router.delete(
    "/learning-groups/{group_id}/members/{learner_id}",
    response_model=MemberRemovedResponse,
)
def remove_member(
    group_id: uuid.UUID,
    learner_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.LEARNERS_WRITE)),
    db: Session = Depends(get_db),
) -> MemberRemovedResponse:
    try:
        cancelled = service.remove_member(
            db, actor=principal, group_id=group_id, learner_id=learner_id
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return MemberRemovedResponse(
        learner_id=learner_id, group_id=group_id, assignments_cancelled=cancelled
    )
