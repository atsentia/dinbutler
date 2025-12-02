from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List

class SandboxState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"

@dataclass
class SandboxInfo:
    sandbox_id: str
    template_id: str
    state: SandboxState
    started_at: datetime
    end_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    envs: Dict[str, str] = field(default_factory=dict)

    @property
    def is_running(self) -> bool:
        return self.state == SandboxState.RUNNING

@dataclass
class SandboxQuery:
    metadata: Optional[Dict[str, str]] = None
    state: Optional[List[SandboxState]] = None
