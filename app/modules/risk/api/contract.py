from dataclasses import dataclass
@dataclass(frozen=True)
class RiskAPIContract:
    resource:str='risk'
    version:str='v1'
