from dataclasses import dataclass
from uuid import UUID
@dataclass(frozen=True)
class CreateExecution: project_id:UUID; title:str; description:str=''; planned_start:object=None; planned_end:object=None; budget:float=0; resource_plan:float=0; actor_id:UUID|None=None
@dataclass(frozen=True)
class PlanExecution: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class StartExecution: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class MarkExecutionAtRisk: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class BlockExecution: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class CompleteExecution: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class CancelExecution: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class ArchiveExecution: execution_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class UpdateExecutionProgress: execution_id:UUID; progress:float; actor_id:UUID|None=None
@dataclass(frozen=True)
class RecordResourceConsumption: execution_id:UUID; amount:float; actor_id:UUID|None=None
@dataclass(frozen=True)
class RecordBudgetSpend: execution_id:UUID; amount:float; actor_id:UUID|None=None
@dataclass(frozen=True)
class RecordScheduleVariance: execution_id:UUID; days:float; actor_id:UUID|None=None
@dataclass(frozen=True)
class CalculateExecutionHealth: execution_id:UUID; actor_id:UUID|None=None
