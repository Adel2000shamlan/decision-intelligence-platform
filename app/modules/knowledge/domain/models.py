from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
@dataclass
class KnowledgeItem:
    id: UUID; tenant_id: UUID; title: str; content: str; source: str; project_id: UUID|None=None; evidence_uri: str|None=None; created_at: datetime=field(default_factory=lambda:datetime.now(timezone.utc)); version:int=1
    @classmethod
    def create(cls,tenant_id,title,content,source,project_id=None,evidence_uri=None):
        if not str(title).strip() or not str(content).strip(): raise ValueError('title and content are required')
        return cls(uuid4(),UUID(str(tenant_id)),str(title).strip(),str(content),str(source).strip(),UUID(str(project_id)) if project_id else None,evidence_uri)
