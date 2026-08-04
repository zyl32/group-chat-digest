from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


def get_engine(url: str = "sqlite:///data/db/app.db"):
    return create_engine(url, future=True)


@contextmanager
def get_session(engine) -> Session:
    session = sessionmaker(bind=engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
