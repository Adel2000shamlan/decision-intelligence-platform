from dataclasses import dataclass
from uuid import UUID
from app.modules.option.domain.models import OptionType, OptionSource
@dataclass(frozen=True)
class CreateOption: decision_id: UUID; title: str; description: str=''; option_type: OptionType=OptionType.ORIGINAL; source: OptionSource=OptionSource.HUMAN; rank: int|None=None; actor_id: UUID|None=None
@dataclass(frozen=True)
class UpdateOption: option_id: UUID; actor_id: UUID|None=None; title: str|None=None; description: str|None=None; option_type: OptionType|None=None; source: OptionSource|None=None; rank: int|None=None
@dataclass(frozen=True)
class StartOptionEvaluation: option_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class MarkOptionEligible: option_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class SelectOption: option_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class RejectOption: option_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class WithdrawOption: option_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class ArchiveOption: option_id: UUID; actor_id: UUID|None=None
