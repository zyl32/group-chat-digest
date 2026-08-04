from datetime import datetime

from app.models.db import Base, get_engine, get_session
from app.models.upload import Upload
from app.models.message import Message
from app.models.todo import Todo
from app.models.digest import Digest


def test_create_upload_and_messages():
    engine = get_engine("sqlite://")
    Base.metadata.create_all(engine)
    with get_session(engine) as session:
        upload = Upload(filename="t.json", fmt="wechat", size=1024, status="received")
        session.add(upload)
        session.commit()
        msg = Message(
            upload_id=upload.id,
            sender="alice",
            content="hi",
            timestamp=datetime.now(),
            msg_id="m1",
        )
        session.add(msg)
        session.commit()
        assert session.query(Upload).count() == 1
        assert session.query(Message).count() == 1


def test_todo_state_constraint():
    engine = get_engine("sqlite://")
    Base.metadata.create_all(engine)
    with get_session(engine) as session:
        upload = Upload(filename="t.json", fmt="wechat", size=1, status="received")
        session.add(upload)
        session.commit()
        todo = Todo(upload_id=upload.id, who="alice", what="submit report", state="pending")
        session.add(todo)
        session.commit()
        assert todo.state == "pending"
