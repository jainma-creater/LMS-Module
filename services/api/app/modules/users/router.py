"""HTTP endpoints for identity and role administration.

Route handlers translate domain errors into HTTP responses; authorization is
enforced by dependencies, never by the client.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.users import service
from app.modules.users.schemas import (
    PrincipalResponse,
    RoleAssignmentRequest,
    UserRolesResponse,
)
from app.security.dependencies import get_current_principal, require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["users"])
admin_router = APIRouter(prefix="/admin", tags=["users-admin"])


@router.get("/me", response_model=PrincipalResponse)
def read_me(principal: Principal = Depends(get_current_principal)) -> PrincipalResponse:
    return PrincipalResponse.model_validate(principal)


@admin_router.get("/users/{user_id}/roles", response_model=UserRolesResponse)
def get_user_roles(
    user_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ROLES_ASSIGN)),
    db: Session = Depends(get_db),
) -> UserRolesResponse:
    try:
        service.get_user(db, user_id)
    except service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        ) from None
    return UserRolesResponse(user_id=user_id, roles=service.list_user_roles(db, user_id))


@admin_router.post(
    "/users/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
)
def assign_user_role(
    user_id: uuid.UUID,
    payload: RoleAssignmentRequest,
    principal: Principal = Depends(require_permission(Permission.ROLES_ASSIGN)),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.assign_role(db, actor=principal, user_id=user_id, role_name=payload.role)
    except service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        ) from None
    except service.RoleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found."
        ) from None
    except service.RoleAlreadyAssignedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Role already assigned."
        ) from None


@admin_router.delete(
    "/users/{user_id}/roles/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_user_role(
    user_id: uuid.UUID,
    role_name: str,
    principal: Principal = Depends(require_permission(Permission.ROLES_ASSIGN)),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.revoke_role(db, actor=principal, user_id=user_id, role_name=role_name)
    except service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        ) from None
    except service.RoleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found."
        ) from None
    except service.RoleNotAssignedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Role not assigned."
        ) from None
