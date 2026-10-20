import os

# Configure the environment BEFORE importing the application.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["AUTH_PROVIDER"] = "disabled"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import registry  # noqa: F401  (registers all models on Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.users import repository
from app.modules.users import service as users_service
from app.modules.users.models import User, UserRole, UserStatus
from app.security.principal import AuthenticatedIdentity
from app.security.providers import InvalidCredentialsError, get_authentication_provider


class StubAuthenticationProvider:
    """Test double for an external identity provider.

    Real providers validate tokens/signatures/expiry; this stub lets tests
    exercise the provider-independent authorization boundary without inventing
    a fake production login path.
    """

    name = "stub"

    def __init__(self, holder: dict) -> None:
        self.holder = holder

    def authenticate(self, request):
        if self.holder.get("raise_invalid"):
            raise InvalidCredentialsError()
        return self.holder.get("identity")


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    users_service.ensure_roles(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def auth_holder():
    return {"identity": None, "raise_invalid": False}


@pytest.fixture()
def app(db_session, auth_holder):
    application = create_app()

    def override_get_db():
        yield db_session

    stub = StubAuthenticationProvider(auth_holder)
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_authentication_provider] = lambda: stub
    yield application
    application.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def deny_client(db_session):
    """Client using the real (deny-by-default) provider, only DB overridden."""
    application = create_app()

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


@pytest.fixture()
def login(auth_holder):
    def _login(subject="user-1", email="user1@example.com", name="User One"):
        auth_holder["identity"] = AuthenticatedIdentity(
            external_identity_id=subject, email=email, display_name=name
        )
        return auth_holder["identity"]

    return _login


@pytest.fixture()
def make_user(db_session):
    def _make(external_identity_id: str, roles=(), email: str | None = None) -> User:
        user = User(
            external_identity_id=external_identity_id,
            email=email,
            display_name=external_identity_id,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.flush()
        for role_name in roles:
            role = repository.get_role_by_name(db_session, role_name)
            assert role is not None, f"role not seeded: {role_name}"
            db_session.add(UserRole(user_id=user.id, role_id=role.id))
        db_session.commit()
        return user

    return _make
