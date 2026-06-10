from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LatencyProfileName = Literal["balanced", "fast", "ultra_low"]


@dataclass(frozen=True)
class LatencyOptions:
    """Toggleable speed/privacy trade-offs for remote control."""

    profile: LatencyProfileName = "balanced"
    auto_prefetch_tree: bool = True
    auto_prefetch_screenshot: bool = False
    screenshot_thumbnail: bool = True
    observe_after_action: bool = True
    prewarm_model: bool = False
    optimistic_low_risk_actions: bool = False
    action_verify_delay_ms: int = 250

    @classmethod
    def for_profile(cls, profile: str) -> "LatencyOptions":
        if profile == "ultra_low":
            return cls(
                profile="ultra_low",
                auto_prefetch_tree=True,
                auto_prefetch_screenshot=True,
                screenshot_thumbnail=True,
                observe_after_action=False,
                prewarm_model=True,
                optimistic_low_risk_actions=True,
                action_verify_delay_ms=50,
            )
        if profile == "fast":
            return cls(
                profile="fast",
                auto_prefetch_tree=True,
                auto_prefetch_screenshot=False,
                screenshot_thumbnail=True,
                observe_after_action=True,
                prewarm_model=True,
                optimistic_low_risk_actions=False,
                action_verify_delay_ms=125,
            )
        return cls()

    def descriptions(self) -> dict[str, str]:
        return {
            "auto_prefetch_tree": "Fetches the accessibility tree before the model asks; faster planning, small local RPC cost.",
            "auto_prefetch_screenshot": "Fetches a thumbnail screenshot proactively; lowest latency for visual tasks, higher battery/privacy cost.",
            "screenshot_thumbnail": "Downscales screenshots for model use; faster and more private, less visual detail.",
            "observe_after_action": "Re-observes after each action; safer recovery, adds round-trip latency.",
            "prewarm_model": "Sends a tiny local model request before work starts; faster first answer, keeps model warm.",
            "optimistic_low_risk_actions": "Allows obvious low-risk navigation without extra verification; fastest, less conservative.",
            "action_verify_delay_ms": "Delay before verification after taps/types; lower is faster but can race animations.",
        }
