from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.llm.mock import MockLLMAdapter
from app.main import app
from app.models.db import Base, get_engine


@pytest.fixture
def in_memory_db() -> Iterator[Session]:
    """Create an isolated in-memory SQLite database for a single test.

    Yields a SQLAlchemy Session bound to a fresh in-memory schema. The engine
    is disposed in teardown to avoid ResourceWarning about unclosed databases.
    """
    engine = get_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a FastAPI TestClient.

    NOTE: T14 (Upload Router) will extend this with `app.dependency_overrides`
    to inject the in-memory DB session for endpoint-level tests. Today the
    healthz route has no DB dependency, so scaffolding-only.
    """
    yield TestClient(app)


@pytest.fixture
def mock_llm() -> Iterator[MockLLMAdapter]:
    """Yield a fresh MockLLMAdapter for testing LLM-dependent services.

    Tests can pre-program responses via `set_response` or inject failures
    via `fail_n_times` to exercise retry/fallback paths in DigestService
    (T15) and TodoExtractor (T16).
    """
    yield MockLLMAdapter()
