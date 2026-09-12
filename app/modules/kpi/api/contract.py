from dataclasses import dataclass
@dataclass(frozen=True)
class KPIAPIContract:
    resource:str='kpi'
    version:str='v1'
