import pytest
from app.services.todo_state import TodoStateMachine, IllegalTransition


@pytest.fixture
def sm():
    return TodoStateMachine()


def test_pending_to_done(sm):
    assert sm.transition("pending", "done") == "done"


def test_pending_to_ignored(sm):
    assert sm.transition("pending", "ignored") == "ignored"


def test_pending_to_snoozed(sm):
    assert sm.transition("pending", "snoozed") == "snoozed"


def test_snoozed_to_pending(sm):
    assert sm.transition("snoozed", "reactivate") == "pending"


def test_done_to_pending_rejected(sm):
    with pytest.raises(IllegalTransition):
        sm.transition("done", "reactivate")


def test_ignored_to_done_rejected(sm):
    with pytest.raises(IllegalTransition):
        sm.transition("ignored", "done")


def test_unknown_action(sm):
    with pytest.raises(IllegalTransition):
        sm.transition("pending", "bogus")
