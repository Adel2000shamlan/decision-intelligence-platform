from dataclasses import dataclass
@dataclass(frozen=True)
class DecisionAPIContract:
    resource:str='decision'
    version:str='v1'
