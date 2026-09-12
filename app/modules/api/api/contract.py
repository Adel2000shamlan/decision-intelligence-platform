from dataclasses import dataclass
@dataclass(frozen=True)
class APIAPIContract:
    resource:str='api'
    version:str='v1'
