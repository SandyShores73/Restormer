from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class CompactSessionState:
    session_id: str
    user_goal: str
    current_app: str = "unknown"
    current_subgoal: str = ""
    last_actions: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    known_constraints: list[str] = field(default_factory=lambda: [
        "One UI action at a time.",
        "Prefer accessibility tree before screenshots.",
        "Approval is required for sends, deletes, purchases, account/security changes, contacts, calendar, and messages.",
    ])
    final_success_criteria: str = "User goal is complete and no risky action was taken without approval."
    raw_screenshots_stored: bool = False

    def remember_action(self, action: str, summary: str) -> None:
        self.last_actions.append({"action": action, "summary": summary})
        self.last_actions = self.last_actions[-12:]


class AgentOrchestrator:
    """Compact, single-device orchestration state for weaker local models."""

    def __init__(self, goal: str, *, store_raw_screenshots: bool = False) -> None:
        self.state = CompactSessionState(
            session_id=str(uuid4()),
            user_goal=goal,
            raw_screenshots_stored=store_raw_screenshots,
        )
        self._action_in_flight = False

    def enqueue_action(self, action: str) -> None:
        if self._action_in_flight:
            raise RuntimeError("another phone action is already in flight")
        self._action_in_flight = True
        self.state.remember_action(action, "queued")

    def complete_action(self, action: str, summary: str) -> None:
        self._action_in_flight = False
        self.state.remember_action(action, summary)

    def compact_view(self) -> dict[str, Any]:
        return {
            "session_id": self.state.session_id,
            "user_goal": self.state.user_goal,
            "current_app": self.state.current_app,
            "current_subgoal": self.state.current_subgoal,
            "last_actions": self.state.last_actions[-12:],
            "pending_approvals": self.state.pending_approvals,
            "known_constraints": self.state.known_constraints,
            "final_success_criteria": self.state.final_success_criteria,
            "raw_screenshots_stored": self.state.raw_screenshots_stored,
        }
