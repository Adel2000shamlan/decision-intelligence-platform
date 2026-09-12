from dataclasses import dataclass
@dataclass(frozen=True)
class ExecutionAPIContract:
    resource:str='execution'
    version:str='v1'
