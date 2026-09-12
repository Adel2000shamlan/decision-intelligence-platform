from dataclasses import dataclass
@dataclass(frozen=True)
class AIAPIContract:
    resource:str='ai'
    version:str='v1'
