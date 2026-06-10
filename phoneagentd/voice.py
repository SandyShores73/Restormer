from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import uuid4

InterjectionStatus = Literal["listening_for_break", "delivered", "cancelled", "expired"]


@dataclass
class VoiceInterjectionRequest:
    question: str
    reason: str = "agent needs user input"
    urgency: Literal["low", "normal", "urgent"] = "normal"
    max_listen_seconds: int = 45
    silence_ms: int = 900
    transcript_mode: Literal["local_only", "controller_only", "off"] = "controller_only"


@dataclass
class VoiceInterjection:
    id: str = field(default_factory=lambda: str(uuid4()))
    status: InterjectionStatus = "listening_for_break"
    created_at: float = field(default_factory=time.time)
    delivered_at: float | None = None
    request: VoiceInterjectionRequest = field(default_factory=lambda: VoiceInterjectionRequest(question=""))

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["battery_policy"] = "microphone opens only while waiting for a natural break, then shuts off after delivery/cancel/timeout"
        data["privacy_policy"] = "speech detection/transcription should run on the iPhone/controller or a local STT service; do not send audio to cloud unless explicitly enabled"
        return data

    def complete(self, delivered: bool) -> None:
        self.status = "delivered" if delivered else "cancelled"
        self.delivered_at = time.time()
