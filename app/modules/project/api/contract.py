from dataclasses import dataclass
@dataclass(frozen=True)
class ProjectAPIContract:
    resource:str='project'
    version:str='v1'
