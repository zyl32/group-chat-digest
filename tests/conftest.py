from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.llm.mock import MockLLMAdapter
from app.main import app
from app.models.db import Base


def _make_in_memory_engine() -> Engine:
    """Create an in-memory SQLite engine usable across threads.

    The default ``sqlite://`` engine uses ``SingletonThreadPool`` (one
    connection per thread), which breaks FastAPI's ``TestClient`` because
    request handlers run in a separate thread from the test. Using
    ``StaticPool`` with ``check_same_thread=False`` keeps a single shared
    connection so writes from one thread are visible to reads in another.
    """
    return create_engine(
        "sqlite://",
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def in_memory_db() -> Iterator[Session]:
    """Create an isolated in-memory SQLite database for a single test.

    Yields a SQLAlchemy Session bound to a fresh in-memory schema. The engine
    is disposed in teardown to avoid ResourceWarning about unclosed databases.
    """
    engine = _make_in_memory_engine()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(in_memory_db) -> Iterator[TestClient]:
    """Yield a FastAPI TestClient with DB dependency overridden to use in-memory DB.

    The router's ``get_db`` dependency is replaced so endpoint tests run
    against the same in-memory SQLite instance as ``in_memory_db``.
    """
    from app.routers.uploads import get_db

    session = in_memory_db

    def _override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm() -> Iterator[MockLLMAdapter]:
    """Yield a fresh MockLLMAdapter for testing LLM-dependent services.

    Tests can pre-program responses via `set_response` or inject failures
    via `fail_n_times` to exercise retry/fallback paths in DigestService
    (T15) and TodoExtractor (T16).
    """
    yield MockLLMAdapter()
