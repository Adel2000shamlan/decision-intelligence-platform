from dataclasses import dataclass
@dataclass(frozen=True)
class KnowledgeAPIContract:
    resource:str='knowledge'
    version:str='v1'
