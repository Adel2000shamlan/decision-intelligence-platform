from dataclasses import dataclass
@dataclass(frozen=True)
class ScenarioAPIContract:
    resource:str='scenario'
    version:str='v1'
