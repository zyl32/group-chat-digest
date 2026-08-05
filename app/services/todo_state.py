"""Pure-logic todo state machine with explicit transitions."""

from types import MappingProxyType
from typing import Final, Mapping

__all__ = ["TodoStateMachine", "IllegalTransition"]


class IllegalTransition(Exception):
    def __init__(self, frm: str, action: str):
        super().__init__(f"illegal transition: state={frm} action={action}")
        self.frm = frm
        self.action = action


_TRANSITIONS: Final[Mapping[tuple[str, str], str]] = MappingProxyType({
    ("pending", "done"): "done",
    ("pending", "ignored"): "ignored",
    ("pending", "snoozed"): "snoozed",
    ("snoozed", "reactivate"): "pending",
})

_KNOWN_ACTIONS: Final[frozenset[str]] = frozenset(
    {action for _, action in _TRANSITIONS.keys()}
)


class TodoStateMachine:
    def transition(self, current_state: str, action: str) -> str:
        if (current_state, action) in _TRANSITIONS:
            return _TRANSITIONS[(current_state, action)]
        raise IllegalTransition(current_state, action)

    @classmethod
    def known_actions(cls) -> frozenset[str]:
        """Return the set of action names recognized by the state machine."""
        return _KNOWN_ACTIONS
