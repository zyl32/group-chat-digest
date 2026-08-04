"""Pure-logic todo state machine with explicit transitions."""

__all__ = ["TodoStateMachine", "IllegalTransition"]


class IllegalTransition(Exception):
    def __init__(self, frm: str, action: str):
        super().__init__(f"illegal transition: state={frm} action={action}")
        self.frm = frm
        self.action = action


_TRANSITIONS: dict[tuple[str, str], str] = {
    ("pending", "done"): "done",
    ("pending", "ignored"): "ignored",
    ("pending", "snoozed"): "snoozed",
    ("snoozed", "reactivate"): "pending",
}


class TodoStateMachine:
    def transition(self, current_state: str, action: str) -> str:
        if (current_state, action) in _TRANSITIONS:
            return _TRANSITIONS[(current_state, action)]
        raise IllegalTransition(current_state, action)
