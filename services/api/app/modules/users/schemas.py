import uuid

from pydantic import BaseModel, ConfigDict, Field


class PrincipalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    external_identity_id: str
    email: str | None
    display_name: str | None
    roles: list[str]
    permissions: list[str]


class RoleAssignmentRequest(BaseModel):
    role: str = Field(min_length=1, max_length=50)


class UserRolesResponse(BaseModel):
    user_id: uuid.UUID
    roles: list[str]
