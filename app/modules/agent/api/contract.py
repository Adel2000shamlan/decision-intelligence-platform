from dataclasses import dataclass
@dataclass(frozen=True)
class AgentAPIContract:
    resource:str='agent'
    version:str='v1'
