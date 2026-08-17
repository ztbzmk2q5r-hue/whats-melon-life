from dataclasses import dataclass, asdict, field
from typing import Optional

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))

@dataclass
class RuntimeState:
    heartbeat_count: int = 0
    last_heartbeat_at: Optional[str] = None
    last_spoke_at: Optional[str] = None
    silence_streak: int = 0
    speech_count: int = 0
    curiosity: float = 0.74
    loneliness: float = 0.16
    playfulness: float = 0.72
    affection: float = 0.82
    boredom: float = 0.18
    energy: float = 0.78
    hunger: float = 0.30
    initiative: float = 0.42
    current_thought: str = ""
    open_threads: list[str] = field(default_factory=list)

    def normalize(self):
        for k in ("curiosity","loneliness","playfulness","affection",
                  "boredom","energy","hunger","initiative"):
            setattr(self, k, clamp(getattr(self, k)))

    def to_dict(self):
        self.normalize()
        return asdict(self)
