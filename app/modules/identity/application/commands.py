from dataclasses import dataclass
from uuid import UUID
@dataclass(frozen=True)
class CreateUser: email:str; display_name:str; description:str=''; actor_id:UUID|None=None
@dataclass(frozen=True)
class SuspendUser: user_id:UUID; actor_id:UUID|None=None; reason:str=''; expected_version:int|None=None
@dataclass(frozen=True)
class ReactivateUser: user_id:UUID; actor_id:UUID|None=None; expected_version:int|None=None
@dataclass(frozen=True)
class ArchiveUser: user_id:UUID; actor_id:UUID|None=None; reason:str=''; expected_version:int|None=None
@dataclass(frozen=True)
class RenameUser: user_id:UUID; new_name:str; actor_id:UUID|None=None; expected_version:int|None=None
